# agentize.eu PoC — TWI Work Instruction Generator

Enterprise AI platform proof-of-concept that generates structured **TWI (Training Within Industry)** work instructions via a Microsoft Teams and Telegram chatbot. A LangGraph agent orchestrates multi-step human-in-the-loop approval before producing final PDF output, with full EU AI Act transparency labeling and audit trail.

| Field | Value |
|---|---|
| **Status** | PoC — Implemented |
| **Region** | Sweden Central (EU Data Zone Standard) |
| **Runtime** | Python 3.12, FastAPI, LangGraph |
| **Channels** | Microsoft Teams, Telegram |
| **Spec** | [`specification.md`](specification.md) v1.4 |
| **Deployment** | [`INSTALL.md`](INSTALL.md) |

---

## Architecture

```
Teams / Telegram
  └── Azure Bot Service
        └── FastAPI (Azure Container App, VNET)
              ├── LangGraph Agent
              │     classify_intent
              │       ├── generate_twi / edit_twi → process_input → generate → review [INTERRUPT]
              │       ├── question → generate → review [INTERRUPT]
              │       └── unknown → clarify → END
              │     review
              │       ├── approved → approve [INTERRUPT] → output → audit → END
              │       ├── revision_requested → revise → generate (max 3 loops)
              │       └── rejected → reject → audit → END
              │
              ├── Azure AI Foundry (GPT-4o / Mistral Large, Data Zone Standard)
              ├── Cosmos DB (MongoDB API) — state, audit, documents
              └── Blob Storage — PDF output (SAS URL, 24h expiry)
```

Two human-in-the-loop interrupt points enforce review and explicit final approval before any PDF is generated, as required by EU AI Act compliance.

---

## Project Structure

```
TWI_POC/
├── poc-backend/                 Python backend (FastAPI + LangGraph)
│   ├── app/
│   │   ├── main.py              FastAPI app, /api/messages endpoint
│   │   ├── config.py            pydantic-settings configuration
│   │   ├── agent/
│   │   │   ├── graph.py         LangGraph StateGraph definition
│   │   │   ├── state.py         AgentState TypedDict
│   │   │   ├── mongodb_checkpointer.py   Cosmos DB checkpoint persistence
│   │   │   ├── nodes/           One file per graph node
│   │   │   │   ├── intent.py    Intent classification (temp=0.1)
│   │   │   │   ├── process_input.py  Structured input extraction
│   │   │   │   ├── generate.py  TWI draft generation (temp=0.3)
│   │   │   │   ├── review.py    Review interrupt node
│   │   │   │   ├── revise.py    Revision handling
│   │   │   │   ├── approve.py   Final approval interrupt node
│   │   │   │   ├── output.py    PDF generation + Blob upload
│   │   │   │   ├── audit.py     Cosmos DB audit trail
│   │   │   │   └── clarify.py   Unknown intent response
│   │   │   └── tools/
│   │   │       └── pdf_generator.py  Jinja2 + WeasyPrint PDF pipeline
│   │   ├── bot/
│   │   │   ├── bot_handler.py   AgentizeBotHandler (message routing)
│   │   │   └── adaptive_cards.py  4 card templates (review, approval, result, welcome)
│   │   ├── models/              Pydantic data models
│   │   ├── services/            Azure service clients (AI Foundry, Cosmos, Blob, Key Vault)
│   │   ├── locale/              i18n strings (Hungarian, English)
│   │   └── templates/
│   │       └── twi_template.html  Jinja2 PDF template
│   ├── infra/
│   │   ├── main.bicep           Azure infrastructure-as-code
│   │   ├── deploy.ps1           Automated deployment (PowerShell)
│   │   ├── deploy.sh            Automated deployment (Bash)
│   │   └── validate.ps1         Post-deployment validation
│   ├── tests/                   pytest test suite
│   ├── Dockerfile               Production container image
│   ├── pyproject.toml           Python project metadata
│   ├── requirements.txt         Dependency floors
│   └── requirements.lock        Pinned versions for Docker builds
├── teams-app/                   Teams manifest + icons
├── .github/workflows/
│   └── deploy.yml               CI/CD (lint, test, build, deploy)
├── specification.md             Implementation specification (v1.4)
├── INSTALL.md                   Step-by-step deployment guide
├── go_live_guide.md             Quick deployment reference
└── PETER_GAP.md                 Gap analysis vs platform spec
```

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.12+
- Azure CLI (`az --version`)
- An Azure subscription with deployed infrastructure (see [INSTALL.md](INSTALL.md))

### Setup

```bash
cd poc-backend

# Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Copy environment template and fill in real values
cp .env.example .env
# Edit .env with your Azure connection strings
```

### Run

```bash
cd poc-backend
uvicorn app.main:app --reload --port 8000
```

Endpoints:

| Endpoint | Description |
|---|---|
| `GET /` | Service info |
| `GET /health` | Health check |
| `GET /docs` | Swagger UI (only in `poc` / `development` environments) |
| `POST /api/messages` | Bot Framework messaging endpoint |

### Run Tests

