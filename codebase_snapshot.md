# Codebase Snapshot — agentize.eu TWI PoC

> Generated: 2026-03-06

---

## 1. DIRECTORY TREE

```
TWI_POC/
├── .claude/
│   ├── settings.local.json                          [config]
│   └── worktrees/
│       └── eager-jackson/                           [other]
├── .cursor/
│   ├── rules/
│   │   ├── azure-service-clients.mdc                [doc]
│   │   ├── bicep-infra-conventions.mdc              [doc]
│   │   ├── bot-adaptive-cards.mdc                   [doc]
│   │   ├── eu-ai-act-compliance.mdc                 [doc]
│   │   ├── langgraph-agent-patterns.mdc             [doc]
│   │   └── python-backend-patterns.mdc              [doc]
│   └── skills/
│       ├── agentize-poc-architecture/
│       │   └── SKILL.md                             [doc]
│       ├── agentize-poc-azure-infra/
│       │   └── SKILL.md                             [doc]
│       ├── agentize-poc-bot-cards/
│       │   └── SKILL.md                             [doc]
│       └── agentize-poc-langgraph/
│           └── SKILL.md                             [doc]
├── .devcontainer/
│   └── devcontainer.json                            [config]
├── .github/
│   └── workflows/
│       └── deploy.yml                               [config]
├── .gitignore                                       [config]
├── .flake8                                          [config]
├── .pre-commit-config.yaml                          [config]
├── agent_vendor_guide_v2.docx                       [doc]
├── codebase_snapshot.md                             [doc]
├── go_live_guide.md                                 [doc]
├── poc_technical_spec.md                            [doc]
├── poc_technical_spec.md.pdf                        [doc]
├── poc_vibe_coding_context.md                       [doc]
├── poc_vibe_coding_context.md.pdf                   [doc]
├── poc-backend/
│   ├── .devcontainer/
│   │   └── devcontainer.json                        [config]
│   ├── .env.example                                 [config]
│   ├── Dockerfile                                   [config]
│   ├── pyproject.toml                               [config]
│   ├── requirements.txt                             [config]
│   ├── setup.cfg                                    [config]
│   ├── app/
│   │   ├── __init__.py                              [code]
│   │   ├── main.py                                  [code]
│   │   ├── config.py                                [code]
│   │   ├── agent/
│   │   │   ├── __init__.py                          [code]
│   │   │   ├── graph.py                             [code]
│   │   │   ├── state.py                             [code]
│   │   │   ├── nodes/
│   │   │   │   ├── __init__.py                      [code]
│   │   │   │   ├── approve.py                       [code]
│   │   │   │   ├── audit.py                         [code]
│   │   │   │   ├── generate.py                      [code]
│   │   │   │   ├── intent.py                        [code]
│   │   │   │   ├── output.py                        [code]
│   │   │   │   ├── process_input.py                 [code]
│   │   │   │   ├── review.py                        [code]
│   │   │   │   └── revise.py                        [code]
│   │   │   └── tools/
│   │   │       ├── __init__.py                      [code]
│   │   │       └── pdf_generator.py                 [code]
│   │   ├── bot/
│   │   │   ├── __init__.py                          [code]
│   │   │   ├── adaptive_cards.py                    [code]
│   │   │   └── bot_handler.py                       [code]
│   │   ├── models/
│   │   │   └── __init__.py                          [code]
│   │   ├── services/
│   │   │   ├── __init__.py                          [code]
│   │   │   ├── ai_foundry.py                        [code]
│   │   │   ├── blob_storage.py                      [code]
│   │   │   ├── checkpoint.py                        [code]
│   │   │   ├── cosmos_db.py                         [code]
│   │   │   └── key_vault.py                         [code]
│   │   └── templates/
│   │       └── twi_template.html                    [code]
│   ├── infra/
│   │   ├── main.bicep                               [code]
│   │   ├── parameters.example.json                  [config]
│   │   ├── deploy.ps1                               [code]
│   │   ├── deploy.sh                                [code]
│   │   └── validate.ps1                             [code]
│   └── tests/
│       ├── __init__.py                              [code]
│       ├── conftest.py                              [code]
│       ├── test_ai_foundry.py                       [code]
│       ├── test_blob_storage.py                     [code]
│       ├── test_bot_handler.py                      [code]
│       ├── test_checkpoint_integration.py           [code]
│       ├── test_cosmos_db.py                        [code]
│       ├── test_generation.py                       [code]
│       ├── test_graph.py                            [code]
│       ├── test_output.py                           [code]
│       └── test_pdf.py                              [code]
└── teams-app/
    ├── manifest.json                                [config]
    ├── color.png                                    [other]
    └── outline.png                                  [other]
```

---

## 2. TECH STACK DETECTED

