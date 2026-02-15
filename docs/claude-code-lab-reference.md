# Claude Code as CMO Lab — Complete Reference

Build and validate the CMO "brain" (agents, skills, MCP connections, knowledge) inside Claude Code using your Max subscription. Once workflows are proven, transfer them to the CrewAI production project (`the-ai-first-co`). This document covers everything needed to set up and use the lab.

---

## 1. SKILLS

### What They Are

Skills are custom slash commands. Each is a markdown file with optional YAML frontmatter that defines a reusable workflow Claude follows when invoked.

### File Structure

```
.claude/skills/                          # project-level (committed to git)
├── linkedin/
│   ├── SKILL.md                         # /linkedin command (required)
│   ├── template.md                      # optional template
│   └── examples/
│       └── sample-post.md               # optional example output
├── blog/
│   └── SKILL.md                         # /blog command
└── strategy/
    └── SKILL.md                         # /strategy command

~/.claude/skills/                        # personal (works across ALL projects)
└── research/
    └── SKILL.md                         # /research (available everywhere)
```

### SKILL.md Format

```yaml
---
name: linkedin                           # slash command name (lowercase, hyphens)
description: Create a LinkedIn post      # when to auto-invoke + /menu description
disable-model-invocation: false          # true = only manual /invoke, no auto-trigger
user-invocable: true                     # false = only Claude can trigger (background knowledge)
allowed-tools: Read, Grep, Bash(python *)# auto-approved tools (no permission prompts)
argument-hint: [topic] [audience]        # shown in /menu as usage hint
model: claude-sonnet-4-5-20250929        # override model for this skill
context: fork                            # fork = run in isolated subagent context
agent: strategist                        # which custom agent runs this (requires context: fork)
hooks:                                   # hooks scoped to this skill's lifetime
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
---

Markdown instructions here. Claude follows these when the skill is invoked.
```

All frontmatter fields are optional. Only the markdown body is required.

### Arguments

Skills accept positional arguments via string substitution:

```markdown
Create a $0 post about "$1" targeting $2.
```

`/linkedin "AEO trends" "marketing managers"` becomes:
`Create a linkedin post about "AEO trends" targeting marketing managers.`

| Variable | Meaning |
|---|---|
| `$ARGUMENTS` | All arguments as one string |
| `$ARGUMENTS[0]` or `$0` | First argument |
| `$ARGUMENTS[1]` or `$1` | Second argument |
| `${CLAUDE_SESSION_ID}` | Current session ID |

If no `$ARGUMENTS` placeholder exists in the skill, Claude Code appends `ARGUMENTS: <input>` automatically.

### Shell Command Preprocessing

The `` !`command` `` syntax runs commands BEFORE Claude sees the prompt. Output replaces the placeholder:

```markdown
## Current context
- Company config: !`cat config/bison.yaml`
- Recent posts: !`ls -la output/cmo/`
- Current date: !`date +%Y-%m-%d`

## Task
Write a LinkedIn post about $ARGUMENTS...
```

Claude receives the fully-rendered prompt with actual command output. This is preprocessing, not a tool call.

### Allowed-Tools Syntax

| Pattern | Matches |
|---|---|
| `Read` | Exact tool |
| `Read, Grep, Glob` | Multiple tools (comma-separated) |
| `Bash(python *)` | Bash commands starting with "python" |
| `Bash(git *)` | Bash commands starting with "git" |
| `Bash` | All bash commands |
| `mcp__github__*` | All GitHub MCP tools |
| `mcp__supabase__query` | Specific MCP tool |
| `Task(worker, researcher)` | Only spawn these agent types |

### Auto-Invocation

When `disable-model-invocation` is false (default), Claude automatically triggers the skill when the user's request matches the `description`. To prevent auto-triggers on dangerous skills (deploy, publish, send messages), set `disable-model-invocation: true`.

### Skills Cannot Chain Directly

Skills cannot call other skills. But a skill with `context: fork` spawns a subagent, and that subagent can invoke skills if needed. For sequential workflows, describe all steps in a single skill.

### Supporting Files

Keep SKILL.md focused (under 500 lines). Move reference material to sibling files:

```
my-skill/
├── SKILL.md           # Main instructions
├── reference.md       # Detailed docs (loaded when Claude clicks link)
├── examples/
│   └── sample.md      # Example output
└── scripts/
    └── validate.sh    # Executable helper
```

Reference from SKILL.md: `For complete API details, see [reference.md](reference.md)`

