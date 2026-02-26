---
name: agentize-poc-architecture
description: Architecture guide for the agentize.eu Enterprise AI Platform PoC. Covers system overview, key design decisions, request flow, project structure, and 10-day implementation order. Use when designing new features, understanding component interactions, or planning PoC implementation steps.
---

# agentize.eu PoC — Architecture & Design

## What This PoC Does

Enterprise AI platform that generates TWI (Training Within Industry) work instructions via a **Microsoft Teams + Telegram bot**, running in the customer's Azure subscription (Sweden Central, EU Data Zone Standard).

## Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| No RAG/AI Search | User input only | Documents are generated from user input, not retrieved |
| No hallucination framework | Multi-step approval workflow | Review + Final Approval replaces confidence scoring |
| Output format | PDF (WeasyPrint) | Primary deliverable format required by client |
| Multi-channel | Bot Framework (Teams + Telegram) | Native multi-channel support, +1 channel = config toggle |
| IP protection | Resource group + explicit RBAC | No Managed App wrapper needed for PoC |
| Token costs | Agent vendor pays | Platform infra is fixed cost; LLM consumption is vendor's |

## High-Level Components

```
Teams / Telegram
  └── Azure Bot Service (channel routing)
        └── FastAPI (Container App, VNET)
              ├── LangGraph Agent (intent → generate → review → approve → PDF)
              ├── Azure AI Foundry (Mistral Large / GPT-4o, Data Zone Standard)
              ├── Cosmos DB (MongoDB API) — state + audit
              └── Blob Storage — PDF output
```

## Request Flow (Happy Path)

1. User sends message → Bot Service routes to `/api/messages`
2. FastAPI → `BotFrameworkAdapter` → `AgentizeBotHandler.on_message_activity()`
3. Bot handler → `run_agent()` → LangGraph graph invocation
4. **Intent node** classifies: `generate_twi | edit_twi | question | unknown`
5. **Generate node** → AI Foundry (Mistral Large, temp=0.3) → draft + AI label
6. **Review checkpoint** (INTERRUPT) → Adaptive Card sent to user
7. User approves/edits → Bot handler resumes graph with `resume_from`
8. **Final approval checkpoint** (INTERRUPT) → second confirmation
9. **Output node** → WeasyPrint PDF → Blob Storage → SAS URL (24h)
10. **Audit node** → Cosmos DB log entry
11. Bot sends Result Card with download link

## EU AI Act Compliance

Every AI output automatically includes:
> `⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.`

## Project Structure

```
poc-backend/
├── app/
│   ├── main.py            # FastAPI + /api/messages endpoint
│   ├── config.py          # pydantic-settings (all env vars)
│   ├── bot/               # Bot Framework handler + Adaptive Cards
│   ├── agent/             # LangGraph graph, nodes, state, prompts, tools
│   ├── services/          # ai_foundry, cosmos_db, blob_storage, key_vault
│   ├── models/            # Pydantic data models
│   └── templates/         # Jinja2 HTML → PDF templates
├── tests/
├── infra/                 # Bicep templates
└── Dockerfile
```

## 10-Day Implementation Order

| Days | Focus | Validation Gate |
|------|-------|----------------|
| 1–2 | Bicep infra deploy (all Azure resources) | AI Foundry responds, all resources reachable |
| 3–4 | Backend core: config, services, intent+generate nodes, base graph | pytest: intent + generation working |
| 5–6 | Bot Framework + Adaptive Cards + channel registration | Teams message → Adaptive Card response |
| 7–8 | Human-in-the-loop: review/revise/approve nodes + interrupt | Full flow: generate → review → edit → approve |
| 9 | PDF generation, output+audit nodes, Docker build | PDF downloadable, audit log in Cosmos DB |
| 10 | End-to-end tests (Teams + Telegram) + demo prep | Demo script runs without errors |

## Environment Variables

See `.env.example` — key vars:
- `AI_FOUNDRY_ENDPOINT` + `AI_FOUNDRY_KEY` — AI Foundry inference endpoint
- `COSMOS_CONNECTION` — MongoDB API connection string
- `BLOB_CONNECTION` + `BLOB_CONTAINER=pdf-output`
- `BOT_APP_ID` + `BOT_APP_PASSWORD` — Entra ID App Registration
- `TELEGRAM_BOT_TOKEN` — optional

## Additional Resources

- For LangGraph agent details, see the `agentize-poc-langgraph` skill
- For Bicep infrastructure, see the `agentize-poc-azure-infra` skill
- For Bot Framework and Adaptive Cards, see the `agentize-poc-bot-cards` skill
- Full spec: `poc_technical_spec.md`