### LLM / Agent Layer
| Component | Source | Version Constraint |
|---|---|---|
| LangGraph | requirements.txt | `>=1.0.0` |
| LangChain Core | requirements.txt | `>=1.2.0` |
| LangSmith | requirements.txt | `>=0.7.0` |
| Azure AI Inference SDK | requirements.txt | `>=1.0.0b1,<2.0.0` |
| Mistral Large (default model) | config.py, main.bicep | `gpt-4o` |
| GPT-4o (alternative) | main.bicep | `gpt-4o` |

### Backend
| Component | Source | Version Constraint |
|---|---|---|
| Python | pyproject.toml, Dockerfile | `>=3.11` (runtime: 3.12-slim) |
| FastAPI | requirements.txt | `>=0.135.0` |
| Uvicorn | requirements.txt | `>=0.41.0` |
| Bot Framework (botbuilder-core) | requirements.txt | `>=4.17.0` |
| Bot Framework (aiohttp integration) | requirements.txt | `>=4.17.0` |
| aiohttp | requirements.txt | `>=3.10.0` |
| Pydantic | requirements.txt | `>=2.12.0` |
| Pydantic Settings | requirements.txt | `>=2.13.0` |
| python-dotenv | requirements.txt | `>=1.2.0` |
| Jinja2 | requirements.txt | `>=3.1.0` |
| WeasyPrint | requirements.txt | `>=68.0` |
| Markdown | requirements.txt | `>=3.10.0` |

### Frontend
| Component | Source | Notes |
|---|---|---|
| Microsoft Teams (Adaptive Cards v1.4) | teams-app/manifest.json | Manifest schema v1.17 |
| Telegram (fallback, text-only) | bot_handler.py | Interactive actions NOT supported |

### Infrastructure
| Component | Source | Notes |
|---|---|---|
| Azure Container Apps | main.bicep | 1 CPU / 2 GiB, min 1 replica |
| Azure AI Foundry (CognitiveServices) | main.bicep | DataZoneStandard SKU, Sweden Central |
| Azure Virtual Network + NSG | main.bicep | /16 VNet, /23 Container Apps subnet |
| Azure Container App Environment | main.bicep | External ingress, Log Analytics |
| Azure Bot Service | main.bicep | S1, SingleTenant, Teams + Telegram channels |
| Bicep (IaC) | main.bicep | Resource Group scope |
| GitHub Actions CI/CD | deploy.yml | Build Docker -> GHCR -> Container App update |
| Docker | Dockerfile | python:3.12-slim base |
| Dev Containers | devcontainer.json (x2) | Python 3.12 + Azure CLI + Docker-in-Docker |

### Auth
| Component | Source | Notes |
|---|---|---|
| Entra ID (App Registration) | main.bicep, deploy.ps1 | SingleTenant, User.Read Graph permission |
| Bot Framework JWT Validation | main.py | JwtTokenValidation on /api/messages |
| Azure RBAC (Key Vault) | main.bicep | System identity -> KV Secrets User |

### Storage
| Component | Source | Notes |
|---|---|---|
| Azure Cosmos DB (MongoDB API) | main.bicep, cosmos_db.py | Serverless, MongoDB 7.0 |
| Azure Blob Storage | main.bicep, blob_storage.py | Standard_LRS, SAS URLs (24h) |
| Azure Key Vault | main.bicep, key_vault.py | Standard tier, RBAC auth, soft delete |

### Observability
| Component | Source | Notes |
|---|---|---|
| Azure Application Insights | main.bicep, main.py | OpenTelemetry integration |
| OpenTelemetry SDK | requirements.txt | `>=1.36.0,<1.40.0` |
| Azure Monitor OpenTelemetry | requirements.txt | `>=1.6.13,<1.7.0` |
| Log Analytics Workspace | main.bicep | 30-day retention |

### Dev / Test
| Component | Source | Notes |
|---|---|---|
| pytest | requirements.txt | `>=9.0.0` |
| pytest-asyncio | requirements.txt | `>=1.3.0`, `asyncio_mode = "auto"` |
| httpx | requirements.txt | `>=0.28.0` |
| Gitleaks (pre-commit) | .pre-commit-config.yaml | v8.18.4 |
| flake8 | .flake8, setup.cfg | max-line-length 120 |
| mypy | pyproject.toml | strict mode, ignore_missing_imports |
| Hatchling (build) | pyproject.toml | Build backend |

---

## 3. ARCHITECTURE SUMMARY

This system is an enterprise AI platform (PoC) built by agentize.eu that generates **TWI (Training Within Industry) work instructions** through a conversational bot interface on Microsoft Teams (primary) and Telegram (secondary, limited). The backend is a **FastAPI** application hosted on **Azure Container Apps** in Sweden Central, ensuring EU data residency via the DataZoneStandard SKU for AI Foundry.

