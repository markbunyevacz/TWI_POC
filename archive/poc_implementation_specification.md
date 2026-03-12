> **[ARCHIVED — 2026-03-12]**
> This document is a strict subset of `specification.md` v1.1 (2026-03-12).
> All content here (sections 1 & 2) exists in the authoritative spec with
> equal or greater detail. Kept for historical reference only.

# agentize.eu PoC — Implementation Specification

**Version:** 1.0
**Date:** 2026-03-12
**Status:** ARCHIVED — redundant, merged into `specification.md` v1.1
**Scope:** TWI (Training Within Industry) Work Instruction Generator — Enterprise AI Platform PoC

---

## Table of Contents

1. [User Functionalities & Workflows](#1-user-functionalities--workflows)
2. [Architecture & Technology Stack](#2-architecture--technology-stack)

---

## 1. User Functionalities & Workflows

The PoC implements a TWI (Training Within Industry) work instruction generator accessible via Microsoft Teams and Telegram. The following sections describe each step of the user journey.

### 1.1 Onboarding

When a user adds the bot in Teams or Telegram, they receive a Welcome card introducing the AI assistant and showing an example prompt such as *"Készíts egy TWI utasítást a CNC-01 gép beállításáról"*.

### 1.2 Message Submission & Intent Classification

The user sends a natural-language request. The bot responds with *"⏳ Feldolgozom a kérésedet..."* and the LangGraph agent classifies the intent (at `temperature=0.1`) into one of four categories:

| Intent | Behaviour |
|---|---|
| `generate_twi` | New TWI work instruction generation |
| `edit_twi` | Modify an existing TWI |
| `question` | General Q&A (skips input processing) |
| `unknown` | Clarification prompt sent back to user |

### 1.3 TWI Draft Generation

For `generate_twi` / `edit_twi`, the input is structured and sent to the LLM (`temperature=0.3`) with a system prompt enforcing a 6-section TWI format:

1. **CÍM** — Title
2. **CÉL** — Objective
3. **SZÜKSÉGES ANYAGOK ÉS ESZKÖZÖK** — Materials & Tools
4. **BIZTONSÁGI ELŐÍRÁSOK** — Safety
5. **LÉPÉSEK** — Steps (with main step, key points, rationale)
6. **MINŐSÉGI ELLENŐRZÉS** — Quality check

The EU AI Act label `⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges.` is automatically prepended to every draft.

### 1.4 Human-in-the-Loop #1: Draft Review

The graph interrupts and sends the user a Review Adaptive Card containing:

- The draft (truncated to 2,000 chars for card limits)
- EU AI Act metadata: *"⚠️ AI által generált tartalom | Modell: {model} | Generálva: {timestamp}"*
- An optional feedback text field
- Three actions:

| Action | Result |
|---|---|
| **Jóváhagyom a vázlatot** | Moves to final approval |
| **Szerkesztés kérem** | Enters revision loop |
| **Elvetés** | Discards draft, ends flow |

### 1.5 Revision Loop

When the user requests edits, their feedback is injected into the LLM prompt alongside the previous draft. The agent regenerates and presents a new Review card. This loop is capped at 3 rounds — after the third revision, the flow forces a move to final approval.

```
generate → [Review Card] → edit requested → revise → generate → [Review Card] → ...
                                                                  (max 3 rounds)
```

### 1.6 Human-in-the-Loop #2: Final Approval

After the user approves the draft, a Final Approval Adaptive Card appears with an explicit verification message:

> *"Ez a dokumentum AI által generált tartalom. Kérlek ellenőrizd a tartalmat, mielőtt véglegesíted."*

Two actions:

| Action | Result |
|---|---|
| **Ellenőriztem és jóváhagyom** | Triggers PDF generation |
| **Vissza a szerkesztéshez** | Returns to revision loop |

This second checkpoint is mandatory per EU AI Act — no PDF can be generated without it.

### 1.7 PDF Generation & Delivery

Upon final approval:

1. Draft markdown is converted to HTML via Jinja2 template (A4 format with agentize.eu branding)
2. HTML is rendered to PDF via WeasyPrint
3. PDF is uploaded to Azure Blob Storage
4. A 24-hour SAS URL is generated
5. A Result Adaptive Card is sent with the download link, showing document title, format, model used, and approver

The PDF includes:

- Header with title, generation date, model, version
- EU AI Act warning box
- Full TWI content
- Approval box (who approved, when)
- Footer on every page: *"agentize.eu — AI által generált tartalom — {page}/{pages}"*

### 1.8 Audit Trail

After PDF delivery, the audit node logs to Cosmos DB:

- `user_id`, `tenant_id`, `channel`
- `llm_model`, `llm_tokens_input`, `llm_tokens_output`
- `approval_timestamp` (ISO 8601 UTC)
- `revision_count`
- `pdf_blob_name`, `status`

This is invisible to the user but supports EU AI Act traceability requirements.

### 1.9 Telegram Variant

Since Telegram does not support Adaptive Cards, the bot formats the same workflow as markdown text messages with text-based options (`Igen/Nem`, `Módosítás`). The approval flow on Telegram skips the second card and goes directly to PDF generation after the user explicitly approves.

### 1.10 Complete Workflow Diagram

```
[User message]
     │
     ▼
 intent_node ──── unknown ──→ "Kérlek pontosítsd..." → END
     │
     ├── generate_twi / edit_twi
     │         │
     │    process_input → generate → [INTERRUPT #1: Review Card]
     │                                    │          │           │
     │                               approve    request_edit   reject → END
     │                                    │          │
     │                                    │     revise → generate → [Review Card]
     │                                    │              (max 3 rounds)
     │                                    ▼
     │                          [INTERRUPT #2: Approval Card]
     │                                    │
     │                              final_approve
     │                                    │
     │                              output (PDF) → audit → END
     │                                    │
     │                              [Result Card + PDF link]
     │
     └── question → generate (Q&A) → END
```

### 1.11 EU AI Act Compliance Summary

| Requirement | Implementation |
|---|---|
| In-text label | Prepended to draft in `generate_node` |
| PDF footer | `twi_template.html`: "agentize.eu — AI által generált tartalom — {page}/{pages}" |
| Adaptive Card label | "⚠️ AI által generált tartalom \| Modell: {model} \| Generálva: {generated_at}" |
| Two approval checkpoints | `interrupt_before=["review", "approve"]` in graph compilation |
| Audit trail | `audit_node` logs to `audit_log` collection with model, tokens, approval timestamp |
| LLM temperature | Intent: 0.1; TWI generation: 0.3 |

---

## 2. Architecture & Technology Stack

### 2.1 High-Level Architecture

The solution runs entirely within the customer's own Azure subscription inside a VNET in Sweden Central (EU Data Zone Standard guarantee). It consists of 11 Azure resources orchestrated by a single Bicep template.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    AZURE VNET — Sweden Central                       │
│                                                                      │
│  ┌───────────┐     ┌─────────────────────┐     ┌─────────────────┐  │
│  │ Azure Bot │────▶│ Container App       │────▶│ Azure AI        │  │
│  │ Service   │     │ (FastAPI+LangGraph) │     │ Foundry         │  │
│  │ (global)  │     │ port 8000           │     │ (GPT-4o /       │  │
│  └─────┬─────┘     └──────┬──────┬───────┘     │  Mistral Large) │  │
│        │                  │      │              └─────────────────┘  │
│  ┌─────┴──────┐    ┌──────┴───┐  ├──────────┐                      │
│  │ Teams /    │    │ Cosmos DB│  │ Blob     │   ┌────────────────┐  │
│  │ Telegram   │    │ (MongoDB │  │ Storage  │   │ Key Vault      │  │
│  │ Channels   │    │  API)    │  │ (PDF)    │   │ (secrets)      │  │
│  └────────────┘    └─────────┘  └──────────┘   └────────────────┘  │
│                                                                      │
│  ┌──────────────────┐     ┌────────────────┐                        │
│  │ App Insights +   │     │ Entra ID       │                        │
│  │ Log Analytics    │     │ (SSO / Auth)   │                        │
│  └──────────────────┘     └────────────────┘                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Network & Security Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Virtual Network | Azure VNET (`10.0.0.0/16`) | Network isolation for all resources |
| Subnet: `snet-container-apps` | `/23` (256+ IPs) | Delegated to Container Apps Environment |
| Subnet: `snet-private-endpoints` | `/24` | Reserved for private endpoint hardening (MVP) |
| NSG | Network Security Group | Allows HTTPS + Bot Service inbound; denies everything else |
| Entra ID | Microsoft Identity Platform | SingleTenant app registration; JWT token validation on `/api/messages` |
| Key Vault | Azure Key Vault (RBAC-enabled) | Stores all secrets (AI key, Cosmos connection, Bot password, Blob connection) |

Secrets flow: Key Vault → Container App secret refs (resolved at startup) → `pydantic-settings` reads from env vars. No runtime Key Vault calls.

### 2.3 Compute — Containerized Backend

| Component | Technology | Details |
|---|---|---|
| Container App | Azure Container Apps | 1 CPU, 2Gi RAM; min 1 replica (no cold start); max 5 replicas |
| Runtime | Python 3.12-slim (Debian Bookworm) | Non-root user, health check on `/health` |
| Web Framework | FastAPI + Uvicorn (2 workers) | Three endpoints: `/api/messages`, `/health`, `/` |
| Scaling | HTTP-based autoscaler | Triggers at 20 concurrent requests per replica |
| Identity | System-assigned Managed Identity | Granted `Key Vault Secrets User` role via RBAC |
| Probes | Liveness + Readiness | Both hit `/health` endpoint on port 8000 |

### 2.4 AI Orchestration — LangGraph Agent

| Component | Technology | Purpose |
|---|---|---|
| Orchestrator | LangGraph (StateGraph) | Directed graph of 9 nodes with conditional edges |
| State | `AgentState` (TypedDict, 15 fields) | Carries context through the entire workflow |
| Checkpointer | MongoDB-backed `MongoDBSaver` (falls back to `MemorySaver`) | Persists graph state across container restarts and replicas |
| Interrupt pattern | `interrupt_before=["review", "approve"]` | Two mandatory human-in-the-loop checkpoints |
| Resume pattern | `graph.aupdate_state()` + `graph.ainvoke(None)` | Bot handler patches state and resumes from last interrupt |

The compiled graph:

```
classify_intent ──┬── generate_twi/edit_twi ── process_input ── generate ── [INTERRUPT: review]
                  │                                                            │      │       │
                  │                                                       approve  revise   END
                  │                                                            │      │
                  ├── question ── generate ── END                              │   generate
                  │                                                            │   (max 3x)
                  └── unknown ── clarify ── END                         [INTERRUPT: approve]
                                                                               │
                                                                            output ── audit ── END
```

### 2.5 AI Model Access

| Component | Technology | Details |
|---|---|---|
| AI Foundry | Azure Cognitive Services (`AIServices` kind) | `DataZoneStandard` SKU — contractual EU data residency |
| SDK | `azure-ai-inference` (async client) | `ChatCompletionsClient` with `AzureKeyCredential` |
| Models | GPT-4o (default) or Mistral Large 3 | Configurable via Bicep parameter + `AI_MODEL` env var |
| Temperature | 0.1 (intent) / 0.3 (generation) | Low temperature for deterministic classification; moderate for content |
| Token tracking | Every LLM call logs `input_tokens` + `output_tokens` | Feeds into audit trail |

The client is a singleton — one `AsyncChatCompletionsClient` instance per process lifetime.

### 2.6 Multi-Channel Bot Framework

| Component | Technology | Details |
|---|---|---|
| Azure Bot Service | S1 SKU (global resource) | Routes messages from Teams/Telegram to `/api/messages` |
| Bot SDK | `botbuilder-core` + `botbuilder-integration-aiohttp` | `BotFrameworkAdapter` + `AgentizeBotHandler` |
| Teams Channel | MsTeamsChannel | Adaptive Cards v1.4 for rich interactive UI |
| Telegram Channel | TelegramChannel (optional) | Markdown-formatted messages as fallback |
| Auth | Entra ID JWT validation | `JwtTokenValidation.authenticate_request()` on every incoming activity |
| Teams App Manifest | `teams-app/manifest.json` (sideload-ready) | Placeholder tokens `{{BOT_APP_ID}}`, `{{BACKEND_FQDN}}` |

### 2.7 Data Persistence — Cosmos DB

| Collection | Purpose | Key Indexes |
|---|---|---|
| `conversations` | Active chat sessions | `conversation_id` (unique), `tenant_id+user_id`, TTL 90 days |
| `agent_state` | LangGraph checkpoints (graph state persistence) | `thread_id+checkpoint_id` (unique), `thread_id+created_at` |
| `generated_documents` | Approved TWI docs with PDF references | `tenant_id+created_at`, `conversation_id` |
| `audit_log` | Immutable event trail (EU AI Act) | `tenant_id+created_at`, `event_type` |

Technology: Cosmos DB with MongoDB API (serverless mode), accessed via `motor` (async MongoDB driver). Three service classes — `ConversationStore`, `AuditStore`, `DocumentStore` — each with a singleton database connection.

### 2.8 PDF Generation & Storage

| Step | Technology | Details |
|---|---|---|
| Markdown to HTML | `markdown` library (tables + fenced_code extensions) | Converts LLM output to structured HTML |
| HTML templating | Jinja2 (`twi_template.html`) | A4 layout, header, AI warning box, content, approval box |
| HTML to PDF | WeasyPrint (system deps: Pango, HarfBuzz, GDK-Pixbuf) | Renders styled A4 PDF with page numbering |
| PDF storage | Azure Blob Storage (`pdf-output` container) | Path: `twi/{conversation_id}/{uuid}.pdf` |
| Download URL | SAS token (24-hour expiry) | Read-only, time-limited; no public blob access |

### 2.9 Observability

| Component | Technology | Purpose |
|---|---|---|
| Application Insights | Azure Monitor OpenTelemetry | Auto-configured at startup if connection string present |
| Log Analytics | Workspace linked to App Insights + Container App | 30-day retention; structured log ingestion |
| Structured logging | Python `logging` (INFO level default) | Every LLM call, PDF upload, audit event logged with context |
| Health endpoint | `GET /health` | Returns `{"status": "healthy", "environment": "poc"}` |

### 2.10 CI/CD & Deployment

| Component | Technology | Details |
|---|---|---|
| Infrastructure | Bicep (single `main.bicep`, ~550 lines) | One-command deploy: `az deployment group create` |
| Container build | GitHub Actions + Docker Buildx | Triggered on push to `main` (paths: `poc-backend/**`) |
| Registry | GitHub Container Registry (GHCR) | Tags: `${{ github.sha }}` + `latest` |
| App deploy | `az containerapp update` | Pulls new image from GHCR into Container App |
| Dev environment | Devcontainer (Python 3.12 + Azure CLI + Docker-in-Docker) | Port 8000 forwarded |

### 2.11 Technology Summary

| Layer | Technologies |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI + Uvicorn |
| AI orchestration | LangGraph (StateGraph + conditional edges + interrupts) |
| LLM access | Azure AI Foundry (`azure-ai-inference` SDK) |
| Bot framework | Microsoft Bot Framework SDK (`botbuilder-core`) |
| UI (Teams) | Adaptive Cards v1.4 |
| Database | Cosmos DB (MongoDB API) via `motor` |
| File storage | Azure Blob Storage (SAS URLs) |
| PDF pipeline | Markdown → Jinja2 → WeasyPrint |
| Config | pydantic-settings (env vars from Key Vault refs) |
| Auth | Entra ID (JWT token validation) |
| Infrastructure-as-Code | Bicep |
| Containerization | Docker (python:3.12-slim-bookworm) |
| CI/CD | GitHub Actions |
| Observability | Azure Monitor OpenTelemetry + App Insights |

---

*agentize.eu — AI & Organizational Solutions*
*Implementation Specification v1.0 — 2026-03-12*
