# agentize.eu PoC — Codebase Snapshot

**Generated:** 2026-03-06
**Repository:** TWI_POC
**Purpose:** Complete codebase analysis for the agentize.eu Enterprise AI Platform Proof-of-Concept

---

## 1. DIRECTORY TREE

```
TWI_POC/
├── .claude/                                          [other]
│   └── worktrees/
│       └── eager-jackson/                            [other]
├── .cursor/                                          [other]
│   ├── rules/
│   │   ├── azure-service-clients.mdc                 [config]
│   │   ├── bicep-infra-conventions.mdc               [config]
│   │   ├── bot-adaptive-cards.mdc                    [config]
│   │   ├── eu-ai-act-compliance.mdc                  [config]
│   │   ├── langgraph-agent-patterns.mdc              [config]
│   │   └── python-backend-patterns.mdc               [config]
│   └── skills/
│       ├── agentize-poc-architecture/
│       │   └── SKILL.md                              [doc]
│       ├── agentize-poc-azure-infra/
│       │   └── SKILL.md                              [doc]
│       ├── agentize-poc-bot-cards/
│       │   └── SKILL.md                              [doc]
│       └── agentize-poc-langgraph/
│           └── SKILL.md                              [doc]
├── .devcontainer/
│   └── devcontainer.json                             [config]
├── .flake8                                           [config]
├── .github/
│   └── workflows/
│       └── deploy.yml                                [config]
├── agent_vendor_guide_v2.docx                        [doc]
├── go_live_guide.md                                  [doc]
├── poc_technical_spec.md                             [doc]
├── poc_technical_spec.md.pdf                         [doc]
├── poc_vibe_coding_context.md                        [doc]
├── poc_vibe_coding_context.md.pdf                    [doc]
├── teams-app/
│   ├── manifest.json                                 [config]
│   ├── color.png                                     [other]
│   └── outline.png                                   [other]
└── poc-backend/
    ├── .devcontainer/
    │   └── devcontainer.json                         [config]
    ├── .env                                          [config]
    ├── .env.example                                  [config]
    ├── Dockerfile                                    [config]
    ├── pyproject.toml                                [config]
    ├── requirements.txt                              [config]
    ├── setup.cfg                                     [config]
    ├── app/
    │   ├── __init__.py                               [code]
    │   ├── main.py                                   [code]
    │   ├── config.py                                 [code]
    │   ├── agent/
    │   │   ├── __init__.py                           [code]
    │   │   ├── graph.py                              [code]
    │   │   ├── state.py                              [code]
    │   │   ├── nodes/
    │   │   │   ├── __init__.py                       [code]
    │   │   │   ├── approve.py                        [code]
    │   │   │   ├── audit.py                          [code]
    │   │   │   ├── generate.py                       [code]
    │   │   │   ├── intent.py                         [code]
    │   │   │   ├── output.py                         [code]
    │   │   │   ├── process_input.py                  [code]
    │   │   │   ├── review.py                         [code]
    │   │   │   └── revise.py                         [code]
    │   │   └── tools/
    │   │       ├── __init__.py                       [code]
    │   │       └── pdf_generator.py                  [code]
    │   ├── bot/
    │   │   ├── __init__.py                           [code]
    │   │   ├── adaptive_cards.py                     [code]
    │   │   └── bot_handler.py                        [code]
    │   ├── models/
    │   │   └── __init__.py                           [code]
    │   ├── services/
    │   │   ├── __init__.py                           [code]
    │   │   ├── ai_foundry.py                         [code]
    │   │   ├── blob_storage.py                       [code]
    │   │   └── cosmos_db.py                          [code]
    │   └── templates/
    │       └── twi_template.html                     [code]
    ├── infra/
    │   ├── main.bicep                                [code]
    │   ├── deploy.ps1                                [code]
    │   ├── deploy.sh                                 [code]
    │   ├── validate.ps1                              [code]
    │   ├── parameters.example.json                   [config]
    │   └── error.txt                                 [other]
    └── tests/
        ├── __init__.py                               [code]
        ├── conftest.py                               [code]
        ├── test_cosmos_db.py                         [code]
        ├── test_generation.py                        [code]
        ├── test_graph.py                             [code]
        ├── test_output.py                            [code]
        └── test_pdf.py                               [code]
```

---

## 2. TECH STACK DETECTED

### LLM / Agent Layer

| Technology | Version | Source |
|---|---|---|
| LangGraph | 0.3.x | requirements.txt, pyproject.toml |
| LangChain Core | 0.3.x | requirements.txt |
| LangSmith | 0.2.x | requirements.txt |
| Azure AI Foundry (azure-ai-inference) | >=1.0.0b1,<2.0.0 | requirements.txt |
| Model: Mistral Large (default) or GPT-4o | DataZoneStandard SKU | main.bicep, config.py |

### Backend