The core processing engine is a **LangGraph state machine** (`app/agent/graph.py`) implementing a multi-node workflow: intent classification -> input processing -> TWI document generation -> human-in-the-loop review -> optional revision loop (max 3 rounds) -> mandatory final approval -> PDF output -> audit logging. The graph uses **two human-in-the-loop interrupts** (`interrupt_before=["review", "approve"]`), pausing execution to collect user feedback via **Adaptive Cards** in Teams.

The LLM integration goes through **Azure AI Foundry** (`app/services/ai_foundry.py`), calling Mistral Large (or GPT-4o) for intent classification (temperature=0.1) and TWI generation (temperature=0.3). Every AI-generated output is labelled with an EU AI Act compliance warning.

Approved documents are rendered as **A4 PDFs** using a Jinja2 -> Markdown -> WeasyPrint pipeline (`app/agent/tools/pdf_generator.py`), uploaded to **Azure Blob Storage** with 24-hour SAS URLs, and metadata is persisted in **Cosmos DB** (MongoDB API) across four collections: `conversations`, `agent_state`, `generated_documents`, and `audit_log`.

The **Bot Framework adapter** in `app/main.py` receives messages at `/api/messages`, validates JWT tokens from Azure Bot Service, and delegates to `AgentizeBotHandler`, which orchestrates the LangGraph invocations and card-based interactions. The bot handler includes a Telegram fallback that renders Adaptive Card content as plain text, though interactive actions (approve/reject/edit) are not supported on Telegram.

Infrastructure is fully defined in a single **Bicep template** (`infra/main.bicep`) with automated deployment scripts for both PowerShell and Bash. Secrets are stored in **Azure Key Vault** and injected into the Container App via Key Vault references. A **GitHub Actions workflow** builds the Docker image, pushes to GHCR, and updates the Container App.

The main entry point is `app/main.py` (FastAPI app), which exposes three routes: `POST /api/messages` (bot endpoint), `GET /health`, and `GET /` (root info). The infrastructure entry point is `infra/main.bicep` with `infra/deploy.ps1` or `infra/deploy.sh` as the deployment orchestrators.

---

## 4. FILE-BY-FILE SUMMARY

### Application Code

#### `poc-backend/app/main.py`
- **Purpose:** FastAPI application entry point; configures Bot Framework adapter, routes, and telemetry.
- **Key functions/classes:** `messages()` (POST /api/messages), `health()`, `root()`, `_on_error()`.
- **External deps:** `fastapi`, `botbuilder-core`, `botbuilder.connector.auth.JwtTokenValidation`, `azure.monitor.opentelemetry`.

#### `poc-backend/app/config.py`
- **Purpose:** Centralized configuration via Pydantic Settings; loads from environment/.env file.
- **Key classes:** `Settings(BaseSettings)` -- all config fields with defaults.
- **External deps:** `pydantic_settings`.

#### `poc-backend/app/agent/graph.py`
- **Purpose:** Defines and compiles the LangGraph state machine; provides `run_agent()` for invocation/resumption.
- **Key functions:** `create_agent_graph()`, `get_graph()` (singleton), `run_agent()`, `_build_resume_state()`, `should_generate()`, `after_review()`, `after_revision()`, `clarify_node()`, `_create_checkpointer()`.
- **External deps:** `langgraph.graph.StateGraph`, `langgraph.checkpoint.memory.MemorySaver`.

#### `poc-backend/app/agent/state.py`
- **Purpose:** TypedDict definition for the LangGraph agent state schema.
- **Key classes:** `AgentState(TypedDict)` -- 15 fields covering input, processing, revision, output, and audit.
- **External deps:** None (stdlib typing only).

#### `poc-backend/app/agent/nodes/intent.py`
- **Purpose:** Classifies user intent via LLM call (temperature=0.1).
- **Key functions:** `intent_node(state)` -- returns state with `intent` field set.
- **External deps:** `app.services.ai_foundry.call_llm`.

#### `poc-backend/app/agent/nodes/process_input.py`
- **Purpose:** Lightweight input structuring (placeholder for future NER/extraction).
- **Key functions:** `process_input_node(state)` -- wraps message into `processed_input` dict.
- **External deps:** None.

#### `poc-backend/app/agent/nodes/generate.py`
- **Purpose:** Generates or revises a TWI document draft via LLM (temperature=0.3).
- **Key functions:** `generate_node(state)` -- calls LLM with system prompt + user message, prepends EU AI Act label.
- **External deps:** `app.services.ai_foundry.call_llm`, `app.config.settings`.

#### `poc-backend/app/agent/nodes/review.py`
- **Purpose:** Human-in-the-loop checkpoint #1; graph pauses here for user review.
- **Key functions:** `review_node(state)` -- sets `status="review_needed"`.
- **External deps:** None.