---

## 2. AGENTS (SUBAGENTS)

### What They Are

Custom agents are dedicated Claude instances with their own personality, tools, model, and memory. Each runs in its own context window and returns results to the main conversation.

### File Structure

```
.claude/agents/                          # project-level (committed to git)
├── strategist.md                        # marketing strategist
├── copywriter.md                        # content writer
└── editor.md                            # content reviewer

~/.claude/agents/                        # personal (all projects)
└── researcher.md                        # general research agent
```

### Agent File Format

```yaml
---
name: strategist
description: Content strategist expert in B2B SaaS marketing. Use for creating content strategies based on Hormozi and Priestley frameworks.
tools: Read, Grep, Glob                  # allow-list: ONLY these tools
disallowedTools: Write, Edit             # deny-list: BLOCK these tools (alternative to allow-list)
model: sonnet                            # sonnet, opus, haiku, or inherit (from parent)
maxTurns: 10                             # max iterations before stopping
memory: project                          # persistent memory scope (see below)
permissionMode: default                  # permission handling (see below)
skills:                                  # preload these skills into agent context
  - api-conventions
  - error-handling-patterns
mcpServers:                              # MCP server access (see below)
  - supabase
  - google-docs
hooks:                                   # hooks scoped to agent lifetime
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
---

You are a senior content strategist with deep expertise in B2B SaaS marketing.

Your full system prompt / personality goes here as markdown.
This entire body becomes the agent's system prompt.
```

### Permission Modes

| Mode | Behavior | Use case |
|---|---|---|
| `default` | User approves each tool use | Normal operation |
| `acceptEdits` | Auto-accept file edits | Trusted file modifications |
| `dontAsk` | Auto-deny prompts (only allowed-tools work) | Restricted agent |
| `delegate` | Coordination only, can only spawn/manage teammates | Team lead |
| `bypassPermissions` | Skip all checks | Use with extreme caution |
| `plan` | Read-only exploration | Research before implementation |

### Persistent Memory

Agents can retain knowledge across sessions via `MEMORY.md` files:

| Scope | Location | Use case |
|---|---|---|
| `user` | `~/.claude/agent-memory/<name>/` | Learnings across all projects |
| `project` | `.claude/agent-memory/<name>/` | Project-specific, sharable via git |
| `local` | `.claude/agent-memory-local/<name>/` | Project-specific, don't commit |

How it works:
- First 200 lines of `MEMORY.md` are injected into agent context at startup
- Agent can read and update `MEMORY.md` during execution
- Memory persists between conversations
- Over time, builds institutional knowledge

### MCP in Agents

Agents access MCP servers via the `mcpServers` field:

**Reference existing servers** (configured in settings):
```yaml
mcpServers:
  - supabase
  - google-docs
```

**Inline definition**:
```yaml
mcpServers:
  custom-api:
    type: http
    url: "https://api.example.com/mcp"
    headers:
      Authorization: "Bearer ${API_TOKEN}"
```

**Mix both**:
```yaml
mcpServers:
  - supabase                            # reference
  - google-docs                         # reference
  custom-deploy:                        # inline
    type: http
    url: "https://deploy.internal.com/mcp"
```

Limitation: **background subagents cannot use MCP**. Only foreground subagents have MCP access.

### Skills Preloading in Agents

The `skills` field preloads full skill content into the agent's context at startup:

```yaml
skills:
  - api-conventions
  - error-handling-patterns
```

The agent doesn't discover or invoke these skills — it just knows the content from the start.

### Parallel Execution

Multiple subagents can run simultaneously:
- **Foreground**: blocks main conversation until complete
- **Background**: runs concurrently (press Ctrl+B to background a running task)
  - Cannot use MCP tools
  - Cannot ask clarifying questions
  - Must have all permissions pre-approved

### Resume Behavior

Each subagent gets an agent ID on creation. Ask Claude to "continue that review" to resume with full previous context. Transcripts persist at `~/.claude/projects/{project}/{sessionId}/subagents/`.

### Agent Teams (Experimental)

Multiple Claude instances coordinated by a team lead:
- Teammates run independently with own context windows
- Share a task list (pending/in-progress/completed)
- Can message each other directly
- Lead coordinates, assigns, and synthesizes