| Technology | Version | Source |
|---|---|---|
| Python | >=3.11 (3.12 in Dockerfile) | pyproject.toml, Dockerfile |
| FastAPI | 0.115.x | requirements.txt |
| Uvicorn (ASGI) | 0.32.x | requirements.txt |
| Pydantic | 2.10.x | requirements.txt |
| Pydantic Settings | 2.7.x | requirements.txt |
| python-dotenv | 1.0.x | requirements.txt |
| aiohttp | 3.10.x | requirements.txt |
| Bot Framework (botbuilder-core) | 4.16.x | requirements.txt |
| Bot Framework (botbuilder-integration-aiohttp) | 4.16.x | requirements.txt |
| Jinja2 | 3.1.x | requirements.txt |
| WeasyPrint | 63.x | requirements.txt |
| Markdown | 3.7.x | requirements.txt |

### Frontend

| Technology | Version | Source |
|---|---|---|
| Microsoft Teams (Adaptive Cards v1.4) | Schema v1.17 | manifest.json, adaptive_cards.py |
| Telegram (optional channel) | — | main.bicep, config.py |

### Infrastructure

| Technology | Version | Source |
|---|---|---|
| Azure Container Apps | 2023-05-01 API | main.bicep |
| Azure Bicep | — | main.bicep |
| Docker | python:3.12-slim base | Dockerfile |
| GitHub Actions CI/CD | — | deploy.yml |
| Azure VNet + NSG | 2023-09-01 API | main.bicep |
| Azure Log Analytics | 2023-09-01 API | main.bicep |
| Azure Application Insights | 2020-02-02 API | main.bicep |
| Azure Bot Service | 2022-09-15 API | main.bicep |

### Auth

| Technology | Version | Source |
|---|---|---|
| Microsoft Entra ID (App Registration) | — | main.bicep, deploy.ps1 |
| Azure Key Vault | 2023-07-01 API | main.bicep |
| azure-identity SDK | 1.19.x | requirements.txt |
| azure-keyvault-secrets SDK | 4.9.x | requirements.txt |

### Storage

| Technology | Version | Source |
|---|---|---|
| Azure Cosmos DB (MongoDB API 7.0) | 2023-11-15 API, Serverless | main.bicep |
| Motor (async MongoDB driver) | 3.6.x | requirements.txt |
| PyMongo | 4.9.x | requirements.txt |
| Azure Blob Storage | 2023-01-01 API | main.bicep |
| azure-storage-blob SDK | 12.23.x | requirements.txt |

### Observability

| Technology | Version | Source |
|---|---|---|
| OpenTelemetry API | 1.29.x | requirements.txt |
| OpenTelemetry SDK | 1.29.x | requirements.txt |
| Azure Monitor OpenTelemetry | 1.6.x | requirements.txt |

### Dev / Test

| Technology | Version | Source |
|---|---|---|
| pytest | 8.3.x | requirements.txt |
| pytest-asyncio | 0.25.x | requirements.txt |
| httpx | 0.28.x | requirements.txt |
| Hatchling (build) | — | pyproject.toml |
| Flake8 | — | .flake8, setup.cfg |

---

## 3. ARCHITECTURE SUMMARY

This system is an Enterprise AI Platform Proof-of-Concept built for **agentize.eu** that generates TWI (Training Within Industry) work instructions via an AI agent orchestrated with **LangGraph**, deployed in the customer's Azure subscription with EU data residency guarantees (Sweden Central, DataZoneStandard SKU).

The user interacts through **Microsoft Teams** (primary) or **Telegram** (optional) by sending natural-language requests to an Azure Bot Service bot. The bot's messaging endpoint is a **FastAPI** application running inside an **Azure Container App** with VNet isolation. When a message arrives at `/api/messages`, it is validated via Entra ID JWT tokens and routed through the **Bot Framework adapter** to the `AgentizeBotHandler`.