#### `poc-backend/app/agent/nodes/revise.py`
- **Purpose:** Increments revision counter before re-entering the generate node.
- **Key functions:** `revise_node(state)` -- increments `revision_count`, sets `status="revision_requested"`.
- **External deps:** None.

#### `poc-backend/app/agent/nodes/approve.py`
- **Purpose:** Human-in-the-loop checkpoint #2; graph pauses here for final approval.
- **Key functions:** `approve_node(state)` -- sets `status="approved"`.
- **External deps:** None.

#### `poc-backend/app/agent/nodes/output.py`
- **Purpose:** Generates PDF, uploads to Blob Storage, saves metadata to Cosmos DB.
- **Key functions:** `output_node(state)` -- orchestrates PDF gen, upload, and DB save.
- **External deps:** `app.agent.tools.pdf_generator`, `app.services.blob_storage.upload_pdf`, `app.services.cosmos_db.DocumentStore`.

#### `poc-backend/app/agent/nodes/audit.py`
- **Purpose:** Writes immutable audit log entry to Cosmos DB for EU AI Act compliance.
- **Key functions:** `audit_node(state)` -- logs event to `audit_log` collection.
- **External deps:** `app.services.cosmos_db.AuditStore`.

#### `poc-backend/app/agent/tools/pdf_generator.py`
- **Purpose:** Converts TWI Markdown draft to A4 PDF via Jinja2 template + WeasyPrint.
- **Key functions:** `generate_twi_pdf(content, metadata, user_id, approval_timestamp)`, `extract_title(content)`.
- **External deps:** `jinja2`, `weasyprint`, `markdown`.

#### `poc-backend/app/bot/bot_handler.py`
- **Purpose:** Bot Framework activity handler; routes text messages and Adaptive Card actions to LangGraph.
- **Key classes:** `AgentizeBotHandler(ActivityHandler)`.
- **Key methods:** `on_message_activity()`, `on_members_added_activity()`, `_handle_text_message()`, `_handle_card_action()`, `_send_card()` (with Telegram fallback), `_send_message()`, `_is_telegram()`.
- **External deps:** `botbuilder.core`, `app.agent.graph.get_graph`/`run_agent`, `app.bot.adaptive_cards`, `app.services.cosmos_db.ConversationStore`.

#### `poc-backend/app/bot/adaptive_cards.py`
- **Purpose:** Builds Adaptive Card JSON payloads for all four bot interaction points.
- **Key functions:** `create_review_card()`, `create_approval_card()`, `create_result_card()`, `create_welcome_card()`.
- **External deps:** None (pure dict construction).

#### `poc-backend/app/services/ai_foundry.py`
- **Purpose:** Async client wrapper for Azure AI Foundry (ChatCompletionsClient).
- **Key functions:** `call_llm(prompt, system_prompt, temperature, max_tokens)` -> `(content, tokens)`, `_get_client()`.
- **External deps:** `azure.ai.inference.aio.ChatCompletionsClient`, `azure.core.credentials.AzureKeyCredential`.

#### `poc-backend/app/services/blob_storage.py`
- **Purpose:** Uploads PDF bytes to Azure Blob Storage and generates 24-hour SAS URL.
- **Key functions:** `upload_pdf(pdf_bytes, blob_name)` -> SAS URL string, `_get_client()`.
- **External deps:** `azure.storage.blob.BlobServiceClient`, `azure.storage.blob.generate_blob_sas`.

#### `poc-backend/app/services/cosmos_db.py`
- **Purpose:** Motor-based async MongoDB client for Cosmos DB; provides three store classes.
- **Key classes:** `ConversationStore` (get_or_create, activity tracking), `AuditStore` (immutable log), `DocumentStore` (approved docs).
- **Key function:** `_get_db()` -- singleton Motor database handle.
- **External deps:** `motor.motor_asyncio.AsyncIOMotorClient`.

#### `poc-backend/app/services/key_vault.py`
- **Purpose:** Optional async Key Vault secret client for runtime secret reads.
- **Key functions:** `get_secret(name)` -> secret value string, `_get_client()`.
- **External deps:** `azure.identity.aio.DefaultAzureCredential`, `azure.keyvault.secrets.aio.SecretClient`.

#### `poc-backend/app/services/checkpoint.py`
- **Purpose:** Cosmos DB (MongoDB API) backed LangGraph checkpointer replacing MemorySaver.
- **Key classes:** `MongoDBSaver(BaseCheckpointSaver)`.
- **Key methods:** `aget_tuple()`, `alist()`, `aput()`, `aput_writes()`, `ensure_indexes()`.
- **External deps:** `langgraph.checkpoint.base`, `langchain_core.runnables.RunnableConfig`, `app.services.cosmos_db._get_db`.

### Infrastructure Code

