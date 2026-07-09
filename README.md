# Grant Copilot

A Slack agent that helps nonprofits **find, track, and apply to U.S. federal grants** — without leaving Slack.

Built for the **Slack Agent Builder Challenge** (track: *Slack Agent for Good*).

## What it does

- **Discover** — describe your mission in the Assistant pane; the agent searches live grants.gov data and explains *why each grant fits*.
- **Qualify** — set an organization profile (applicant type + focus areas) once; every search is then filtered to grants your org is actually eligible for.
- **Track** — save grants to an App Home pipeline (*To apply / In progress / Submitted*) and get a DM reminder before each deadline.
- **Draft** — generate a first-pass *Project Summary*, grounded in the opportunity's own text so nothing is invented.

## How it works

```
Assistant pane ──► Bolt app ──► Agent orchestrator (Mistral tool-use)
                                        │
                                        ▼
                              Custom MCP server (stdio)
                                        │
                                        ▼
                          grants.gov Search2 API (public, no key)
```

Two design decisions carry the reliability:

1. **The LLM only picks the search keyword.** Eligibility filters (`eligibilities`, `fundingCategories`) are injected deterministically from the org profile when the tool call executes — a small model can't get them wrong.
2. **The MCP server is a standalone process** exposing `search_grants` and `get_grant`. It is the only module that knows grants.gov, so it is testable in isolation and new funding sources plug in without touching the agent.

## Project structure

```
src/grant_copilot/
  mcp_server.py   MCP server: search_grants / get_grant tools (FastMCP, stdio)
  agent/          Mistral orchestration — search loop, curation, draft writer
  domain/         models + repository interfaces (no Slack, no HTTP)
  grants/         grants.gov client, record mapper, facet taxonomy
  infra/          SQLite repositories, deadline reminder scheduler
  slack/          Bolt surfaces — Assistant, App Home, Block Kit, modals
```

## Stack

Python 3.14 · uv · Slack Bolt (Socket Mode) · MCP (FastMCP) · Mistral Small · SQLite · APScheduler

## Setup

1. Install dependencies: `uv sync`
2. Create a Slack app from `manifest.json` (Slack Developer Program sandbox), install it to your workspace, and grab the bot token (`xoxb-…`) and app-level token (`xapp-…`, Socket Mode).
3. Copy `.env.example` to `.env` and fill in the tokens plus a [Mistral API key](https://console.mistral.ai).

## Run

```
uv run grant-copilot          # or: uv run python -m grant_copilot
```

Then open the app in Slack: chat in the **Assistant pane** to search, open the **Home tab** to manage your pipeline and org profile.

## Smoke tests

```
uv run python scripts/spike_grants_gov.py "clean water"   # data path — public API, no key needed
uv run python scripts/spike_mcp_client.py                 # MCP server round-trip
uv run python scripts/spike_mistral_tools.py              # needs MISTRAL_API_KEY
```

---

*[PLAN.md](PLAN.md) is the internal build journal (in French); the app and all submission deliverables are in English.*
