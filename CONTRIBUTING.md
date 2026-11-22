# Contributing to InfraGPT

Thank you for your interest in contributing to InfraGPT! We welcome community contributions in SRE diagnostics, FastMCP tools, and UI components.

---

### Development Workflow

1. **Fork and Clone the Repository:**
   ```bash
   git clone https://github.com/Akshat-124/Infra_GPT.git
   ```

2. **Backend Setup:**
   ```bash
   pip install -r orchestrator/requirements.txt -r mcp-server/requirements.txt
   python orchestrator/test_api.py
   ```

3. **Frontend Setup:**
   ```bash
   cd chat-ui
   npm install
   npm run dev
   ```

4. **Conventional Commits:**
   Please use conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `sec:`).