#### `poc-backend/infra/main.bicep`
- **Purpose:** Complete Azure infrastructure definition for the PoC (550 lines).
- **Key resources:** Log Analytics, NSG, VNet (2 subnets), Key Vault, Application Insights, Container App Environment, AI Foundry + model deployment, Cosmos DB (MongoDB API) + 4 collections, Storage Account + blob container, Container App, RBAC role assignment, Bot Service + Teams channel + optional Telegram channel.
- **External deps:** Azure Resource Manager APIs.

#### `poc-backend/infra/parameters.example.json`
- **Purpose:** Example Bicep parameter file with placeholder values.
- **External deps:** None.

#### `poc-backend/infra/deploy.ps1`
- **Purpose:** PowerShell deployment orchestrator (8 steps: App Reg -> RG -> Bicep -> Keys -> KV RBAC -> KV Secrets -> Restart -> .env).
- **External deps:** Azure CLI (`az`).

#### `poc-backend/infra/deploy.sh`
- **Purpose:** Bash equivalent of deploy.ps1 for Linux/CI environments.
- **External deps:** Azure CLI (`az`), `python3` (for JSON parsing).

#### `poc-backend/infra/validate.ps1`
- **Purpose:** Post-deployment validation script (10 checks: login, RG, resources, model, KV secrets, collections, blob, health, channels, AI connectivity).
- **External deps:** Azure CLI (`az`), `Invoke-RestMethod`.

### Configuration Files

#### `poc-backend/Dockerfile`
- **Purpose:** Multi-stage Docker build for the FastAPI backend; installs WeasyPrint system deps, creates non-root user, configures health check.

#### `poc-backend/pyproject.toml`
- **Purpose:** Python project metadata, dependencies, pytest config, mypy strict mode.

#### `poc-backend/requirements.txt`
- **Purpose:** Canonical dependency list for Docker builds (mirrors pyproject.toml).

#### `poc-backend/.env.example`
- **Purpose:** Template environment file with all required configuration variables.

#### `.github/workflows/deploy.yml`
- **Purpose:** GitHub Actions CI/CD -- builds Docker image, pushes to GHCR, deploys to Container App on push to main.

#### `teams-app/manifest.json`
- **Purpose:** Microsoft Teams app manifest with placeholder tokens (`{{BOT_APP_ID}}`, `{{BACKEND_FQDN}}`).

#### `.devcontainer/devcontainer.json` (root)
- **Purpose:** VS Code Dev Container config for the full repo (Python 3.12, Azure CLI, Docker-in-Docker).

#### `poc-backend/.devcontainer/devcontainer.json`
- **Purpose:** VS Code Dev Container config for the backend subdirectory only.

#### `.pre-commit-config.yaml`
- **Purpose:** Pre-commit hooks configuration -- Gitleaks secret scanning only.

#### `.flake8` / `poc-backend/setup.cfg`
- **Purpose:** Flake8 linting configuration (max 120 chars, relaxed E203/W503).

### Test Files

#### `poc-backend/tests/conftest.py`
- **Purpose:** Shared pytest fixtures: `mock_llm_response`, `sample_agent_state`, `sample_draft`.

#### `poc-backend/tests/test_graph.py`
- **Purpose:** Tests for LangGraph routing functions, resume state builder, graph compilation, intent node, and revise node.
- **Test count:** 17 test methods across 6 classes.

#### `poc-backend/tests/test_bot_handler.py`
- **Purpose:** Tests for AgentizeBotHandler: text message handling, card action routing, error handling, Telegram fallback, welcome card.
- **Test count:** 22 test methods across 5 classes.

#### `poc-backend/tests/test_generation.py`
- **Purpose:** Tests for TWI generation node (EU AI Act label, revision context, metadata, temperature), intent temperature, process_input node, and Adaptive Card structure.
- **Test count:** 17 test methods across 4 classes.

#### `poc-backend/tests/test_ai_foundry.py`
- **Purpose:** Tests for the AI Foundry service client (call_llm): response parsing, system prompt, temperature/max_tokens.
- **Test count:** 4 test methods.

#### `poc-backend/tests/test_blob_storage.py`
- **Purpose:** Tests for Blob Storage upload_pdf: SAS URL generation, missing account_key error.
- **Test count:** 2 test methods.

#### `poc-backend/tests/test_cosmos_db.py`
- **Purpose:** Tests for DocumentStore.save: insert_one call, created_at field.
- **Test count:** 1 test function.

#### `poc-backend/tests/test_output.py`
- **Purpose:** Tests for output_node: PDF generation, blob upload, DocumentStore save, returned state.
- **Test count:** 1 test function.

#### `poc-backend/tests/test_pdf.py`
- **Purpose:** Tests for PDF generation pipeline: title extraction, PDF byte output, HTML rendering, approval box, EU AI Act footer.
- **Test count:** 11 test methods across 2 classes.