```bash
cd poc-backend
pytest tests/ -v
```

Integration tests (require `COSMOS_CONNECTION`) are skipped by default. To run them:

```bash
COSMOS_CONNECTION="mongodb://localhost:27017/" pytest tests/test_checkpoint_integration.py -v
```

---

## Azure Deployment

The infrastructure is defined in a single Bicep template and deployed via an automated script that handles Entra ID App Registration, resource provisioning, Key Vault secrets, and `.env` generation.

```powershell
cd poc-backend/infra
az login
.\deploy.ps1
```

For detailed step-by-step instructions including prerequisites, troubleshooting, Teams app setup, Telegram configuration, and CI/CD pipeline setup, see **[INSTALL.md](INSTALL.md)**.

### Azure Resources Created

| Resource | Name | Purpose |
|---|---|---|
| Container App | `ca-agentize-poc-backend` | FastAPI backend |
| AI Foundry | `ai-agentize-poc` | LLM inference (DataZoneStandard) |
| Cosmos DB | `cosmos-agentize-poc` | State, audit, documents |
| Blob Storage | `stagentizepoc` | PDF output |
| Key Vault | `kv-agentize-poc` | Secret management |
| Bot Service | `bot-agentize-poc` | Teams + Telegram channel routing |
| VNET | `vnet-agentize-poc` | Network isolation |

All resources deploy to **Sweden Central** for EU data residency compliance.

---

## Environment Variables

All configuration is managed via `pydantic-settings` and loaded from `poc-backend/.env`. See [`poc-backend/.env.example`](poc-backend/.env.example) for the full template.

| Variable | Required | Default | Description |
|---|---|---|---|
| `AI_FOUNDRY_ENDPOINT` | Yes | — | Azure AI Foundry inference endpoint |
| `AI_FOUNDRY_KEY` | Yes | — | AI Foundry API key |
| `AI_MODEL` | No | `gpt-4o` | Model deployment name |
| `AI_TEMPERATURE` | No | `0.3` | LLM temperature (keep <= 0.3) |
| `COSMOS_CONNECTION` | Yes | — | Cosmos DB (MongoDB API) connection string |
| `BLOB_CONNECTION` | Yes | — | Azure Blob Storage connection string |
| `BOT_APP_ID` | Yes | — | Entra ID App Registration Client ID |
| `BOT_APP_PASSWORD` | Yes | — | Entra ID App Registration Client Secret |
| `TELEGRAM_BOT_TOKEN` | No | — | Telegram bot token (optional channel) |
| `ENVIRONMENT` | No | `poc` | Environment flag (`poc`, `development`, `production`) |

---

## EU AI Act Compliance

Every AI-generated output carries mandatory transparency labels:

- **In drafts and bot messages:** `⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.`
- **In PDF footer:** `agentize.eu — AI által generált tartalom — {page}/{pages}`
- **In Adaptive Cards:** model name and generation timestamp

Two mandatory human checkpoints (`review` and `approve`) must be passed before any PDF is generated. The audit trail logs all events to the `audit_log` Cosmos DB collection with user ID, tenant ID, channel, model, token counts, approval timestamp, and revision count.

---

## CI/CD

GitHub Actions workflow (`.github/workflows/deploy.yml`) triggers on pushes to `main` that touch `poc-backend/`:

1. **Lint** — `ruff check` + `ruff format --check`
2. **Test** — `pytest`
3. **Build** — Docker image pushed to GitHub Container Registry
4. **Deploy** — Azure Container App updated with new image
5. **Health check** — `/health` endpoint verified

Requires the `AZURE_CREDENTIALS` GitHub repository secret (Service Principal JSON).

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **LangGraph** (not LangChain chains) | GA, production-ready, native interrupt support |
| **No RAG / AI Search** | Agent generates from user input, not document retrieval |
| **Sweden Central, DataZoneStandard** | EU data residency guarantee for automotive clients |
| **Bot Framework** | Multi-channel (Teams + Telegram) with stable SDK |
| **PDF as primary output** | Matches existing TWI delivery format |
| **Multi-checkpoint approval** | EU AI Act human-in-the-loop instead of confidence scoring |
| **Cosmos DB (MongoDB API)** | Serverless, graph checkpointing, audit trail |

---

## Documentation Index

| Document | Description |
|---|---|
| [`specification.md`](specification.md) | Full implementation specification (v1.4) |
| [`INSTALL.md`](INSTALL.md) | Detailed deployment guide (Phase 0-9) |
| [`go_live_guide.md`](go_live_guide.md) | Quick deployment reference |
| [`PETER_GAP.md`](PETER_GAP.md) | Gap analysis: PoC vs platform spec |
| [`codebase_snapshot.md`](codebase_snapshot.md) | Full file tree and tech stack reference |
| [`.cursor/skills/`](.cursor/skills/) | Agent skills for Cursor AI (architecture, infra, bot, LangGraph) |
| [`.cursor/rules/`](.cursor/rules/) | Cursor AI rules (patterns, conventions, compliance) |

---

## License

Internal / Confidential — agentize.eu