Enable: set env `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

Token costs are much higher (each teammate is a full Claude instance).

---

## 3. MCP (Model Context Protocol)

### What It Is

MCP connects Claude Code to external services (databases, APIs, SaaS tools). Once connected, Claude automatically discovers and can use the tools exposed by each server.

### Configuration Files

| File | Scope | Shared | Use case |
|---|---|---|---|
| `.mcp.json` (project root) | Project | Yes (git) | Team-shared integrations |
| `~/.claude.json` | User/Local | No | Personal tools, credentials |
| `/Library/Application Support/ClaudeCode/managed-mcp.json` | Enterprise (macOS) | Admin-managed | Org-wide required services |

### Transport Types

**HTTP (recommended)**:
```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_TOKEN}"
      }
    }
  }
}
```

**Stdio (local tools)**:
```json
{
  "mcpServers": {
    "supabase": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server", "--supabase-url", "https://xxx.supabase.co", "--supabase-key", "${SUPABASE_KEY}"],
      "env": {
        "SUPABASE_KEY": "${SUPABASE_SERVICE_KEY}"
      }
    }
  }
}
```

**SSE (deprecated, use HTTP instead)**:
```json
{
  "mcpServers": {
    "legacy": {
      "type": "sse",
      "url": "https://mcp.example.com/sse"
    }
  }
}
```

### CLI Commands

```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
claude mcp add --transport stdio db -- npx -y @bytebase/dbhub
claude mcp add --transport http api https://api.example.com --header "Authorization: Bearer token"
claude mcp list
claude mcp get github
claude mcp remove github
claude mcp reset-project-choices
```

Important: all options must come BEFORE the server name. Use `--` to separate options from the stdio command.

### Authentication

**Bearer token**:
```bash
claude mcp add --transport http api https://api.example.com \
  --header "Authorization: Bearer ${API_TOKEN}"
```

**OAuth 2.0** (automatic):
```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
# Then: /mcp → select server → authenticate in browser
```

**OAuth 2.0** (pre-configured):
```bash
claude mcp add --transport http my-server https://mcp.example.com \
  --client-id your-client-id --client-secret --callback-port 8080
```

Credentials stored securely in system keychain (macOS) or encrypted file (Linux/Windows).

### Environment Variable Expansion

```json
{
  "env": {
    "DB_URL": "${DATABASE_URL:-postgresql://localhost:5432}",
    "API_KEY": "${API_KEY}"
  }
}
```

- `${VAR}` — required, fails if not set
- `${VAR:-default}` — uses default if VAR not set

### Tool Naming Convention

MCP tools follow: `mcp__<server-name>__<tool-name>`

In permission rules:
```json
{
  "permissions": {
    "allow": ["mcp__github__*"],
    "deny": ["mcp__dangerous__*"]
  }
}
```

### Common MCP Servers

**Supabase** (database + knowledge storage):
```json
{
  "mcpServers": {
    "supabase": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server", "--supabase-url", "https://xxx.supabase.co", "--supabase-key", "${SUPABASE_KEY}"]
    }
  }
}
```

**GitHub**:
```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    }
  }
}
```

**Notion**:
```json
{
  "mcpServers": {
    "notion": {
      "type": "http",
      "url": "https://mcp.notion.com/mcp"
    }
  }
}
```

**PostgreSQL**:
```json
{
  "mcpServers": {
    "postgres": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub"],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}"
      }
    }
  }
}
```

**Slack**:
```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://mcp.slack.com/api"
    }
  }
}
```

### Debugging

```bash
/mcp                    # interactive status of all servers
claude doctor           # diagnose config errors, unreachable servers
MCP_DEBUG=1 claude      # enable debug logging (check ~/.claude/logs/)
```

| Problem | Fix |
|---|---|
| "Connection closed" | Check stdio command works manually, verify env vars |
| "Unable to connect" | Verify URL, check firewall, increase timeout: `MCP_TIMEOUT=30000 claude` |
| "Auth failed" | `/mcp` → clear auth → re-authenticate |
| Tools consume too much context | `ENABLE_TOOL_SEARCH=auto:5 claude` |
| Output too large | `MAX_MCP_OUTPUT_TOKENS=50000` |

### Key Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `MCP_TIMEOUT` | 500ms | Server startup timeout |
| `MCP_TOOL_TIMEOUT` | — | Tool execution timeout |
| `MAX_MCP_OUTPUT_TOKENS` | 25000 | Max output per tool call |
| `ENABLE_TOOL_SEARCH` | auto:10 | Tool search activation threshold |
| `MCP_DEBUG` | — | Enable debug logging |

---

## 4. FEEDBACK AND AGENT LEARNING

### In Claude Code (Lab)

**Persistent Memory** — the primary feedback mechanism:

Agents with `memory: project` (or `user`) maintain a `MEMORY.md` file that persists across sessions:

```yaml
---
name: strategist
memory: project
---