#### `poc-backend/tests/test_checkpoint_integration.py`
- **Purpose:** Integration tests for MongoDBSaver (skipped unless COSMOS_CONNECTION is set): put/get round-trip, alist ordering, pending_writes.
- **Test count:** 4 test functions (conditionally skipped).

### Templates

#### `poc-backend/app/templates/twi_template.html`
- **Purpose:** Jinja2 HTML template for A4 PDF rendering of TWI documents; includes EU AI Act warning banner, approval box, custom CSS for print layout.

---

## 5. OPEN ISSUES / CODE SMELLS

### Hardcoded Values

1. **`poc-backend/app/agent/tools/pdf_generator.py:10`** -- `FileSystemLoader("app/templates")` uses a relative path. This works when the CWD is `/app` inside Docker, but will break if the application is launched from any other directory (e.g., during development or testing from the project root).

2. **`poc-backend/app/config.py:8`** -- `ai_model: str = "gpt-4o"` is the default model. The same string appears in `generate.py:77`, `main.bicep:17`, `parameters.example.json:12`, etc. A single source of truth would be better.

3. **`poc-backend/app/bot/bot_handler.py:47`** -- Hungarian error messages are hardcoded throughout bot_handler.py (lines 47, 91-95, 101, 113-116, 121-123, 139-141, 145-148, 153, 182-184, 199-201, 207-209, 219, 231, 246-248, 254-256, 264-266, 281-283). There is no i18n/localization framework -- adding a second language would require touching dozens of lines.

### Missing Error Handling / Robustness

4. **`poc-backend/app/services/ai_foundry.py:14-18`** -- The singleton `_client` is never closed. If the connection drops or credentials rotate, the stale client persists for the lifetime of the process. There is no retry/backoff logic for transient LLM API failures.

5. **`poc-backend/app/services/cosmos_db.py:28`** -- The singleton Motor client (`_client`) is never closed. In a Container App with graceful shutdown, open connections may linger.

6. **`poc-backend/app/services/blob_storage.py:22`** -- The singleton `BlobServiceClient` is never closed. Same concern as above.

7. **`poc-backend/app/services/key_vault.py:35`** -- `DefaultAzureCredential()` is created without specifying `exclude_*` options. In a Container App with system-assigned identity, this is fine, but locally it may try multiple credential types and produce confusing timeout errors.

8. **`poc-backend/app/main.py:62`** -- `Activity().deserialize(body)` does not validate that `body` is a valid Activity structure. A malformed JSON payload could produce cryptic errors rather than a clean 400 response.

9. **`poc-backend/app/agent/graph.py:80-81`** -- `aget_state` is called inside a try/except that catches all exceptions and silently continues (line 97-99). This masks real bugs -- e.g., if Cosmos DB is unreachable, the guard is silently skipped and a duplicate run may be started.

### Structural Issues

10. **`poc-backend/app/models/__init__.py`** -- Empty module. The `models/` package is never used anywhere in the codebase. This suggests an incomplete feature or premature directory creation.

11. **`poc-backend/app/agent/tools/__init__.py`** -- Empty module. The `tools/` package only contains `pdf_generator.py`, which is more of a utility than a "tool" in the LangGraph sense (it is never registered as a LangGraph tool).

12. **`poc-backend/app/bot/bot_handler.py:295-297`** -- `_is_telegram()` is defined as a static method but is never called anywhere in the codebase. The Telegram check is done inline via `channel_id == "telegram"` at line 328.

13. **`poc-backend/app/bot/bot_handler.py:300-304`** -- `_send_message()` accepts `channel_id` parameter but ignores it completely (line 304 just calls `send_activity(text)` regardless of channel). The parameter exists for future Telegram-specific formatting but is unused.

14. **`poc-backend/app/bot/adaptive_cards.py:63-64`** -- The full draft text is embedded in `Action.Submit` data payloads (`"draft": draft`). For long drafts, this inflates the Adaptive Card JSON far beyond the 28KB Teams limit mentioned in the comment at line 8. The `_DRAFT_DISPLAY_MAX_CHARS` truncation only applies to the visible TextBlock, not the action data payloads.

15. **`poc-backend/app/agent/graph.py:166-185`** -- `run_agent()` constructs an `AgentState` with `title` absent from the TypedDict definition in `state.py`. The `output_node` at line 59 adds `"title"` to the state dict, but `AgentState` TypedDict does not declare it. This works at runtime (TypedDict is not enforced), but is a type-safety gap.

### Security Concerns

16. **`poc-backend/app/services/key_vault.py:58`** -- `logger.info("Retrieved secret '%s' from Key Vault.", name)` logs the secret name. While not logging the value, in some configurations the secret name itself may be sensitive.

17. **`poc-backend/app/services/ai_foundry.py:17`** -- `AzureKeyCredential(settings.ai_foundry_key)` uses a plain API key. The key is sourced from environment variables which is correct for Container App KV references, but the key_vault.py service (designed for runtime secret fetching) is never used to dynamically retrieve or rotate this key.

