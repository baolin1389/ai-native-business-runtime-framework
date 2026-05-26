# Deployment Isolation

## Overview

When an MCP Server manages sensitive business data, the database must be isolated from the AI Agent's execution environment. This is not a code-level constraint — it is a **deployment contract** that any Agent framework (OpenClaw, Hermes, or others) must satisfy.

## Why Code-Level Enforcement Is Impossible

AI Agents have arbitrary code execution capability. Any check placed inside the execution context can be inspected and bypassed by the agent itself:

```
Agent Execution Context
├── import database.py  → reads connection path
├── exec()              → bypasses any runtime check
└── requests.post()     → connects to DB if network-accessible
```

The only reliable protection is **architectural isolation**: the database is physically unreachable from the agent's execution context, regardless of what code the agent runs.

## The Deployment Contract

```
┌──────────────────────────────────────────────────────────────┐
│  AI Agent (OpenClaw / Hermes / any framework)               │
│  Code execution + filesystem access + network access           │
└─────────────────────────┬────────────────────────────────────┘
                          │ MCP over stdio (the only legal gate)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  MCP Server (stdio daemon)                                   │
│  tools.py is the ONLY data access path                       │
│  No direct DB file or connection exposed to the agent        │
└─────────────────────────┬────────────────────────────────────┘
                          │ DB connection (MCP Server process only)
                          ▼
┌──────────────────────────────────────────────────────────────┐
│  Database (isolated)                                         │
│  Path: outside agent workspace                                │
│  Credentials: passed via env:, not via filesystem             │
│  Network: not directly reachable from agent context            │
└──────────────────────────────────────────────────────────────┘
```

## Three Requirements

### 1. Database Path Outside Agent Workspace

The database file MUST be stored outside any directory the agent can explore, guess, or access via filesystem tools.

```
# ❌ Agent can find it via workspace exploration
/Users/ICECOOL/.hermes/workspace/foreign-trade-mcp/data/foreign_trade.db

# ✅ Agent has no way to discover this path
~/.hermes/.db/foreign_trade.db
```

### 2. Credentials via `env:`, Not Filesystem

DB connection credentials (encryption keys, passwords, API tokens) MUST be passed through the MCP Server's environment, not written to any file the agent can read.

In your MCP server config (`config.yaml` or equivalent):

```yaml
mcp_servers:
  my-mcp-server:
    command: python3
    args:
      - mcp_server.py
    env:
      DB_KEY: "your-32-char-secret"
      DB_PATH: "~/.hermes/.db/business.db"
```

The agent cannot read environment variables of another process — only the parent process's environment.

### 3. No Agent Filesystem Access to DB Path

Even if the agent can execute code, it must not be able to `open("/path/to/db")`. This can be enforced by:

- **File permissions**: MCP Server runs as a different user with exclusive read access to the DB directory
- **macOS SIP / App Sandbox**: Restrict the agent process from accessing certain paths
- **Chroot / container**: Isolate the agent process from the DB path entirely
- **Network isolation**: If the DB is a remote server (PostgreSQL, MySQL), it is only reachable from the MCP Server's network context

## MCP Server Implementation Checklist

When building an MCP Server for sensitive data, the `tools.py` file is the **only** entry point for data operations. Follow these rules:

- [ ] `tools.py` contains all database access functions
- [ ] `mcp_server.py` only delegates to `tools.py` — no direct `engine.execute()` calls with raw SQL
- [ ] `database.py` is NOT importable by anything other than the MCP Server process
- [ ] Database file path is read from an environment variable, not hardcoded in source
- [ ] No credentials are written to any file in the agent's workspace
- [ ] All MCP tool functions have descriptive docstrings explaining their behavior (not just their parameters)

## MCP Server Packaging Template

When distributing an MCP Server based on this framework, include this contract in your `README.md`:

```markdown
## Security / Deployment Requirements

This MCP Server manages sensitive business data.
The database MUST be isolated from the AI Agent's execution environment:

1. Database file path MUST be outside the agent's workspace
2. DB credentials MUST be passed via `env:` in your MCP config
3. The agent MUST NOT have filesystem access to the DB file path

Failure to meet these requirements allows the agent to bypass MCP tools
and access data directly, defeating the purpose of access control.
```

## Framework Generation

When using `runtime_generator/` to scaffold a new MCP Server project, these requirements should be documented in the generated project's `README.md` and enforced by the project template's `database.py` (which should read `DB_PATH` from environment and default to a path outside the workspace).

## Relationship to This Document

This document is the canonical reference for the deployment isolation requirement described in:

- `docs/architecture/mcp-adapter.md` — MCP Server architecture pattern
- `docs/guides/security.md` — General security guidelines for MCP Servers

Revisions to this document should be reflected in those guides as well.
