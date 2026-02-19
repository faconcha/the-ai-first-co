# The AI-First Co

AI agent products for businesses, built on CrewAI. Each "product" (CMO, CFO, Legal, etc.) is a set of agents orchestrated by a Flow.

## Two-Track Development Model

Every feature starts as a **Claude Code workflow** (local, zero-cost, fast to iterate) and graduates to a **CrewAI product** when production-ready.

| | Claude Code (`claude/`) | CrewAI (`crews/` + `flow.py`) |
|---|---|---|
| **Where** | `products/<name>/claude/` | `products/<name>/crews/`, `flow.py` |
| **Triggered by** | Claude Code skills, subagents, local scripts | `main.py` CLI → CrewAI Flow |
| **Cost** | Zero (no LLM API calls) | Billed per LLM call |
| **Purpose** | Prototyping, data pipelines, orchestration scripts | Production agent workflows |
| **Runtime** | Your machine, Claude Code session | Any machine, schedulable |

**Rule:** Start in `claude/`. Move to CrewAI only when the feature is stable and needs production deployment.

## Architecture

```
config/                    → Shared YAML configs (LLM profiles, company context)
shared/                    → Thin utilities (settings loader, LLM profile resolver)
products/<name>/           → Each product folder
  claude/                  → Claude Code-only: scripts, pipelines, skills implementation
  crews/                   → CrewAI: crew definitions and agent configs
  flow.py                  → CrewAI: Flow orchestrator
  knowledge/               → Shared: domain knowledge markdown files
.claude/skills/            → Claude Code skill definitions (project-wide)
output/                    → Generated content per product (gitignored)
```

**No platform wrapper.** Products use CrewAI directly. The shared layer is only config loading and LLM profiles.

## Running a Product

```bash
uv run python main.py cmo --topic "..." --audience "..." --platform linkedin --language en
```

## LLM Profiles

Defined in `config/llm.yaml`. Agents reference profiles by name, not specific models:
- `fast` → cheap/quick tasks
- `smart` → reasoning tasks
- `creative` → content generation

Usage in crew code: `llm_config.get_llm("smart")`

To change which model a profile uses, edit `config/llm.yaml`. All agents using that profile update automatically.

## How to Add a New Product

1. Create `products/<name>/` with this structure:
```
products/<name>/
├── __init__.py
├── claude/              # Claude Code-only: scripts, pipelines, orchestration
│   └── __init__.py
├── flow.py              # CrewAI Flow orchestrator
├── crews/
│   ├── __init__.py
│   └── <crew_name>/
│       ├── __init__.py
│       ├── <crew_name>_crew.py
│       └── config/
│           ├── agents.yaml
│           └── tasks.yaml
└── knowledge/           # Optional: markdown files with domain knowledge
```

Start by building the feature in `claude/` first. Once stable, implement it in `crews/` + `flow.py` for production.

2. In `flow.py`, create a Flow class with Pydantic state:
```python
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

class MyFlowState(BaseModel):
    # inputs and intermediate results
    ...

class MyFlow(Flow[MyFlowState]):
    @start()
    def first_step(self):
        ...

    @listen(first_step)
    def next_step(self):
        result = MyCrew().crew().kickoff(inputs={...})
        self.state.result = result.raw
```

3. Register in `main.py`: add a subparser and run function.

## How to Add a New Agent/Crew to an Existing Product

1. Create `products/<product>/crews/<new_crew>/` with config/ YAML + crew.py
2. Follow the `@CrewBase` pattern (see existing crews for reference)
3. Add a `@listen` step in the product's `flow.py` that runs the new crew

## How to Add Tools

CrewAI tools can be added to any agent:

```python
from crewai.tools import tool

@tool("Tool Name")
def my_tool(input: str) -> str:
    """Tool description."""
    # implementation
    return result
```

Assign to an agent: `tools=[my_tool]` in the agent constructor.

## How to Add MCP Connections

CrewAI supports MCP natively on agents:

```python
from crewai import Agent

agent = Agent(
    role="...",
    goal="...",
    backstory="...",
    mcps=[
        {
            "type": "sse",
            "url": "http://localhost:8000/sse",
        }
    ],
)
```

## How to Connect N8N

N8N connects via webhooks. Pattern:
1. Create a webhook trigger in N8N
2. Create a CrewAI tool that calls the webhook URL
3. Assign the tool to the relevant agent

The tool sends data to N8N, which runs the workflow and returns results.

## Observability (LangSmith)

Set in `.env`:
```
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=the-ai-first-co
LANGCHAIN_TRACING_V2=true
```

No code changes needed. All agent runs are traced automatically.

## Coding Rules

- Imports at the top of every file, never inside functions or classes
- Call methods from imported packages (e.g., `settings.get_company_config()`, not `from shared.settings import get_company_config`)
- No mock code, ever. Everything must be real and functional
- Keep code simple. Minimal prints in main files
- When creating examples, mirror the source code folder structure under `examples/`
- For "local examples", use `local_example/` at project root: clean it, run, save output to text file