You are a content strategist. Before starting any task, read your memory
for accumulated learnings. After completing a task, update your memory
with what worked and what didn't.
```

After each run, you tell the agent: "The hook was too generic, next time lead with a specific number." The agent writes this to its `MEMORY.md`. Next session, it reads this memory and applies the lesson.

Over time, MEMORY.md accumulates:
```markdown
## Content Strategy Learnings

### Hooks
- Lead with specific numbers ("15% increase" not "significant increase")
- Ask a question the reader recognizes from their own experience
- Avoid generic industry buzzwords

### CTAs
- "Comment your domain" outperforms "DM me"
- Free audit offers get 3x more engagement than whitepaper downloads

### Platform-Specific
- LinkedIn: keep under 1300 chars, use line breaks every 2 sentences
- Blog: H2 every 200-300 words, include data tables
```

**Knowledge File Updates** — update the source material:

Edit `knowledge/hormozi_principles.md` or `knowledge/priestley_principles.md` directly with new learnings. These are read every time the agent runs.

**Skill Refinement** — update the workflow:

Edit `SKILL.md` files based on what produces good results. The skill IS the process — refining it is refining the agent's approach.

**Interactive Correction** — real-time in conversation:

You're in the loop. Say "make it punchier" or "the CTA should be about audits, not whitepapers" and Claude adjusts immediately. This is the fastest feedback loop.

### In CrewAI (Production)

**Human Input on Tasks**:

```yaml
# tasks.yaml
create_strategy:
  description: ...
  expected_output: ...
  agent: content_strategist
  human_input: true              # pauses and asks for feedback before finishing
```

The agent drafts output, shows it to you, and waits for approval or corrections before finalizing.

**CrewAI Memory System**:

```python
@crew
def crew(self) -> Crew:
    return Crew(
        agents=self.agents,
        tasks=self.tasks,
        memory=True,                     # enables all memory types
        verbose=True,
    )
```

CrewAI memory types:
- **Short-term**: context within the current run
- **Long-term**: task results stored for future runs (learns what worked)
- **Entity memory**: remembers facts about people, companies, concepts

When `memory=True`, the crew remembers outcomes from previous runs and applies those learnings to new ones.

**Knowledge Source Updates**:

Same as Claude Code — update the markdown files or swap the loader function to pull from Supabase. The content shapes the agent's expertise.

**Output Validation with Pydantic**:

```python
@task
def create_strategy(self) -> Task:
    return Task(
        config=self.tasks_config["create_strategy"],
        output_pydantic=ContentStrategy,     # rejects output that doesn't match schema
    )
