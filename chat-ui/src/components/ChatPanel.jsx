import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { SRE_COMMANDS, parseAnalysis, toneClass } from '../lib/format';

const markdownComponents = {
  p: ({ node, ...props }) => <p className="break-words leading-relaxed mb-2 last:mb-0" {...props} />,
  ul: ({ node, ...props }) => <ul className="list-disc pl-4 space-y-1 my-2" {...props} />,
  table: ({ node, ...props }) => (
    <div className="overflow-x-auto my-3 border border-slate-800 rounded-lg">
      <table className="min-w-full divide-y divide-slate-800 text-left text-xs font-mono" {...props} />
    </div>
  ),
  thead: ({ node, ...props }) => <thead className="bg-slate-950 text-slate-400" {...props} />,
  th: ({ node, ...props }) => <th className="px-3 py-2 font-semibold" {...props} />,
  td: ({ node, ...props }) => <td className="px-3 py-2 border-t border-slate-800/60 align-top" {...props} />,
  pre: ({ node, ...props }) => (
    <pre className="p-3 rounded-lg bg-slate-950 text-cyan-200 font-mono text-xs border border-slate-800 overflow-x-auto my-2 whitespace-pre-wrap break-words" {...props} />
  ),
  code: ({ node, inline, ...props }) =>
    inline ? (
      <code className="px-1.5 py-0.5 rounded bg-slate-950 text-cyan-200 font-mono text-xs border border-slate-800" {...props} />
    ) : (
      <code className="block font-mono text-xs whitespace-pre-wrap break-words" {...props} />
    ),
};

export default function ChatPanel({ messages, onSendMessage, isLoading, activeNamespace }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  return (
    <main className="flex-1 flex flex-col min-h-0 min-w-0 bg-transparent">
      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-5 space-y-5">
        {messages.map((msg, index) => (
          <Message key={index} msg={msg} />
        ))}
        {isLoading && (
          <div className="flex gap-3 max-w-3xl">
            <Avatar>AI</Avatar>
            <div className="px-4 py-3 rounded-2xl rounded-tl-md bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-300 animate-pulse" />
              Reading the cluster and preparing the next step
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-slate-800 bg-slate-950/80">
        <div className="flex flex-wrap gap-2 mb-3">
          {SRE_COMMANDS.map((command) => (
            <button
              key={command.prompt}
              type="button"
              onClick={() => onSendMessage(command.prompt)}
              disabled={isLoading}
              className="text-[11px] px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 disabled:opacity-50"
            >
              {command.label}
            </button>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={isLoading}
            placeholder={`Ask about ${activeNamespace}: failing pods, restarts, scale, logs`}
            className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-4 py-3 rounded-xl bg-cyan-300 hover:bg-cyan-200 text-slate-950 font-semibold text-sm disabled:opacity-40"
          >
            Send
          </button>
        </form>
      </div>
    </main>
  );
}

function Message({ msg }) {
  const isUser = msg.sender === 'user';
  const analysis = !isUser ? parseAnalysis(msg.text) : null;
  const isError = msg.kind === 'error' || /Kubernetes unavailable|Deployment not found|Pod not found|Approval expired|backend unreachable/i.test(msg.text || '');
  const isSuccess = msg.kind === 'success';

  return (
    <div className={`flex gap-3 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : ''}`}>
      <Avatar user={isUser}>{isUser ? 'You' : 'AI'}</Avatar>
      <div className="min-w-0 space-y-2">
        {msg.invokedTools?.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {msg.invokedTools.map((tool, index) => (
              <span key={index} className="px-2 py-0.5 rounded-full border border-slate-700 bg-slate-950 text-[10px] font-mono text-cyan-200">
                {tool.tool}
              </span>
            ))}
          </div>
        )}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-slate-800 text-slate-50 rounded-tr-md'
              : isError
                ? 'bg-rose-950/40 border border-rose-900 text-rose-50 rounded-tl-md'
                : isSuccess
                  ? 'bg-emerald-950/30 border border-emerald-900 text-slate-100 rounded-tl-md'
                  : 'bg-slate-900/90 border border-slate-800 text-slate-100 rounded-tl-md'
          }`}
        >
          {analysis ? <AnalysisCard analysis={analysis} /> : (
            <ReactMarkdown components={markdownComponents}>{msg.text || ''}</ReactMarkdown>
          )}
        </div>
        <div className="text-[10px] font-mono text-slate-500 px-1">{msg.timestamp}</div>
      </div>
    </div>
  );
}

function AnalysisCard({ analysis }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs uppercase tracking-wide text-slate-400">Root cause analysis</div>
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${toneClass(analysis.riskTone)}`}>
          {analysis['Risk Level'].split('\n')[0]}
        </span>
      </div>
      <Section title="Root Cause" body={analysis['Root Cause']} />
      <Section title="Evidence" body={analysis.Evidence} />
      <Section title="Suggested Fix" body={analysis['Suggested Fix']} />
    </div>
  );
}

function Section({ title, body }) {
  return (
    <div>
      <div className="text-[11px] font-semibold text-cyan-200 mb-1">{title}</div>
      <ReactMarkdown components={markdownComponents}>{body}</ReactMarkdown>
    </div>
  );
}

function Avatar({ children, user }) {
  return (
    <div className={`w-8 h-8 rounded-lg shrink-0 grid place-items-center text-[10px] font-bold font-mono ${user ? 'bg-slate-800 text-slate-200' : 'bg-cyan-300 text-slate-950'}`}>
      {children}
    </div>
  );
}