18. **`poc-backend/app/agent/tools/pdf_generator.py:11`** -- `autoescape=False` on the Jinja2 Environment. The comment says "HTML is trusted -- generated by the system," but the draft content originates from LLM output, which could theoretically contain malicious HTML/JS if prompt injection occurs. Since the output is a PDF (not served as web HTML), the practical risk is low, but it violates defense-in-depth.

### Test Coverage Gaps

19. **No tests for `app/services/key_vault.py`** -- The Key Vault service has zero test coverage.

20. **No tests for `app/services/cosmos_db.ConversationStore`** -- Only `DocumentStore.save` is tested; `ConversationStore.get_or_create` (including the update path) has no tests.

21. **No tests for `app/services/cosmos_db.AuditStore`** -- The audit logging path has no unit tests.

22. **`poc-backend/tests/test_checkpoint_integration.py`** -- All 4 tests are skipped in CI unless COSMOS_CONNECTION is set. The CI pipeline (deploy.yml) does not provision a test database, so these tests effectively never run in CI.

### Miscellaneous

23. **`poc-backend/app/agent/graph.py:4`** -- `MemorySaver` is imported at module level even when `MongoDBSaver` is used. Not a bug, but unnecessary import when Cosmos is configured.

24. **Two devcontainer.json files** -- `.devcontainer/devcontainer.json` (root) and `poc-backend/.devcontainer/devcontainer.json` have different configurations (different extensions, different names, different postCreateCommand). This may confuse developers.

25. **No `validate.sh`** -- `deploy.sh` references "Run ./validate.sh" in its summary (line 295), but only `validate.ps1` exists. There is no bash equivalent of the validation script.

---

## 6. KNOWN GAPS VS SPEC

### Dockerfile
**Status: IMPLEMENTED**

The `poc-backend/Dockerfile` is complete and production-ready:
- Uses `python:3.12-slim` base image
- Installs WeasyPrint system dependencies (pango, harfbuzz, libffi, gdk-pixbuf)
- Creates non-root user (`appuser`, UID 1000)
- Copies requirements.txt and app/ code
- Configures HEALTHCHECK (30s interval, curl to /health)
- Runs uvicorn with 2 workers on port 8000

No gaps identified.

---

### key_vault.py Service
**Status: IMPLEMENTED (but unused at runtime)**

`poc-backend/app/services/key_vault.py` implements:
- Singleton async `SecretClient` via `DefaultAzureCredential`
- `get_secret(name)` function for runtime secret reads
- Proper error handling (RuntimeError if KEY_VAULT_URL not configured)

**Gap:** The service is never called by any other module. All secrets are injected via Container App Key Vault references (environment variables resolved at startup), as noted in the module docstring. The `key_vault_url` config field defaults to `""` and is documented as optional. This is by design for the PoC, but means the service is dead code that has **zero test coverage**.

---

### Cosmos DB-backed LangGraph Checkpointer (not MemorySaver)
**Status: IMPLEMENTED**

`poc-backend/app/services/checkpoint.py` implements `MongoDBSaver(BaseCheckpointSaver)`:
- Full async implementation: `aget_tuple()`, `alist()`, `aput()`, `aput_writes()`
- Compound unique index on `(thread_id, checkpoint_id)`
- TTL index on `created_at` (default 30 days)
- Upsert semantics for checkpoint persistence
- Pending writes support

`poc-backend/app/agent/graph.py:117-134` implements `_create_checkpointer()`:
- Uses `MongoDBSaver` when `settings.cosmos_connection` is configured
- Falls back to `MemorySaver` when no connection string (local dev)
- Graceful fallback with warning on MongoDBSaver init failure

**Gap:** The sync wrapper methods (`get_tuple`, `list`, `put`, `put_writes`) at lines 244-272 raise `NotImplementedError`. While the app is fully async and never calls these, newer LangGraph versions may invoke sync methods in certain code paths (e.g., during graph compilation or serialization). Integration tests exist but are skipped in CI.

---

### LangGraph Resume Bug in bot_handler.py
**Status: PARTIAL -- potential bug identified**

The resume flow in `bot_handler.py` works as follows:
1. `_handle_card_action()` receives a card submission with `action` field
2. For `"request_edit"` (line 179): calls `run_agent(resume_from="revision", context={"feedback": feedback})`
3. For `"final_approve"` (line 228): calls `run_agent(resume_from="output", context={"timestamp": timestamp})`
4. `run_agent()` in `graph.py:158-164`: calls `graph.aupdate_state()` then `graph.ainvoke(None, config)`

**Potential bugs / concerns:**