```

This enforces structure but not quality. For quality feedback, combine with `human_input: true`.

**Guardrails** (coming in newer CrewAI versions):

Pre/post task validation functions that check output quality before accepting it.

### The Feedback Transfer Path

```
Claude Code Lab                          CrewAI Production
───────────────                          ──────────────────
MEMORY.md (accumulated learnings)  →     Agent backstory refinements
Refined SKILL.md instructions      →     Task YAML description improvements
Updated knowledge files            →     Same knowledge files (or Supabase)
Interactive corrections            →     human_input: true on tasks
Your intuition about what works    →     Guardrails and validation rules
```

The lab is where you discover what good output looks like. Production is where you encode that into repeatable, automated rules.

---

## 5. MAPPING: CLAUDE CODE to CREWAI

| Claude Code | CrewAI | Same? |
|---|---|---|
| `.claude/agents/strategist.md` (system prompt) | `crews/strategist/config/agents.yaml` (role, goal, backstory) | Yes — same content, different format |
| `.claude/skills/linkedin/SKILL.md` (workflow) | `crews/*/config/tasks.yaml` + `flow.py` (task + orchestration) | Equivalent |
| `knowledge/*.md` (read by agent) | `StringKnowledgeSource` (RAG via ChromaDB) | Same content, different delivery |
| `~/.claude/settings.json` (MCP servers) | `mcps=[]` on Agent constructor | Same servers, same protocol |
| `memory: project` (MEMORY.md) | `memory=True` on Crew (long-term) | Equivalent concept |
| `allowed-tools` | `tools=[]` on Agent | Same |
| Interactive feedback (you in conversation) | `human_input: true` on Task | Equivalent |
| Agent Teams (multi-instance) | Multi-crew Flows with `@listen` chains | Equivalent orchestration |

---

## 6. CMO LAB SETUP (Recommended Files)

### Agents

**`.claude/agents/strategist.md`**:
```yaml
---
name: strategist
description: Content strategist expert in B2B SaaS marketing. Use for creating content strategies grounded in Hormozi and Priestley frameworks.
tools: Read, Grep, Glob
model: sonnet
maxTurns: 10
memory: project
---

You are a senior content strategist with deep expertise in B2B SaaS marketing.
[Full personality and instructions from strategist agents.yaml]
```

**`.claude/agents/copywriter.md`**:
```yaml
---
name: copywriter
description: Senior copywriter for B2B technology content. Writes final content pieces from strategies.
tools: Read, Grep, Glob
model: opus
maxTurns: 8
memory: project
---

You are an experienced copywriter who specializes in B2B technology content.
[Full personality and instructions from copywriter agents.yaml]
```

### Skills

**`.claude/skills/linkedin/SKILL.md`**:
```yaml
---
name: linkedin
description: Create a LinkedIn post about a topic for a target audience
context: fork
agent: strategist
allowed-tools: Read, Grep
---

## Context
- Company: !`cat config/bison.yaml`
- Knowledge: !`cat products/cmo/knowledge/hormozi_principles.md`
- Knowledge: !`cat products/cmo/knowledge/priestley_principles.md`

## Task
Create a LinkedIn post about "$0" targeting $1.

Steps:
1. Analyze the topic using Hormozi's value equation and Priestley's oversubscribed method
2. Create a content strategy (angle, key points, tone, CTA, platform guidelines)
3. Write a publish-ready LinkedIn post (max 1300 chars)
4. Save to output/cmo/linkedin_!`date +%Y%m%d`.md
```

### MCP Connections

**`.mcp.json`** (project-level):
```json
{
  "mcpServers": {
    "supabase": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server", "--supabase-url", "${SUPABASE_URL}", "--supabase-key", "${SUPABASE_KEY}"]
    }
  }
}
```

**`~/.claude.json`** (personal, all projects):
```json
{
  "mcpServers": {
    "google-docs": {
      "type": "http",
      "url": "https://mcp.google.com/docs"
    },
    "notion": {
      "type": "http",
      "url": "https://mcp.notion.com/mcp"
    }
  }
}
```

---

## 7. BUILDING YOUR OWN MCP SERVER (for Bison AEO)

To expose the Bison AEO API as an MCP server:

**Python SDK** (recommended):

```python
import mcp.server.stdio
from mcp.types import Tool, TextContent
from mcp.server import Server

server = Server("bison-aeo")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="analyze_prompt",
            description="Analyze a single prompt for brand visibility in AI answers",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string"},
                    "prompt_text": {"type": "string"},
                    "language": {"type": "string", "default": "en"}
                },
                "required": ["company_id", "prompt_text"]
            }
        ),
        Tool(
            name="company_report",
            description="Generate a full company visibility report across all prompts",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {"type": "string"}
                },
                "required": ["company_id"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "analyze_prompt":
        # Call Bison AEO API
        response = requests.post(
            "https://bison-aeo-api.com/analyze/prompt-analysis-report",
            json=arguments
        )
        return [TextContent(type="text", text=json.dumps(response.json()))]

if __name__ == "__main__":
    mcp.server.stdio.serve(server)
```

Register in Claude Code:
```bash
claude mcp add --transport stdio bison-aeo -- python bison_mcp_server.py
```

Now any agent can query Bison AEO data naturally: "Check how Bison is mentioned in AI answers for 'best AEO tools'."

---

## 8. VERIFICATION CHECKLIST

1. Create `.claude/agents/strategist.md` and `.claude/agents/copywriter.md`
2. Create `.claude/skills/linkedin/SKILL.md`
3. Run `/linkedin "how AI is transforming SEO" "marketing managers"`
4. Verify agent uses knowledge files and produces structured strategy
5. Verify copywriter produces publish-ready content
6. Check `.claude/agent-memory/strategist/MEMORY.md` exists after providing feedback
7. Configure at least one MCP server (Supabase) and verify `/mcp` shows it connected
8. Test that feedback given in one session appears in agent memory in the next session
