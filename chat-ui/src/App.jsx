import React, { useEffect, useMemo, useState } from 'react';
import Header from './components/Header';
import StatusStrip from './components/StatusStrip';
import ClusterSidebar from './components/ClusterSidebar';
import ChatPanel from './components/ChatPanel';
import ApprovalModal from './components/ApprovalModal';
import AuditPanel from './components/AuditPanel';
import DemoScenarios from './components/DemoScenarios';
import { api, apiErrorMessage } from './services/api';
import { healthFromPods } from './lib/format';

const WELCOME = `### InfraGPT is online

I can inspect this namespace, explain a failure, and prepare a change for you to approve.

Try one of the commands under the composer, or open **Scenarios** to break payment-service and order-service on purpose. The simulator is the default, so a live cluster is not modified.`;

export default function App() {
  const [view, setView] = useState('operate');
  const [mobilePane, setMobilePane] = useState('chat');
  const [activeNamespace, setActiveNamespace] = useState('production');
  const [clusterStatus, setClusterStatus] = useState(null);
  const [pods, setPods] = useState([]);
  const [deployments, setDeployments] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditBackend, setAuditBackend] = useState('memory');
  const [backendError, setBackendError] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessingApproval, setIsProcessingApproval] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(null);
  const [approvalError, setApprovalError] = useState('');
  const [demoNotice, setDemoNotice] = useState(null);
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: WELCOME,
      timestamp: new Date().toLocaleTimeString(),
      invokedTools: [],
    },
  ]);

  const health = useMemo(() => healthFromPods(pods), [pods]);

  const fetchClusterData = async () => {
    try {
      setIsRefreshing(true);
      const [statusData, podsData, depsData, logsData] = await Promise.all([
        api.getClusterStatus(),
        api.getPods(activeNamespace),
        api.getDeployments(activeNamespace),
        api.getAuditLogs(),
      ]);
      setClusterStatus(statusData);
      setPods(Array.isArray(podsData) ? podsData : []);
      setDeployments(Array.isArray(depsData) ? depsData : []);
      setAuditLogs(logsData.logs || logsData || []);
      setAuditBackend(logsData.backend || statusData.audit_backend || 'memory');
      setBackendError('');
    } catch (err) {
      const text = apiErrorMessage(err).replace(/\*\*/g, '');
      setBackendError(text.split('\n')[0]);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchClusterData();
    const interval = setInterval(fetchClusterData, 10000);
    return () => clearInterval(interval);
  }, [activeNamespace]);

  const pushMessage = (message) => {
    setMessages((prev) => [...prev, { timestamp: new Date().toLocaleTimeString(), invokedTools: [], ...message }]);
  };

  const handleSendMessage = async (text) => {
    const history = messages.map((message) => ({
      role: message.sender === 'user' ? 'user' : 'model',
      content: message.text,
    }));
    pushMessage({ sender: 'user', text });
    setIsLoading(true);
    setView('operate');
    try {
      const data = await api.sendMessage(text, activeNamespace, history);
      if (data.requires_approval) {
        setApprovalError('');
        setPendingApproval({
          approval_id: data.approval_id,
          tool_name: data.tool_name,
          args: data.args,
          summary: data.summary,
          before: data.before,
          after: data.after,
          risk: data.risk,
          expires_at: data.expires_at,
          message: data.message,
        });
      } else {
        pushMessage({
          sender: 'ai',
          text: data.response || 'No response was returned.',
          kind: data.error ? 'error' : 'ai',
          invokedTools: data.invoked_tools || [],
        });
      }
      fetchClusterData();
    } catch (err) {
      pushMessage({ sender: 'ai', kind: 'error', text: apiErrorMessage(err) });
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmApproval = async (approvalId) => {
    try {
      setIsProcessingApproval(true);
      setApprovalError('');
      const res = await api.approveAction(approvalId, true);
      if (res.success === false) {
        setApprovalError(res.error || res.message);
        pushMessage({
          sender: 'ai',
          kind: 'error',
          text: `**${res.error || 'The operation could not be completed'}**\n\n${res.message || ''}`,
        });
        if (res.error === 'Approval expired' || res.status === 'FAILED') {
          setPendingApproval(null);
        }
      } else {
        pushMessage({
          sender: 'ai',
          kind: 'success',
          text: `### Change applied\n\n${res.message}\n\n**Before** \`${JSON.stringify(res.before)}\`\n\n**After** \`${JSON.stringify(res.after)}\``,
          invokedTools: [{ tool: res.tool_name, args: pendingApproval?.args || {} }],
        });
        setPendingApproval(null);
      }
      await fetchClusterData();
    } catch (err) {
      const text = apiErrorMessage(err);
      setApprovalError(text.replace(/\*\*/g, '').split('\n')[0]);
      pushMessage({ sender: 'ai', kind: 'error', text });
      if (/Approval expired|Approval request not found/i.test(text)) {
        setPendingApproval(null);
      }
    } finally {
      setIsProcessingApproval(false);
    }
  };

  const handleCancelApproval = async (approvalId) => {
    try {
      setIsProcessingApproval(true);
      const res = await api.approveAction(approvalId, false);
      pushMessage({
        sender: 'ai',
        text: res.message || `Rejected. \`${pendingApproval?.tool_name}\` was not applied.`,
      });
      setPendingApproval(null);
      await fetchClusterData();
    } catch (err) {
      pushMessage({ sender: 'ai', kind: 'error', text: apiErrorMessage(err) });
      setPendingApproval(null);
    } finally {
      setIsProcessingApproval(false);
    }
  };

  const handleRunScenario = async (scenario) => {
    try {
      const result = await api.runDemo(scenario.id, activeNamespace);
      setDemoNotice({ ok: true, title: scenario.title, detail: result.message });
      pushMessage({ sender: 'ai', kind: 'success', text: `**${scenario.title}**\n\n${result.message}` });
      await fetchClusterData();
    } catch (err) {
      const text = apiErrorMessage(err);
      setDemoNotice({ ok: false, title: scenario.title, detail: text.replace(/\*\*/g, '') });
      pushMessage({ sender: 'ai', kind: 'error', text });
    }
  };

  return (
    <div className="flex flex-col h-screen text-slate-100 overflow-hidden">
      <Header
        clusterStatus={clusterStatus}
        activeNamespace={activeNamespace}
        onNamespaceChange={setActiveNamespace}
        onRefresh={fetchClusterData}
        isRefreshing={isRefreshing}
        view={view}
        onViewChange={setView}
      />
      <StatusStrip
        health={health}
        lastCommand={clusterStatus?.last_command}
        backendError={backendError}
        auditBackend={auditBackend}
      />

      <div className="flex-1 flex flex-col lg:flex-row min-h-0">
        {view === 'operate' && (
          <>
            <div className="lg:hidden flex gap-1 p-2 border-b border-slate-800 bg-slate-950 shrink-0">
              <button
                type="button"
                onClick={() => setMobilePane('chat')}
                className={`flex-1 py-1.5 rounded-lg text-xs font-medium ${mobilePane === 'chat' ? 'bg-slate-100 text-slate-950' : 'text-slate-400'}`}
              >
                Chat
              </button>
              <button
                type="button"
                onClick={() => setMobilePane('cluster')}
                className={`flex-1 py-1.5 rounded-lg text-xs font-medium ${mobilePane === 'cluster' ? 'bg-slate-100 text-slate-950' : 'text-slate-400'}`}
              >
                Cluster ({pods.length})
              </button>
            </div>
            <div className={`${mobilePane === 'cluster' ? 'flex' : 'hidden'} lg:flex flex-1 lg:flex-none min-h-0`}>
              <ClusterSidebar
                pods={pods}
                deployments={deployments}
                activeNamespace={activeNamespace}
                onSelectPodForLog={(podName) => {
                  setMobilePane('chat');
                  handleSendMessage(`Show recent logs for pod ${podName}`);
                }}
                onAsk={(prompt) => {
                  setMobilePane('chat');
                  handleSendMessage(prompt);
                }}
              />
            </div>
            <div className={`${mobilePane === 'chat' ? 'flex' : 'hidden'} lg:flex flex-1 min-h-0 min-w-0`}>
              <ChatPanel
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                activeNamespace={activeNamespace}
              />
            </div>
          </>
        )}
        {view === 'scenarios' && (
          <DemoScenarios
            activeNamespace={activeNamespace}
            onRun={handleRunScenario}
            onAsk={handleSendMessage}
            isBusy={isLoading}
            notice={demoNotice}
          />
        )}
        {view === 'audit' && <AuditPanel auditLogs={auditLogs} backend={auditBackend} />}
      </div>

      <ApprovalModal
        pendingApproval={pendingApproval}
        onConfirm={handleConfirmApproval}
        onCancel={handleCancelApproval}
        isProcessing={isProcessingApproval}
        error={approvalError}
      />
    </div>
  );
}