The handler invokes a **LangGraph** state-machine graph with 8 nodes: `intent` (LLM-based intent classification) -> `process_input` (structured extraction) -> `generate` (LLM-powered TWI draft generation with EU AI Act labeling) -> `review` (human-in-the-loop checkpoint #1 via Adaptive Card) -> optional `revise` loop (max 3 rounds) -> `approve` (human-in-the-loop checkpoint #2, mandatory final approval) -> `output` (PDF generation via WeasyPrint and upload to Azure Blob Storage) -> `audit` (immutable audit trail in Cosmos DB for EU AI Act compliance).

The LLM calls are made to **Azure AI Foundry** (Mistral Large or GPT-4o) through the `azure-ai-inference` SDK, with the service abstracted in `ai_foundry.py`. State persistence uses an **in-memory `MemorySaver`** checkpointer (PoC limitation — Cosmos DB-backed checkpointer is defined in Bicep but not implemented in code). **Cosmos DB (MongoDB API)** stores conversations, generated documents, and audit logs via the async `motor` driver.

PDF output uses a **Jinja2 HTML template** rendered by **WeasyPrint** into A4 PDFs, uploaded to **Azure Blob Storage** with 24-hour SAS URLs for download. The Adaptive Cards flow in Teams presents four card types: welcome, review (with approve/edit/reject actions), final approval, and result (with PDF download link).

Infrastructure is fully defined in a single **Bicep template** (`main.bicep`) covering VNet, NSG, Key Vault, AI Foundry, Cosmos DB (4 collections), Storage Account, Container Apps Environment, Bot Service (with Teams and optional Telegram channels), Application Insights, and Log Analytics. Deployment is automated via **`deploy.ps1`** (PowerShell) and **`deploy.sh`** (bash), which handle Entra ID App Registration creation, Bicep deployment, Key Vault secret population, and local `.env` generation. CI/CD is handled by **GitHub Actions** which builds the Docker image, pushes to GHCR, and updates the Container App.

The main entry points are: `app/main.py` (FastAPI app with `/api/messages`, `/health`, `/` routes), `infra/main.bicep` (infrastructure), `infra/deploy.ps1` / `deploy.sh` (deployment automation), and `.github/workflows/deploy.yml` (CI/CD pipeline).

---

## 4. FILE-BY-FILE SUMMARY

### Backend Application (`poc-backend/app/`)

#### `app/main.py`
- **Purpose:** FastAPI application entry point; defines the Bot Framework adapter, routes, and error handling.
- **Key functions/classes:** `messages()` (POST `/api/messages` — Bot Framework messaging endpoint with Entra ID JWT validation), `health()` (GET `/health`), `root()` (GET `/`), `_on_error()` (adapter error handler).
- **External dependencies:** `fastapi`, `botbuilder.core`, `botbuilder.schema`, `botframework.connector.auth`, `azure.monitor.opentelemetry`.

#### `app/config.py`
- **Purpose:** Centralized configuration using Pydantic Settings; loads env vars from `.env`.
- **Key classes:** `Settings(BaseSettings)` — defines all config fields (AI Foundry, Cosmos DB, Blob Storage, Bot Framework, Telegram, App Insights, app-level settings). Singleton `settings` instance exported at module level.
- **External dependencies:** `pydantic_settings`.

#### `app/agent/graph.py`
- **Purpose:** Defines and compiles the LangGraph agent state-machine graph; provides `run_agent()` to invoke or resume the graph.
- **Key functions:** `create_agent_graph()` (builds the StateGraph with 8 nodes, conditional edges, MemorySaver checkpointer, interrupt_before at review and approve), `get_graph()` (singleton accessor), `run_agent()` (invoke or resume for a conversation), `should_generate()` / `after_review()` / `after_revision()` (conditional edge routing functions), `_build_resume_state()` (builds state patch for HITL resume), `clarify_node()` (placeholder for unknown intent).
- **External dependencies:** `langgraph.graph`, `langgraph.checkpoint.memory`.

#### `app/agent/state.py`
- **Purpose:** Defines the `AgentState` TypedDict that flows through all LangGraph nodes.
- **Key classes:** `AgentState(TypedDict)` — 15 fields covering input context, processing state, revision loop, output, and audit/telemetry.
- **External dependencies:** `typing`, `typing_extensions`.

#### `app/agent/nodes/intent.py`
- **Purpose:** LLM-based intent classification node; classifies user message into one of 4 intents.
- **Key functions:** `intent_node(state)` — calls LLM with temperature=0.1 and max_tokens=20, validates response against `_VALID_INTENTS` set (`generate_twi`, `edit_twi`, `question`, `unknown`).
- **External dependencies:** `app.services.ai_foundry.call_llm`.

#### `app/agent/nodes/process_input.py`
- **Purpose:** Lightweight input structuring node; extracts original message, intent, and channel into `processed_input` dict.
- **Key functions:** `process_input_node(state)` — minimal PoC implementation; notes future extension for machine name / process type extraction.
- **External dependencies:** None (only `AgentState`).

#### `app/agent/nodes/generate.py`
- **Purpose:** Core TWI document generation node; calls LLM with detailed system prompt and handles revision context.
- **Key functions:** `generate_node(state)` — constructs prompt with TWI format instructions (Title, Goal, Materials, Safety, Steps with key points/reasoning, Quality Check), injects previous draft + feedback for revisions, prepends EU AI Act label. `_now_iso()` — UTC timestamp helper.
- **External dependencies:** `app.services.ai_foundry.call_llm`, `app.config.settings`.
- **Constants:** `_TWI_SYSTEM_PROMPT` (Hungarian-language system prompt), `_TWI_GENERATE_PROMPT` (template with message + revision_context), `_EU_AI_ACT_LABEL`.

#### `app/agent/nodes/review.py`
- **Purpose:** Human-in-the-loop checkpoint #1; the graph interrupts before this node. Sets status to `review_needed`.
- **Key functions:** `review_node(state)` — minimal; actual logic is in bot_handler after resume.
- **External dependencies:** None.

#### `app/agent/nodes/revise.py`
- **Purpose:** Increments the revision counter and sets status for the revision loop.
- **Key functions:** `revise_node(state)` — increments `revision_count`, sets `status` to `revision_requested`.
- **External dependencies:** None.

#### `app/agent/nodes/approve.py`
- **Purpose:** Human-in-the-loop checkpoint #2 (mandatory final approval); the graph interrupts before this node.
- **Key functions:** `approve_node(state)` — sets `status` to `approved`.
- **External dependencies:** None.

#### `app/agent/nodes/output.py`
- **Purpose:** PDF generation, Blob Storage upload, and document persistence to Cosmos DB.
- **Key functions:** `output_node(state)` — calls `generate_twi_pdf()`, uploads via `upload_pdf()`, extracts title, saves document record to `DocumentStore`, returns state with `pdf_url`, `pdf_blob_name`, `title`, and `status=completed`.
- **External dependencies:** `app.agent.tools.pdf_generator`, `app.services.blob_storage`, `app.services.cosmos_db.DocumentStore`.

#### `app/agent/nodes/audit.py`
- **Purpose:** Writes an immutable audit log entry to Cosmos DB for EU AI Act compliance.
- **Key functions:** `audit_node(state)` — creates audit entry with conversation_id, user_id, tenant_id, channel, event_type, LLM details, revision count, PDF reference, status, and timestamps.
- **External dependencies:** `app.services.cosmos_db.AuditStore`.

#### `app/agent/tools/pdf_generator.py`
- **Purpose:** Converts TWI markdown draft to formatted A4 PDF via Jinja2 + WeasyPrint pipeline.
- **Key functions:** `generate_twi_pdf(content, metadata, user_id, approval_timestamp)` — converts markdown to HTML, renders Jinja2 template, produces PDF bytes. `_extract_title(content)` — extracts first non-warning line as document title (max 100 chars).
- **External dependencies:** `markdown`, `jinja2`, `weasyprint`.

#### `app/bot/bot_handler.py`
- **Purpose:** Core Bot Framework activity handler; routes messages and Adaptive Card actions to the LangGraph agent.
- **Key classes:** `AgentizeBotHandler(ActivityHandler)` — holds singleton graph and ConversationStore.
- **Key methods:** `on_message_activity()` (routes text messages vs card actions), `on_members_added_activity()` (sends welcome card), `_handle_text_message()` (invokes LangGraph, sends review/clarify/error cards), `_handle_card_action()` (handles approve_draft, request_edit, final_approve, reject actions — resumes LangGraph for revisions and final approval), `_send_card()` (helper to send Adaptive Card).
- **External dependencies:** `botbuilder.core`, `botbuilder.schema`, `app.agent.graph`, `app.bot.adaptive_cards`, `app.services.cosmos_db`.

#### `app/bot/adaptive_cards.py`
- **Purpose:** JSON template builders for all four Adaptive Card types used in the bot interaction flow.
- **Key functions:** `create_review_card(draft, metadata)` — HITL #1 card with approve/edit/reject actions, draft truncated to 2000 chars. `create_approval_card(draft, metadata)` — HITL #2 mandatory approval card. `create_result_card(pdf_url, document_title, metadata)` — final result card with PDF download link. `create_welcome_card()` — onboarding card for new members.
- **External dependencies:** None (pure dict construction).
- **Constants:** `_SCHEMA` (Adaptive Card schema URL), `_VERSION` ("1.4").

#### `app/services/ai_foundry.py`
- **Purpose:** Azure AI Foundry LLM client wrapper; singleton async client for chat completions.
- **Key functions:** `call_llm(prompt, system_prompt, temperature, max_tokens)` — returns `(response_text, total_tokens)`. `_get_client()` — lazy singleton `AsyncChatCompletionsClient`.
- **External dependencies:** `azure.ai.inference.aio`, `azure.core.credentials`.

#### `app/services/blob_storage.py`
- **Purpose:** Azure Blob Storage client for PDF upload with SAS URL generation.
- **Key functions:** `upload_pdf(pdf_bytes, blob_name)` — uploads PDF, generates 24-hour read-only SAS URL. `_get_client()` — lazy singleton `BlobServiceClient`.
- **External dependencies:** `azure.storage.blob`.

#### `app/services/cosmos_db.py`
- **Purpose:** Cosmos DB (MongoDB API) data access layer with three store classes.
- **Key classes:** `ConversationStore` — `get_or_create()` upserts conversation tracking with message count and last_activity. `AuditStore` — `log()` inserts immutable audit entries. `DocumentStore` — `save()` persists generated document records.
- **Key functions:** `_get_db()` — lazy singleton Motor client/database.
- **External dependencies:** `motor.motor_asyncio`.

#### `app/templates/twi_template.html`
- **Purpose:** Jinja2 HTML template for TWI PDF rendering; A4 format with branded styling.
- **Key features:** Page counter footer with "agentize.eu" branding, EU AI Act warning banner, step/key-point/reason styled blocks, approval box (green border), table support, `@page` CSS for A4 margins.
- **Template variables:** `title`, `generated_at`, `model`, `revision`, `content_html`, `approved`, `approved_by`, `approved_at`.

### Infrastructure (`poc-backend/infra/`)

#### `infra/main.bicep`
- **Purpose:** Complete Azure infrastructure-as-code for the PoC; single-file Bicep template.
- **Key resources:** Log Analytics Workspace, NSG (HTTPS + Bot Service inbound, deny-all), VNet (2 subnets: container-apps /23, private-endpoints /24), Key Vault (RBAC auth, soft delete), Application Insights, Container App Environment (VNet-integrated, external ingress), Azure AI Foundry (AIServices kind, DataZoneStandard SKU, Mistral Large or GPT-4o), Cosmos DB (MongoDB API, serverless, 4 collections: conversations, agent_state, generated_documents, audit_log with indexes and TTL), Storage Account (StorageV2, no public blob access, TLS 1.2), Container App (system-assigned identity, Key Vault secret references, liveness/readiness probes, HTTP auto-scaling), RBAC role assignment (Container App -> Key Vault Secrets User), Bot Service (single-tenant, Teams channel, conditional Telegram channel).
- **Parameters:** location, projectPrefix, aiModel, minReplicas, cosmosThroughputMode, botAppId, botAppPassword, telegramBotToken, containerImage.
- **Outputs:** backendFqdn, botEndpoint, aiFoundryEndpoint, aiFoundryInferenceEndpoint, cosmosAccountName, storageAccountName, keyVaultUri, keyVaultName, appInsightsConnectionString, containerAppPrincipalId, backendHostname.

#### `infra/deploy.ps1`
- **Purpose:** PowerShell deployment automation script covering the full Day 1-2 checklist.
- **Key steps:** (0) Prerequisites check, (1) Entra ID App Registration creation with client secret and Graph User.Read permission, (2) Resource Group creation, (3) Bicep deployment, (4) Service key retrieval (AI Foundry, Cosmos, Blob), (5) Deployer Key Vault Secrets Officer RBAC grant, (6) Key Vault secret population, (7) Container App restart for secret resolution, (8) `.env` file generation.
- **Parameters:** ResourceGroup, Location, ProjectPrefix, BotAppId, BotAppPassword, TelegramBotToken, SkipAppReg, WhatIf.

#### `infra/deploy.sh`
- **Purpose:** Bash equivalent of deploy.ps1 for CI/CD and Linux environments; mirrors all 8 steps.
- **External dependencies:** `az` CLI, `python3` (for JSON parsing).

#### `infra/validate.ps1`
- **Purpose:** Post-deployment validation script; checks 10 categories of infrastructure health.
- **Key checks:** Azure login, Resource Group, 9 core resources (Container App Environment, Container App, AI Foundry, Cosmos DB, Storage, Key Vault, Bot Service, App Insights, Log Analytics), AI Foundry model deployment (DataZoneStandard SKU verification), Key Vault secrets (4 required), Cosmos DB collections (4 required), Blob Storage container, Container App health (/health HTTP probe), Bot Service channels (Teams + Telegram), AI Foundry connectivity test.

#### `infra/parameters.example.json`
- **Purpose:** Example Bicep parameters file with placeholder values for deployment.

#### `infra/error.txt`
- **Purpose:** Captured error output from a deploy.ps1 run — encoding issue with Unicode box-drawing characters in the banner.

### Teams App (`teams-app/`)

#### `teams-app/manifest.json`
- **Purpose:** Microsoft Teams app manifest (schema v1.17) for bot sideloading.
- **Key configuration:** Bot with personal/team/groupChat scopes, two commands ("Uj TWI", "Segitseg"), placeholder tokens `{{BOT_APP_ID}}` and `{{BACKEND_FQDN}}` for deployment-time substitution, permissions for identity and messageTeamMembers.

### CI/CD (`.github/workflows/`)

#### `.github/workflows/deploy.yml`
- **Purpose:** GitHub Actions workflow for automated build and deploy on push to main.
- **Triggers:** Push to `main` branch, only when `poc-backend/**` files change.
- **Steps:** Checkout, Azure login, Docker Buildx setup, GHCR login, Docker build+push (sha tag + latest), Container App update via `az containerapp update`.

### Tests (`poc-backend/tests/`)

#### `tests/conftest.py`
- **Purpose:** Shared pytest fixtures for the test suite.
- **Key fixtures:** `mock_llm_response` (default "generate_twi" string), `sample_agent_state` (minimal valid AgentState dict), `sample_draft` (realistic TWI draft with EU AI Act label).

#### `tests/test_graph.py`
- **Purpose:** Tests for LangGraph agent graph routing, revision loop, state transitions, resume state builder, graph compilation, intent node, and revision node.
- **Key test classes:** `TestShouldGenerate` (5 tests — routing for each intent), `TestAfterReview` (4 tests — approved/revision/rejected/unknown), `TestAfterRevision` (4 tests — below/at/above max, zero), `TestBuildResumeState` (4 tests — revision/output/unknown/missing feedback), `TestCreateAgentGraph` (1 test — compilation), `TestIntentNode` (3 tests + parametrized — mocked LLM), `TestReviseNode` (2 tests — increment/first revision).
- **Total:** 23 tests.

#### `tests/test_generation.py`
- **Purpose:** Tests for TWI generation node (EU AI Act label, revision context, output structure), intent node temperature, process_input node, and Adaptive Cards.
- **Key test classes:** `TestGenerateNode` (8 tests — EU AI Act label, status, metadata keys, LLM model, revision context injection, revision count, LLM response content, temperature=0.3), `TestIntentNodeTemperature` (1 test — temperature=0.1), `TestProcessInputNode` (2 tests), `TestAdaptiveCards` (6 tests — review/approval/result/welcome cards).
- **Total:** 17 tests.

#### `tests/test_output.py`
- **Purpose:** Tests for the output node — PDF generation, Blob upload, and DocumentStore persistence.
- **Key tests:** `test_output_node_saves_to_document_store` — verifies PDF generation called, Blob upload called, DocumentStore instantiated and save called with correct document structure, returned state has completed status and PDF URL.
- **Total:** 1 test.

#### `tests/test_pdf.py`
- **Purpose:** Tests for PDF generation pipeline — title extraction and WeasyPrint rendering.
- **Key test classes:** `TestExtractTitle` (6 tests — first non-warning line, skip AI warning, default fallback, truncation to 100 chars, markdown heading strip, empty content), `TestGenerateTwiPdf` (6 tests — returns bytes, non-empty, PDF header, model+timestamp in HTML, approval box with approver ID, EU AI Act footer).
- **Total:** 12 tests.

#### `tests/test_cosmos_db.py`
- **Purpose:** Tests for Cosmos DB DocumentStore save operation.
- **Key tests:** `test_document_store_save` — mocks `_get_db`, verifies insert_one called with correct document including created_at timestamp.
- **Total:** 1 test.

### Configuration Files

#### `poc-backend/pyproject.toml`
- **Purpose:** Python project metadata and tool configuration (hatchling build, pytest, mypy strict mode).

#### `poc-backend/requirements.txt`
- **Purpose:** Pinned Python dependencies for pip install.

#### `poc-backend/setup.cfg`
- **Purpose:** Flake8 configuration (max-line-length=120, ignore E203/W503).

#### `poc-backend/.env.example`
- **Purpose:** Template `.env` file with placeholder values for all required environment variables.

#### `poc-backend/.env`
- **Purpose:** Actual environment configuration (contains placeholder secrets — not production values).

#### `.flake8`
- **Purpose:** Root-level flake8 config (max-line-length=120, ignore E203/W503, relaxed E501 for tests).

#### `.devcontainer/devcontainer.json`
- **Purpose:** Root dev container config (Python 3.11, Azure CLI, Docker-in-Docker, VS Code extensions for Python/Docker/Bicep/Teams).

#### `poc-backend/.devcontainer/devcontainer.json`
- **Purpose:** Backend-specific dev container config (Python 3.12, Azure CLI, Docker-in-Docker, VS Code extensions).

### Documentation

#### `go_live_guide.md`
- **Purpose:** Step-by-step deployment and go-live guide covering Azure infra deployment, GitHub Actions CI/CD setup, Teams manifest configuration, sideloading, and end-to-end validation demo flow.

#### `poc_technical_spec.md`
- **Purpose:** Complete technical specification (Hungarian) — project overview, scope, architecture, 10-day sprint plan, API contracts, LangGraph graph definition, Adaptive Card schemas, Cosmos DB schema, Bicep parameters, cost model, EU AI Act compliance, testing strategy.

#### `poc_vibe_coding_context.md`
- **Purpose:** Vibe-coding session context document — immutable decisions, excluded features, architecture quick reference, tech stack table, LangGraph graph diagram, Adaptive Card flow, Cosmos DB collections, cost model, Entra ID checklist, known risks.

---

## 5. OPEN ISSUES / CODE SMELLS

### Critical Issues

1. **MemorySaver instead of Cosmos DB checkpointer** — `poc-backend/app/agent/graph.py:109` uses `MemorySaver()` which is in-memory only. All LangGraph state is lost on container restart or scale-out. The Bicep template (`infra/main.bicep:282-297`) provisions an `agent_state` collection with proper indexes, but no code uses it. This is the single biggest gap for production readiness.

2. **LangGraph resume bug in `bot_handler.py`** — `poc-backend/app/bot/bot_handler.py:137-161` and lines 163-191: The `run_agent()` call with `resume_from` passes a state update dict to `graph.ainvoke()`, but LangGraph's `interrupt_before` mechanism requires using `graph.ainvoke(None, config)` to resume from the last checkpoint, or using `graph.update_state()` before invoking. The current `_build_resume_state()` approach (`graph.py:170-182`) constructs a partial state dict and passes it as input, which will likely create a *new* graph run instead of resuming the interrupted one. This means the revision loop and final approval flow may not work correctly.

3. **No `key_vault.py` service** — The `azure-keyvault-secrets` SDK (v4.9.x) is listed in requirements.txt, and Key Vault is fully provisioned in Bicep with RBAC and secret references, but there is no `app/services/key_vault.py` module. The Container App resolves secrets via Key Vault references in the Bicep template (environment variables), so runtime Key Vault access is not strictly needed for the PoC. However, the SDK dependency is unused and a dedicated service for runtime secret rotation is missing.

### Missing `.gitignore`

4. **No `.gitignore` file** — The repository has no `.gitignore`. The `.env` file containing secrets is tracked (even if placeholder values). The `__pycache__` directories, `.venv`, and other artifacts are not excluded. The `go_live_guide.md` and `deploy.ps1` both warn about `.gitignore` covering `.env`, but the file doesn't exist.

### Hardcoded Values

5. **Hardcoded Hungarian strings** — All user-facing bot messages are hardcoded in Hungarian throughout `bot_handler.py` (lines 77, 89, 103-105, 113, 139, 165, 179, 195) and `adaptive_cards.py`. No i18n/l10n framework is used. Acceptable for PoC but blocks multi-language support.

6. **Hardcoded `"poc-tenant"` default** — `poc-backend/app/agent/graph.py:130` and `poc-backend/app/services/cosmos_db.py:31` use `"poc-tenant"` as a default tenant_id. This is fine for single-tenant PoC but would be a problem if multi-tenancy is added.

7. **Hardcoded `__CURRENT_TIMESTAMP__` placeholder** — `poc-backend/app/bot/adaptive_cards.py:123` includes `"timestamp": "__CURRENT_TIMESTAMP__"` in the approval card's `data` payload. This placeholder string is never replaced — the actual timestamp comes from `bot_handler.py:166` when the card action is processed, not from the card data. The placeholder is dead data in the card submission payload.

8. **Hardcoded draft truncation at 2000 chars** — `poc-backend/app/bot/adaptive_cards.py:36,110` truncates draft to 2000 characters for Adaptive Card payload limits. The actual Teams limit is ~28KB for the entire card payload, so 2000 chars is conservative but the truncation point is magic-numbered without a named constant.

### Error Handling

9. **Broad exception catches** — `poc-backend/app/bot/bot_handler.py:87,152,177` catch bare `Exception` (noted with `# noqa: BLE001`). Error messages are shown directly to the user (`f"Hiba: {exc}"`), which could leak internal implementation details.

10. **No error handling for Cosmos DB connection failure** — `poc-backend/app/services/cosmos_db.py:17` creates `AsyncIOMotorClient` at first access. If `settings.cosmos_connection` is empty or invalid, the error surfaces only when the first database operation is attempted, with no graceful fallback or startup check.

11. **No error handling in `blob_storage.py` SAS generation** — `poc-backend/app/services/blob_storage.py:45` accesses `client.credential.account_key` which will fail with `AttributeError` if the BlobServiceClient was created with a SAS token or managed identity instead of a connection string with account key.

### Structural Issues

12. **Empty `app/models/__init__.py`** — The `models` package exists but contains no model definitions. Pydantic models for API request/response schemas are absent. The system relies entirely on TypedDict and raw dicts.

13. **`output.py` imports private function** — `poc-backend/app/agent/nodes/output.py:6` imports `_extract_title` from `pdf_generator.py` — a private (underscore-prefixed) function. Should be made public or a wrapper provided.

14. **`process_input_node` is nearly a no-op** — `poc-backend/app/agent/nodes/process_input.py:4-15` simply copies existing state fields into a new dict. The comment mentions future extensions but the node adds no value currently.

15. **Two conflicting `.devcontainer/devcontainer.json` files** — Root uses Python 3.11, `poc-backend/` uses Python 3.12. The Dockerfile uses 3.12. The root devcontainer installs from `poc-backend/requirements.txt` and `poc-backend/[dev]`, while the inner one installs from local `requirements.txt`. This creates ambiguity about which Python version is canonical.

16. **`error.txt` committed to repo** — `poc-backend/infra/error.txt` contains a captured PowerShell error from a failed deploy.ps1 run (Unicode encoding issue with box-drawing characters). This is debug artifact and should not be in the repository.

17. **Duplicate dependency declarations** — Both `requirements.txt` and `pyproject.toml` declare the same dependencies. These could drift out of sync. The `pyproject.toml` is the canonical source but `requirements.txt` is used in Dockerfile.

18. **Bot Framework import inconsistency** — `poc-backend/app/main.py:6` imports `from botframework.connector.auth import JwtTokenValidation, SimpleCredentialProvider` which uses the `botframework` package namespace, while the rest of the code uses `botbuilder`. This may cause import errors depending on the installed package version.

### Test Coverage Gaps

19. **No integration tests** — All tests mock external dependencies. There are no integration tests that verify the actual LangGraph graph execution end-to-end, nor any tests for the Bot Framework handler.

20. **No tests for `bot_handler.py`** — The most complex module (213 lines, multiple card action handlers, LangGraph resume logic) has zero test coverage.

21. **No tests for `ai_foundry.py` or `blob_storage.py`** — Service layer modules lack unit tests even with mocking.

22. **`conftest.py` fixtures unused** — `mock_llm_response` and `sample_draft` fixtures defined in `conftest.py` are never used by any test file. Tests define their own inline fixtures.

---

## 6. KNOWN GAPS VS SPEC

### Dockerfile
- **Status: IMPLEMENTED**
- `poc-backend/Dockerfile` is present and functional. Uses `python:3.12-slim` base, installs WeasyPrint system dependencies (pango, harfbuzz, gdk-pixbuf), copies requirements and app code, exposes port 8000, runs uvicorn with 2 workers.
- **Minor gap:** No `HEALTHCHECK` instruction in the Dockerfile (health checks are defined in the Bicep Container App probes instead).
- **Minor gap:** No non-root user — container runs as root.

### `key_vault.py` Service
- **Status: MISSING**
- There is no `app/services/key_vault.py` file. The `azure-keyvault-secrets==4.9.*` SDK is listed in requirements.txt but never imported anywhere in the application code. Secrets are resolved at container start via Key Vault references in the Bicep template's Container App environment variables, so runtime Key Vault access is not used. A dedicated `key_vault.py` service for programmatic secret access (e.g., runtime rotation, on-demand secret reads) does not exist.

### Cosmos DB-backed LangGraph Checkpointer (not MemorySaver)
- **Status: MISSING (infrastructure provisioned, code not implemented)**
- The Bicep template (`infra/main.bicep:282-297`) provisions an `agent_state` collection with indexes on `thread_id`, `checkpoint_id`, and `created_at` — designed for LangGraph checkpointing.
- The application code (`app/agent/graph.py:109`) uses `MemorySaver()` — an in-memory-only checkpointer. This means:
  - Graph state is lost on every container restart or deployment.
  - Scale-out to multiple replicas will not share state.
  - Long-running conversations (e.g., user leaves and returns hours later) will fail.
- **What's needed:** A custom `MongoDBSaver` class implementing the LangGraph `BaseCheckpointSaver` interface, using the Motor async client to read/write to the `agent_state` collection.

### LangGraph Resume Bug in `bot_handler.py`
- **Status: BUG PRESENT**
- `bot_handler.py` lines 143-151 (revision resume) and 168-176 (final approval resume) call `run_agent()` with `resume_from` parameter.
- `graph.py:137-139` handles resume by building a state update dict via `_build_resume_state()` and passing it to `graph.ainvoke(state_update, config)`.
- **The bug:** LangGraph's `interrupt_before` mechanism pauses the graph at a checkpoint. To resume, you must either:
  1. Call `graph.ainvoke(None, config)` to continue from the last checkpoint, or
  2. Call `graph.update_state(config, state_update)` to modify the state, then `graph.ainvoke(None, config)`.
- The current code passes a partial state dict as input to `ainvoke()`, which starts a new graph execution with that partial state rather than resuming the interrupted checkpoint. This means:
  - The revision loop likely creates a new graph run instead of continuing the existing one.
  - The final approval likely does the same — potentially losing the draft content.
  - The `interrupt_before=["review", "approve"]` configuration is effectively unused.
- **Impact:** The core human-in-the-loop workflow (the primary PoC feature) is likely broken for multi-step interactions.

### Telegram Channel Handling
- **Status: PARTIAL**
- **Infrastructure (IMPLEMENTED):** `infra/main.bicep:503-514` conditionally creates a `TelegramChannel` resource on Bot Service when `telegramBotToken` is provided. The deploy scripts pass the token through.
- **Configuration (IMPLEMENTED):** `app/config.py:24-25` has `telegram_bot_token: str = ""` setting, and `.env.example` includes the `TELEGRAM_BOT_TOKEN` variable.
- **Code handling (MISSING):**
  - `bot_handler.py` does not differentiate behavior based on `channel_id`. The same Adaptive Cards are sent regardless of channel.
  - Telegram does not support Adaptive Cards — the review/approval/result cards will either fail silently or render as unsupported content on Telegram.
  - No Telegram-specific message formatting (e.g., inline keyboards, markdown messages) is implemented.
  - The `channel` field in `AgentState` is tracked but never used for conditional logic in any node.
  - **Effectively:** Telegram is wired at the infrastructure level but the bot will not function correctly on Telegram because the card-based interaction flow has no Telegram fallback.

### Teams App Manifest Completeness
- **Status: PARTIAL**
- **Present and correct:**
  - Schema version 1.17 (current).
  - Bot configuration with personal/team/groupChat scopes.
  - Two command suggestions ("Uj TWI", "Segitseg").
  - Developer info, icons, accent color.
  - Valid `permissions` and `validDomains` with placeholder tokens.
- **Gaps / Issues:**
  - `{{BOT_APP_ID}}` and `{{BACKEND_FQDN}}` are placeholders requiring manual replacement — no automated substitution script exists (the `go_live_guide.md` documents this as a manual step).
  - No `webApplicationInfo` section for SSO/OBO token flow (referenced in the technical spec as an Entra ID requirement).
  - No `composeExtensions` (message extensions) — acceptable for PoC but noted in spec as potential.
  - `"supportsFiles": false` — the bot cannot receive file uploads, which would be needed for "edit existing TWI" scenarios where users upload a document.
  - No `localizationInfo` for Hungarian language declaration.
  - The manifest `id` field uses `{{BOT_APP_ID}}` — this should be a unique GUID for the Teams app, not necessarily the same as the bot's Entra ID app registration client ID (though they can be the same for simple bots).
  - No `defaultInstallScope` or `defaultGroupCapability` — Teams will prompt the user to choose scope on install.