1. **Resume targets do not match interrupt points.** The graph is configured with `interrupt_before=["review", "approve"]` (graph.py:113). When the graph pauses before `review`, the next expected nodes are determined by the `after_review` conditional edge. However, `_build_resume_state("revision")` sets `status="revision_requested"`, which causes `after_review` to route to `"revise"`. This is correct. But for `_build_resume_state("output")` setting `status="approved"`, `after_review` routes to `"approve"` -- which then hits the second interrupt (`interrupt_before=["approve"]`). The graph will pause *again* before `approve`, requiring yet another resume. This means a single "final_approve" card action may not actually reach the `output` node.

2. **Line 80-99: `aget_state` guard.** When the graph has a paused state (line 83: `existing.next` is truthy), the bot sends a Hungarian warning and returns without processing. This is correct behavior for preventing duplicate runs. However, after a reject action (line 280-285), the graph state still has checkpointed data -- but the reject flow simply sends a text message without clearing/resetting the graph state. A subsequent message from the same conversation may incorrectly trigger the "already paused" warning even though the user intends to start fresh.

3. **Draft passed via card data vs. graph state.** The `request_edit` action at line 181 reads `feedback` from `value.get("feedback")`, but the original draft is passed through the card's `data` payload (not read from graph state). The resume path in `run_agent()` only updates `revision_feedback` in the state, while the generate node at `generate.py:51-56` reads `state.get("revision_feedback")` and `state.get("draft")`. The draft should already be in the checkpoint, but the feedback from the card's Input.Text field may not be propagated correctly if the card's `data.feedback` key differs from the Input.Text `id` -- in this case, the Input.Text has `id="feedback"` (adaptive_cards.py:52) which overwrites the card action's `data` dict, so it should work. This is fragile coupling.

---

### Telegram Channel Handling
**Status: PARTIAL**

**Implemented:**
- `main.bicep:503-514`: Telegram channel resource (conditional on `telegramBotToken` being non-empty)
- `config.py:28`: `telegram_bot_token` configuration field
- `bot_handler.py:295-297`: `_is_telegram()` static method
- `bot_handler.py:328-346`: Telegram fallback in `_send_card()` -- extracts TextBlock text, FactSet facts, and Action.OpenUrl links into plain text
- `bot_handler.py:315-326`: Detailed docstring warning about Telegram limitations

**Missing / Not Implemented:**
- **Interactive actions on Telegram are NOT supported.** The Telegram fallback silently drops `Action.Submit` and `Input.Text` elements (documented in docstring at lines 315-326). A Telegram user can view generated drafts and download PDFs via URL, but **cannot approve, reject, or request edits**. This makes the Telegram channel effectively read-only for the TWI workflow.
- **No Telegram inline keyboard adapter.** The docstring at line 325-326 acknowledges this: "Full Telegram interactive support would require a dedicated inline-keyboard adapter (not yet implemented)."
- **`_is_telegram()` is unused.** The actual Telegram check is done via `channel_id == "telegram"` at line 328, not via the static method.
- **`_send_message()` ignores channel_id.** Despite accepting the parameter, it sends identical plain text regardless of channel (line 304). No Telegram-specific Markdown formatting (bold, links, etc.).

---

### Teams App Manifest Completeness
**Status: IMPLEMENTED -- with template placeholders**

`teams-app/manifest.json` is a well-structured v1.17 manifest that includes:
- Schema reference: `https://developer.microsoft.com/en-us/json-schemas/teams/v1.17/MicrosoftTeams.schema.json`
- Developer info (agentize.eu with privacy/terms URLs)
- Bot registration with scopes: `personal`, `team`, `groupChat`
- Command list: "Uj TWI" and "Segitseg" (Hungarian)
- Icons: `color.png` and `outline.png` (files exist in teams-app/)
- `validDomains`: `["{{BACKEND_FQDN}}"]`
- `webApplicationInfo` with resource URI
- Default install scope: personal
- Localization: `defaultLanguageTag: "hu"`

**Gaps:**
1. **Placeholder tokens not automated.** `{{BOT_APP_ID}}` and `{{BACKEND_FQDN}}` must be manually replaced before sideloading. Neither `deploy.ps1` nor `deploy.sh` perform this substitution. There is no manifest packaging step in the CI/CD pipeline.
2. **No .zip packaging.** Teams requires the manifest to be uploaded as a .zip containing `manifest.json`, `color.png`, and `outline.png`. There is no build step or script to produce this .zip.
3. **Missing `composeExtensions` or `messageExtensions`.** The bot only supports plain text input and Adaptive Card responses. There are no message extensions for rich input (e.g., task module for structured TWI parameters).
4. **`supportsFiles: false`** -- The bot cannot receive file attachments from users, which could be useful for importing existing TWI documents or reference materials.
5. **Privacy and Terms URLs** (`https://agentize.eu/privacy`, `https://agentize.eu/terms`) may not be live pages -- these are not validated in the codebase.
