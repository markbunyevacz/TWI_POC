# agentize.eu PoC — Implementation Specification

| Field | Value |
|---|---|
| **Version** | 1.3 |
| **Date** | 2026-03-12 |
| **Status** | Implemented |
| **Owner** | agentize.eu |
| **Confidentiality** | Internal |
| **Original design spec** | `archive/poc_technical_spec.md` v1.0 (2026-02-26) [ARCHIVED] |
| **Deployment guide** | `go_live_guide.md` |

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [User Functionalities & Workflows](#2-user-functionalities--workflows)
3. [Architecture](#3-architecture)
4. [Technology Stack](#4-technology-stack)
5. [LangGraph Agent](#5-langgraph-agent)
6. [Azure Service Clients](#6-azure-service-clients)
7. [Bot Framework & Adaptive Cards](#7-bot-framework--adaptive-cards)
8. [Database Schema](#8-database-schema)
9. [PDF Generation Pipeline](#9-pdf-generation-pipeline)
10. [Infrastructure (Bicep)](#10-infrastructure-bicep)
11. [Environment Variables](#11-environment-variables)
12. [CI/CD & Containerization](#12-cicd--containerization)
13. [Cost Model](#13-cost-model)
14. [Known Risks & Mitigations](#14-known-risks--mitigations)
15. [Success Criteria](#15-success-criteria)
16. [Deviations from Original Spec](#16-deviations-from-original-spec)

---

## 1. Project Overview

### 1.1 What This Is

Enterprise AI platform PoC: a Microsoft Teams and Telegram chatbot powered by a LangGraph agent that generates structured TWI (Training Within Industry) work instructions through a multi-checkpoint human approval workflow, producing PDF output. The system runs inside the customer's own Azure subscription with VNET isolation and EU Data Zone Standard data residency (Sweden Central).

### 1.2 Scope

**In scope:**

- Azure infrastructure from Bicep template (single-command deploy)
- FastAPI backend + LangGraph agent orchestration
- Teams Bot + Telegram Bot (Bot Framework, multi-channel)
- Adaptive Cards interaction (multi-checkpoint approval)
- PDF generation (primary output format)
- Cosmos DB state management + LangGraph checkpointing
- Entra ID app registration + JWT token validation
- EU AI Act transparency labeling on all AI outputs
- Basic VNET isolation

**Out of scope:**

- Azure AI Search / RAG (the agent works from user input, not document retrieval)
- Hallucination framework (confidence scoring, golden dataset) -- the multi-checkpoint approval workflow handles this
- Private Link full hardening (7-point checklist)
- TISAX documentation
- React Tab editor (Adaptive Cards are sufficient)
- SharePoint integration (PDF download via SAS URL instead)
- Multi-tenancy
- Metered billing / Marketplace integration
- Managed Application wrapper (plain resource group + RBAC)

### 1.3 Key Decisions

These decisions are locked and were agreed upon by the project team:

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **LangGraph** (not LangChain chains) | GA, production-ready, architecturally distinct from chain-based approaches |
| 2 | **No AI Search / RAG in PoC** | Agent works from user input, not document retrieval. Eliminates largest cost item ($245/mo) |
| 3 | **Sweden Central, Data Zone Standard** | EU data residency guarantee. Non-negotiable for automotive industry clients |
| 4 | **Bot Framework** (Teams SDK) | Multi-channel (Teams + Telegram). Stable SDK choice among 3 competing options |
| 5 | **Not a Managed Application** | Plain resource group + RBAC. Deny Assignment would have blocked AI Foundry |
| 6 | **PDF as primary output** | Current outputs are already delivered as PDFs; this does not change |
| 7 | **Multi-checkpoint approval** (not hallucination framework) | Continuous interaction + review + final approval. No need for confidence scoring |
| 8 | **EU AI Act labeling** | "AI generated content" label mandatory on all outputs since Feb 2025 |
| 9 | **Cosmos DB (MongoDB API)** | Compatible with existing codebase. Serverless mode for PoC |
| 10 | **Token cost to agent vendor** | Platform infrastructure is fixed cost; LLM consumption is the agent vendor's responsibility |

---

## 2. User Functionalities & Workflows

### 2.1 Business Context & Problem Statement

**What is TWI?**

Training Within Industry (TWI) is a structured methodology developed during World War II to rapidly train workers in manufacturing processes. A TWI Job Instruction (JI) sheet breaks down a task into numbered steps, with each step containing three elements: the *main step* (what to do), *key points* (how to do it right), and *reasons why* (why each key point matters). This three-column format has been adopted globally in automotive, aerospace, and precision manufacturing as the standard for work instruction documentation.

**The current pain point**

Manufacturing companies -- particularly in the automotive/DACH region -- produce TWI sheets manually. A process engineer observes a task, writes the steps, has a supervisor review them, formats the document, and distributes the PDF. This process takes 2-4 hours per instruction and is error-prone: steps are missed, safety warnings are incomplete, key points lack the "why" rationale, and formatting is inconsistent. When processes change, existing instructions must be rewritten from scratch.

**What this system does**

The agentize.eu AI platform replaces the manual drafting step with LLM-assisted generation. The user describes a manufacturing process in natural language (in Hungarian), and the system produces a structured TWI document following the standard 6-section format. A human expert reviews, revises if needed, and explicitly approves the content before a branded PDF is generated. The AI accelerates the drafting from hours to minutes; the human retains full authority over accuracy and completeness.

**Why the approval workflow matters**

EU AI Act (Article 50, effective February 2025) requires that AI-generated content is labeled as such and that a human is accountable for the final output. The dual-checkpoint approval workflow (draft review + final verification) satisfies this requirement while also matching the existing quality assurance culture in manufacturing: no document leaves the system without a named approver.

### 2.2 Target Users & Personas

| Persona | Role | Typical interaction | Frequency |
|---|---|---|---|
| **Process Engineer** | Creates new TWI sheets for new or changed manufacturing processes | Describes the process, reviews the AI draft for technical accuracy, requests revisions for missing steps or safety details, approves the final version | Weekly (during process changes or new product introductions) |
| **Shop Floor Supervisor** | Validates that instructions are practical and match real workshop conditions | Reviews the draft for feasibility, checks that tool names and machine IDs are correct, may request language simplification | As needed (when new instructions arrive for their area) |
| **Quality Manager** | Ensures compliance with internal standards and regulatory requirements | Verifies that safety sections are complete, checks that the quality control section meets audit requirements, gives final approval | Monthly (during batch reviews or audit preparation) |
| **Training Coordinator** | Uses approved TWI sheets to onboard new operators | Does not generate instructions but consumes the PDF output; may request revisions to existing sheets via `edit_twi` intent | Quarterly (during onboarding cycles) |

All users interact through Microsoft Teams (primary channel) in a personal chat with the bot. Telegram is available as a secondary channel with reduced functionality.

### 2.3 Language & Locale

- All bot interactions are in **Hungarian** (prompts, card labels, error messages, processing indicators)
- The TWI system prompt enforces Hungarian output from the LLM with technical terms optionally given in English in parentheses -- e.g., *"hőmérséklet-szabályozó (thermostat)"*
- The 6-section TWI headers use standard Hungarian manufacturing terminology: CIM, CEL, SZUKSEGES ANYAGOK ES ESZKOZOK, BIZTONSAGI ELOIRASOK, LEPESEK, MINOSEGI ELLENORZES
- PDF output is in Hungarian with the EU AI Act footer in Hungarian: *"agentize.eu -- AI altal generalt tartalom"*
- The Teams app manifest sets `defaultLanguageTag: "hu"` with an English localization file (`strings-en.json`) for command labels
- No runtime language switching is supported in the PoC; adding a second locale would require touching bot handler messages, system prompts, and card templates

### 2.4 Onboarding

When a user adds the bot in Teams or Telegram, they receive a Welcome card introducing the AI assistant with an example prompt: *"Készíts egy TWI utasítást a CNC-01 gép beállításáról"*.

### 2.5 Message Submission & Intent Classification

The user sends a natural-language request in the personal bot chat. There is no separate "start generation" button; the conversation is free-form. The bot responds with *"Feldolgozom a kérésedet..."* (a typing indicator in Teams) and the LangGraph agent classifies the intent at `temperature=0.1`:

| Intent | Behaviour | Example user message |
|---|---|---|
| `generate_twi` | New TWI work instruction generation | *"Készíts TWI utasítást a CNC-01 gép beállításáról"* |
| `edit_twi` | Modify an existing TWI (requires a previous draft in the conversation) | *"Módosítsd a 3. lépést, adj hozzá hőmérséklet-ellenőrzést"* |
| `question` | General Q&A -- the agent answers directly, skips structured processing | *"Mi a TWI módszertan?"* |
| `unknown` | Clarification prompt sent back to user | *"Szia"* (greeting with no actionable content) |

**Business rule:** If the user message is ambiguous but contains a process description (tools, steps, materials), the classifier should favour `generate_twi` over `unknown`. The threshold for `unknown` is a message that contains no identifiable manufacturing process content.

### 2.6 TWI Draft Generation

For `generate_twi` / `edit_twi`, the input is structured and sent to the LLM at `temperature=0.3` with a system prompt enforcing a 6-section TWI format. Each section has specific business expectations:

| # | Section | Hungarian header | What the LLM must produce | Quality criteria |
|---|---------|-----------------|--------------------------|-----------------|
| 1 | **Title** | CIM | A concise, descriptive title identifying the process and equipment | Must include machine/workstation ID if mentioned by user |
| 2 | **Objective** | CEL | One or two sentences explaining the purpose of the instruction | Must state the expected outcome, not just the action |
| 3 | **Materials & Tools** | SZUKSEGES ANYAGOK ES ESZKOZOK | Bulleted list of required materials, tools, PPE, and consumables | Must include quantities or specifications when provided by the user |
| 4 | **Safety Instructions** | BIZTONSAGI ELOIRASOK | Numbered safety precautions, hazard warnings, required PPE | Must cover electrical, chemical, and mechanical hazards relevant to the described process; must not be empty |
| 5 | **Steps** | LEPESEK | Numbered main steps; each step has sub-items for *key points* and *reasons why* | Minimum 3 steps; each step must have at least one key point and one reason; steps must be in executable order |
| 6 | **Quality Check** | MINOSEGI ELLENORZES | Verification criteria, tolerances, inspection points | Must include measurable pass/fail criteria when the process involves measurable outputs |

**Business rules for generation:**

- The system prompt is in Hungarian and instructs the LLM to respond exclusively in Hungarian
- Technical terms may optionally include the English equivalent in parentheses
- The **LEPESEK** section follows the standard TWI Job Instruction three-column format: *FO LEPES* (main step), *FONTOS PONT* (key point), *INDOKLAS* (reason why)
- If the user provides insufficient detail (e.g., only a title with no process description), the agent should still generate a best-effort draft but flag gaps explicitly in the output text (e.g., *"[Kérem pontosítsa a hőmérsékleti értékeket]"*)
- For `edit_twi`, the previous draft is loaded from conversation state and the user's edit instructions are applied as a delta; the full 6-section structure is preserved

The EU AI Act label is automatically prepended to every draft: *"⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges."*

### 2.7 Human-in-the-Loop #1: Draft Review

The graph interrupts (`interrupt_before=["review"]`) and sends the user a **Review Adaptive Card** containing:

- The draft text (truncated to 2,000 characters for Adaptive Card rendering limits; full draft is retained in agent state)
- EU AI Act metadata line with model name and generation timestamp
- An optional feedback text input field (`Input.Text`, placeholder: *"Módosítási javaslatok..."*)
- Three action buttons:

| Button label (HU) | Action ID | Result | Graph routing |
|---|---|---|---|
| **Jóváhagyom a vázlatot** | `approve` | Moves to final approval | `review` -> `approve` |
| **Szerkesztés kérem** | `request_edit` | Enters revision loop with user feedback | `review` -> `revise` -> `generate` |
| **Elvetés** | `reject` | Discards draft, logs rejection to audit, ends flow | `review` -> `reject` -> `audit` -> `END` |

**Business rules for review:**

- The reviewer is expected to check: (1) technical accuracy of steps and safety instructions, (2) completeness of materials list, (3) correct use of machine/tool identifiers, (4) appropriate level of detail for the target operator audience
- If the user clicks **Szerkesztés kérem** without entering feedback text, the system re-prompts: *"Kérem, adja meg a módosítási javaslatait."* The revision cannot proceed with empty feedback.
- If the user clicks **Elvetés**, the reason is optional; the `reject` node records `"user_rejected"` as the status in the audit trail regardless

### 2.8 Revision Loop

When the user requests edits, their feedback text is injected into the LLM prompt alongside the previous draft. The system prompt instructs the LLM to treat the feedback as authoritative corrections -- the LLM must not argue with or ignore the feedback. The agent regenerates and presents a new Review card.

**Business rules for revisions:**

- The revision loop is hard-capped at **3 rounds** (`max_revision_count=3` in `AgentState`). After the third revision, the flow automatically advances to final approval. The user is informed: *"Elérted a maximális módosítási kört (3). A véglegesítéshez kérjük, hagyja jóvá."*
- Each revision preserves the full 6-section structure; the LLM may not drop sections even if the feedback only addresses one section
- The revision counter (`revision_count`) is tracked in agent state and persisted to the audit trail
- If the Teams connection drops mid-revision (e.g., timeout), the graph state is persisted in the MongoDB checkpointer and can be resumed when the user next sends a message

### 2.9 Human-in-the-Loop #2: Final Approval

After the user approves the draft, the graph interrupts again (`interrupt_before=["approve"]`) and a **Final Approval Adaptive Card** appears with an explicit verification message. This second checkpoint is mandatory per EU AI Act -- no PDF can be generated without it. The card displays:

- A confirmation prompt: *"Ellenőrizted a tartalmat? A jóváhagyás után PDF generálás indul."*
- The approver's display name (from Teams/Telegram context)
- Timestamp of the approval request

| Button label (HU) | Action ID | Result |
|---|---|---|
| **Ellenőriztem és jóváhagyom** | `final_approve` | Triggers PDF generation; records `approval_timestamp` in audit |
| **Vissza a szerkesztéshez** | `back_to_edit` | Returns to revision loop (does not count against the 3-round cap) |

**Business rule:** The `approval_timestamp` recorded in the audit trail is the moment the user clicks **Ellenőriztem és jóváhagyom**, not the moment the PDF is generated. This distinction matters for audit compliance -- the human decision timestamp is the legally binding one.

### 2.10 PDF Generation & Delivery

Upon final approval, the `output_node` executes the PDF pipeline:

| Step | Action | Detail |
|---|---|---|
| 1 | **Markdown to HTML** | The approved draft markdown is rendered into an A4 HTML document using a Jinja2 template (`twi_template.html`) with agentize.eu branding, corporate colors, and structured section layout |
| 2 | **HTML to PDF** | WeasyPrint converts the HTML to a PDF document with proper page breaks, headers, and footers |
| 3 | **Upload to Blob** | The PDF is uploaded to Azure Blob Storage container `twi-documents` with blob name pattern: `{user_id}/{timestamp}_{sanitized_title}.pdf` |
| 4 | **SAS URL generation** | A read-only SAS token is generated with a **24-hour expiry**; after expiry the link returns HTTP 403 |
| 5 | **Result card** | A Result Adaptive Card is sent to the user containing the download link and a summary |

**PDF layout specification:**

- **Header block:** Title, generation date, LLM model name, document version, revision count
- **EU AI Act warning box:** Yellow-background box at the top of the first page: *"⚠️ Ez a dokumentum AI által generált tartalmat tartalmaz. Az emberi felülvizsgálatot és jóváhagyást [approver_name] végezte [approval_timestamp] időpontban."*
- **Body:** Full 6-section TWI content with numbered steps, sub-items for key points and reasons
- **Approval box:** Green-bordered box showing approver display name, approval timestamp (ISO 8601), and revision count
- **Footer (every page):** *"agentize.eu — AI által generált tartalom — {page}/{pages}"*

**Business rules for PDF delivery:**

- The PDF filename is deterministic and includes the user ID to enable per-user blob listing in future phases
- The 24-hour SAS expiry is a PoC simplification; production would use shorter-lived tokens or Azure AD-authenticated access
- If WeasyPrint fails (e.g., malformed HTML from unusual LLM output), the system logs the error and sends the user a plain-text fallback message with the approved draft content. The PDF failure does not void the approval.
- The Result card includes a *"Letöltés"* (Download) button linking to the SAS URL and a metadata line showing the file size

### 2.11 Audit Trail

After PDF delivery (or after rejection), the `audit_node` logs a record to the Cosmos DB `audit_log` collection. This log is invisible to the user and exists for compliance and operational monitoring.

| Field | Type | Description |
|---|---|---|
| `user_id` | string | Teams/Telegram user identifier |
| `tenant_id` | string | Azure AD tenant ID (Teams) or bot instance ID (Telegram) |
| `channel` | string | `"msteams"` or `"telegram"` |
| `intent` | string | The classified intent (`generate_twi`, `edit_twi`, `question`) |
| `llm_model` | string | Model used for generation (e.g., `"gpt-4o"`) |
| `llm_tokens_input` | integer | Input tokens consumed |
| `llm_tokens_output` | integer | Output tokens consumed |
| `approval_timestamp` | string (ISO 8601 UTC) | When the user clicked the final approval button; `null` for rejections |
| `revision_count` | integer | Number of revision rounds (0 if approved on first attempt) |
| `pdf_blob_name` | string | Blob Storage path of the generated PDF; `null` for rejections |
| `status` | string | `"approved"`, `"user_rejected"`, or `"error"` |
| `created_at` | string (ISO 8601 UTC) | Timestamp of the audit record creation |

**Business rationale:** The audit trail serves three purposes: (1) EU AI Act compliance evidence that a human approved the content, (2) cost tracking by recording token consumption per generation, and (3) operational analytics to identify patterns (e.g., high revision counts indicating unclear user inputs or poor LLM output quality).

### 2.12 Telegram Variant

Telegram does not support Adaptive Cards. The bot implements the same logical workflow using plain markdown text messages and text-based command keywords.

**Mapping of Teams flow to Telegram:**

| Workflow step | Teams (Adaptive Cards) | Telegram (text messages) |
|---|---|---|
| Welcome | Welcome card with example prompt | Plain text greeting with example prompt |
| Processing indicator | *"Feldolgozom a kérésedet..."* | Same text message |
| Draft review | Review card with buttons | Draft text + instruction: *"Válasz: Igen / Nem / Módosítás: [feedback]"* |
| Revision request | Feedback text input on card | User sends *"Módosítás: [feedback text]"* as a message |
| Final approval | Approval card with two buttons | Text prompt: *"Elfogadás / Elutasítás"* |
| PDF delivery | Result card with download button | Text message with SAS URL hyperlink |

**Telegram-specific limitations (PoC):**

- **No second approval checkpoint:** The Telegram flow currently skips the `approve` interrupt and proceeds directly from draft approval to PDF generation. This is a known PoC simplification. For production, a text-based confirmation step should be added.
- **No structured feedback parsing:** User feedback on Telegram is free-form text; there is no form validation. If the user sends an unrecognized keyword, the bot re-prompts.
- **Message length limit:** Telegram messages are capped at 4,096 characters. Long drafts are split across multiple messages with a *"(folytatás...)"* indicator.
- **No inline buttons:** The PoC uses keyword-based commands rather than Telegram inline keyboards. Adding inline buttons would improve UX but is out of scope.
- **No file upload:** PDF is delivered as a download URL, not as a file attachment. Telegram supports file sending via the Bot API, but this is not implemented in the PoC.

### 2.13 Workflow Diagram

```
[User message]
     |
     v
 classify_intent --- unknown ---> clarify ---> END
     |
     |-- generate_twi / edit_twi
     |         |
     |    process_input --> generate --> [INTERRUPT #1: Review Card]
     |                                       |          |           |
     |                                  approve    request_edit   reject --> audit --> END
     |                                       |          |
     |                                       |     revise --> generate --> [Review Card]
     |                                       |               (max 3 rounds)
     |                                       v
     |                             [INTERRUPT #2: Approval Card]
     |                                       |
     |                                 final_approve
     |                                       |
     |                                 output (PDF) --> audit --> END
     |                                       |
     |                                 [Result Card + PDF link]
     |
     |-- question --> generate (Q&A) --> END
```

### 2.14 EU AI Act Compliance Summary

| Requirement | Implementation |
|---|---|
| In-text label | Prepended to every draft in `generate_node` |
| PDF footer | `twi_template.html`: "agentize.eu -- AI altal generalt tartalom -- {page}/{pages}" |
| Adaptive Card label | Warning line with model name and generation timestamp on every card |
| Two approval checkpoints | `interrupt_before=["review", "approve"]` in graph compilation |
| Audit trail | `audit_node` logs to `audit_log` collection with model, tokens, approval timestamp |
| LLM temperature | Intent classification: 0.1; TWI generation: 0.3 |

### 2.15 Error Handling & Edge Cases

The system must handle the following scenarios gracefully without crashing or leaving the user in an unresponsive state:

| Scenario | System behaviour | User-facing message (HU) |
|---|---|---|
| **LLM timeout** (>60s response) | Retry once; if still fails, abort generation and notify user | *"A generálás időtúllépés miatt megszakadt. Kérem, próbálja újra."* |
| **LLM rate limit** (HTTP 429) | Exponential backoff (1s, 2s, 4s); max 3 retries; then abort | *"A rendszer jelenleg túlterhelt. Kérem, próbálja újra néhány perc múlva."* |
| **Empty LLM output** | Treat as generation failure; do not present an empty review card | *"A generálás sikertelen volt. Kérem, próbálja újra részletesebb leírással."* |
| **Malformed TWI sections** | If fewer than 6 sections are detected in the output, re-prompt the LLM once with explicit section enforcement | Same as empty output if retry fails |
| **Blob Storage upload failure** | Retry once; if fails, send the approved markdown as plain text to the user | *"A PDF feltöltés sikertelen. Az alábbi szöveges változatot mentse el:"* |
| **Cosmos DB write failure** (audit) | Log to Application Insights; do not block the user flow -- the PDF has already been delivered | No user-facing message (silent failure, logged) |
| **Teams card action timeout** (user doesn't respond) | Graph state is persisted in MongoDB checkpointer; when the user sends any new message, the bot detects a pending graph and resumes | *"Folytatjuk az előző kérésedet..."* |
| **Telegram unrecognized keyword** | Re-prompt with valid options | *"Kérem, válasszon: Igen / Nem / Módosítás: [megjegyzés]"* |
| **User sends new message during active generation** | The new message is queued; the current generation completes first | *"Folyamatban van egy kérés feldolgozása. Kérem, várjon."* |

### 2.16 Non-Functional Requirements (Business-Level)

| Category | Requirement | PoC target | Production target (future) |
|---|---|---|---|
| **Response time** | Time from user message to review card delivery | < 30 seconds for typical process descriptions (5-15 sentences) | < 15 seconds |
| **Availability** | System uptime during business hours (CET 08:00-18:00) | Best effort (single Container App instance) | 99.5% SLA with auto-scaling |
| **Concurrent users** | Simultaneous active generation workflows | Up to 5 (PoC testing) | 50+ with horizontal scaling |
| **Data residency** | All data stored within EU | Sweden Central region, VNET isolated | Same, with Private Link hardening |
| **Token budget** | Maximum tokens per single TWI generation cycle (including revisions) | ~8,000 input + ~4,000 output per generation | Same, with cost alerting |
| **PDF size** | Maximum generated PDF size | < 2 MB (typical: 100-300 KB for a 5-10 step instruction) | Same |
| **SAS URL lifetime** | Download link validity period | 24 hours | Configurable (1-72 hours) |
| **Audit retention** | How long audit records are kept | Indefinite (Cosmos DB serverless) | 7 years (regulatory minimum) |
| **Language support** | Supported interaction languages | Hungarian only | Hungarian + English + German |

---

## 3. Architecture

### 3.1 High-Level Architecture

```
+----------------------------------------------------------------------+
|                    AZURE VNET -- Sweden Central                       |
|                                                                      |
|  +-----------+     +---------------------+     +-----------------+   |
|  | Azure Bot |---->| Container App       |---->| Azure AI        |   |
|  | Service   |     | (FastAPI+LangGraph) |     | Foundry         |   |
|  | (global)  |     | port 8000           |     | (GPT-4o /       |   |
|  +-----+-----+     +------+------+-------+     |  Mistral Large) |   |
|        |                  |      |              +-----------------+   |
|  +-----+------+    +------+---+  +----------+                       |
|  | Teams /    |    | Cosmos DB|  | Blob     |   +----------------+   |
|  | Telegram   |    | (MongoDB |  | Storage  |   | Key Vault      |   |
|  | Channels   |    |  API)    |  | (PDF)    |   | (secrets)      |   |
|  +------------+    +---------+   +----------+   +----------------+   |
|                                                                      |
|  +------------------+     +----------------+                         |
|  | App Insights +   |     | Entra ID       |                        |
|  | Log Analytics    |     | (SSO / Auth)   |                        |
|  +------------------+     +----------------+                         |
+----------------------------------------------------------------------+
```

### 3.2 Request Flow

```
1. User --> Teams/Telegram: "Keszits egy TWI utasitast a CNC-01 gep beallitasarol"

2. Bot Service --> FastAPI: POST /api/messages
   {
     "type": "message",
     "text": "Keszits egy TWI utasitast...",
     "from": { "id": "user-entra-id", "name": "Kovacs Janos" },
     "channelId": "msteams" | "telegram",
     "conversation": { "id": "conv-123" }
   }

3. FastAPI: Entra ID JWT token validation (JwtTokenValidation.authenticate_request)

4. FastAPI --> LangGraph: invoke graph with AgentState
   {
     "user_id": "user-entra-id",
     "tenant_id": "poc-tenant",
     "channel": "msteams",
     "message": "Keszits egy TWI utasitast...",
     "conversation_id": "conv-123"
   }

5. LangGraph classify_intent --> "generate_twi"

6. LangGraph generate_node --> AI Foundry API:
   POST https://<endpoint>.swedencentral.inference.ai.azure.com/chat/completions
   {
     "model": "gpt-4o",
     "messages": [
       {"role": "system", "content": "<TWI system prompt>"},
       {"role": "user", "content": "Keszits egy TWI utasitast..."}
     ],
     "temperature": 0.3,
     "max_tokens": 4000
   }

7. LangGraph review_node --> INTERRUPT
   Bot sends Adaptive Card to user with draft

8. User approves --> LangGraph resumes via aupdate_state + ainvoke(None)

9. LangGraph output_node --> PDF generation --> Blob Storage upload
   Bot sends Result Card with SAS download link

10. LangGraph audit_node --> Cosmos DB audit_log
```

### 3.3 Resource Group Structure

```
Resource Group: rg-agentize-poc-swedencentral
+-- Log Analytics Workspace: log-agentize-poc
+-- Network Security Group: nsg-agentize-poc
+-- Virtual Network: vnet-agentize-poc
|   +-- Subnet: snet-container-apps (/23, 256+ IPs)
|   +-- Subnet: snet-private-endpoints (/24)
+-- Container App Environment: cae-agentize-poc
|   +-- Container App: ca-agentize-poc-backend (FastAPI + LangGraph)
+-- Azure AI Foundry: ai-agentize-poc
|   +-- Model Deployment: gpt-4o (DataZoneStandard SKU)
+-- Cosmos DB Account: cosmos-agentize-poc (MongoDB API, serverless)
|   +-- Database: agentize-poc-db
|       +-- Collection: conversations
|       +-- Collection: agent_state
|       +-- Collection: audit_log
|       +-- Collection: generated_documents
+-- Storage Account: stagentizepoc
|   +-- Container: pdf-output
+-- Key Vault: kv-agentize-poc (RBAC-enabled)
+-- Application Insights: appi-agentize-poc
+-- Azure Bot Service: bot-agentize-poc (global)
|   +-- Channel: Microsoft Teams
|   +-- Channel: Telegram (optional)
+-- Entra ID App Registration: app-agentize-poc (SingleTenant)
+-- RBAC: Container App MI --> Key Vault Secrets User
```

---

## 4. Technology Stack

### 4.1 Network & Security

| Component | Technology | Purpose |
|---|---|---|
| Virtual Network | Azure VNET (`10.0.0.0/16`) | Network isolation for all resources |
| Subnet: `snet-container-apps` | `/23` (256+ IPs) | Delegated to Container Apps Environment |
| Subnet: `snet-private-endpoints` | `/24` | Reserved for private endpoint hardening (MVP) |
| NSG | Network Security Group | Allows HTTPS + Bot Service inbound; denies everything else |
| Entra ID | Microsoft Identity Platform | SingleTenant app registration; JWT token validation |
| Key Vault | Azure Key Vault (RBAC-enabled) | Stores AI key, Cosmos connection, Bot password, Blob connection |

Secrets flow: Key Vault --> Container App secret refs (resolved at startup) --> `pydantic-settings` reads from env vars. No runtime Key Vault calls.

### 4.2 Compute

| Component | Technology | Details |
|---|---|---|
| Container App | Azure Container Apps | 1 CPU, 2Gi RAM; min 1 replica (no cold start); max 5 replicas |
| Runtime | Python 3.12-slim (Debian Bookworm) | Non-root user, health check on `/health` |
| Web Framework | FastAPI + Uvicorn (2 workers) | Endpoints: `/api/messages`, `/health`, `/` |
| Scaling | HTTP-based autoscaler | Triggers at 20 concurrent requests per replica |
| Identity | System-assigned Managed Identity | Granted Key Vault Secrets User role via RBAC |
| Probes | Liveness + Readiness | Both hit `/health` on port 8000 |

### 4.3 AI & Orchestration

| Component | Technology | Details |
|---|---|---|
| Orchestrator | LangGraph (StateGraph) | 9 nodes, conditional edges, 2 interrupt points |
| AI Foundry | Azure Cognitive Services (`AIServices` kind) | `DataZoneStandard` SKU, EU data residency |
| SDK | `azure-ai-inference` (async) | `AsyncChatCompletionsClient` with `AzureKeyCredential` |
| Models | GPT-4o (default) or Mistral Large 3 | Configurable via Bicep param + `AI_MODEL` env var |

### 4.4 Data & Storage

| Component | Technology | Details |
|---|---|---|
| Database | Cosmos DB (MongoDB API, serverless) | 4 collections, accessed via `motor` async driver |
| File Storage | Azure Blob Storage | PDF blobs at `twi/{conversation_id}/{uuid}.pdf` |
| Download | SAS token (24h expiry) | Read-only, time-limited; no public blob access |

### 4.5 Bot & UI

| Component | Technology | Details |
|---|---|---|
| Bot Service | Azure Bot Service (S1, global) | Routes Teams/Telegram to `/api/messages` |
| Bot SDK | `botbuilder-core` 4.17+ | `BotFrameworkAdapter` + `AgentizeBotHandler` |
| Teams UI | Adaptive Cards v1.4 | 4 card templates: Review, Approval, Result, Welcome |
| Teams Manifest | `teams-app/manifest.json` (v1.17) | Sideload-ready; placeholders `{{BOT_APP_ID}}`, `{{BACKEND_FQDN}}` |
| Teams Localization | `teams-app/strings-en.json` | English UI strings for command labels and descriptions |
| Telegram | Markdown text messages | Fallback for non-card-capable channels |

### 4.6 Observability & CI/CD

| Component | Technology | Details |
|---|---|---|
| App Insights | Azure Monitor OpenTelemetry | Auto-configured at startup |
| Log Analytics | Linked workspace | 30-day retention |
| CI/CD | GitHub Actions + Docker Buildx | Build --> GHCR --> `az containerapp update` |
| Dev Env | Devcontainer (primary) | Python 3.12 + Azure CLI + Docker-outside-of-Docker |
| Dev Env | Devcontainer (fallback) | `devcontainer.fallback.json` + `Dockerfile.fallback` for buildx-incompatible hosts |
| Dev Env Repair | `devcontainer-repair.ps1` | PowerShell script to diagnose and fix Docker/buildx issues |

### 4.7 Summary

| Layer | Technologies |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI + Uvicorn |
| AI orchestration | LangGraph |
| LLM access | Azure AI Foundry (`azure-ai-inference`) |
| Bot framework | Microsoft Bot Framework SDK (`botbuilder-core`) |
| UI (Teams) | Adaptive Cards v1.4 |
| Database | Cosmos DB (MongoDB API) via `motor` |
| File storage | Azure Blob Storage (SAS URLs) |
| PDF pipeline | Markdown --> Jinja2 --> WeasyPrint |
| Config | pydantic-settings |
| Auth | Entra ID (JWT validation) |
| IaC | Bicep |
| Container | Docker (python:3.12-slim-bookworm) |
| CI/CD | GitHub Actions |
| Observability | Azure Monitor OpenTelemetry + App Insights |

---

## 5. LangGraph Agent

### 5.1 AgentState

Source: `poc-backend/app/agent/state.py`

```python
class AgentState(TypedDict):
    # Input context
    user_id: str
    tenant_id: str
    conversation_id: str
    channel: str              # "msteams" | "telegram"
    message: str

    # Processing
    intent: Optional[str]          # "generate_twi" | "edit_twi" | "question" | "unknown"
    processed_input: Optional[dict]
    draft: Optional[str]
    draft_metadata: Optional[dict]  # {model, generated_at, revision}

    # Revision loop
    revision_feedback: Optional[str]
    revision_count: int

    # Output
    status: str  # "processing" | "review_needed" | "revision_requested" | "approved" | "completed" | "error"
    pdf_url: Optional[str]
    pdf_blob_name: Optional[str]

    # Audit / telemetry
    llm_model: Optional[str]
    llm_tokens_used: Optional[int]
    approval_timestamp: Optional[str]

    # Message history (LangGraph internal)
    messages: list[Any]
```

### 5.2 Graph Nodes

| Node | Source file | Purpose | LLM call |
|---|---|---|---|
| `classify_intent` | `nodes/intent.py` | Classifies user intent into 4 categories | Yes (temp=0.1, max_tokens=20) |
| `process_input` | `nodes/process_input.py` | Structures and validates user input | No |
| `generate` | `nodes/generate.py` | Generates or revises TWI draft | Yes (temp=0.3, max_tokens=4000) |
| `review` | `nodes/review.py` | Human-in-the-loop checkpoint #1 | No |
| `revise` | `nodes/revise.py` | Increments revision counter, sets feedback | No |
| `approve` | `nodes/approve.py` | Human-in-the-loop checkpoint #2 | No |
| `output` | `nodes/output.py` | PDF generation + Blob upload + DocumentStore save | No |
| `audit` | `nodes/audit.py` | Writes audit log to Cosmos DB (both happy and rejection paths) | No |
| `reject` | `graph.py` | Finalises rejection state so audit receives a `twi_rejected` event | No |
| `clarify` | `graph.py` | Returns `clarification_needed` status for unknown intent | No |

### 5.3 Conditional Edge Functions

Source: `poc-backend/app/agent/graph.py`

```python
def should_generate(state: AgentState) -> str:
    intent = state.get("intent", "unknown")
    if intent in ("generate_twi", "edit_twi"):
        return "process_input"
    if intent == "question":
        return "generate"
    return "clarify"

def after_review(state: AgentState) -> str:
    status = state.get("status", "")
    if status == "approved":
        return "approve"
    if status == "revision_requested":
        return "revise"
    return "reject"  # rejected → reject node → audit → END

def after_revision(state: AgentState) -> str:
    if state.get("revision_count", 0) >= 3:
        return "approve"      # Force final approval after 3 rounds
    return "regenerate"       # Maps to "generate" node via conditional edge map
```

All routing functions are pure -- no side effects, no I/O.

The `after_revision` function returns `"regenerate"` which the conditional edge map translates to the `generate` node: `{"regenerate": "generate", "approve": "approve"}`. This avoids a naming collision with the `generate` node on the intent routing path.

### 5.4 Graph Compilation

```python
builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["review", "approve"],
)
```

### 5.5 Checkpointer

The graph uses a **MongoDB-backed checkpointer** (`MongoDBSaver`) that persists state to the `agent_state` collection in Cosmos DB. If Cosmos DB is not configured, it falls back to an in-memory `MemorySaver`.

Source: `poc-backend/app/agent/mongodb_checkpointer.py`

The `MongoDBSaver` implements LangGraph's `BaseCheckpointSaver` interface with:
- `get()` -- retrieves the latest checkpoint for a thread
- `put()` -- upserts checkpoint with `thread_id + checkpoint_id` as composite key
- `list()` -- lists checkpoints sorted by `created_at` descending
- Indexes: `(thread_id, checkpoint_id)` unique, `(thread_id, created_at)` descending

### 5.6 Interrupt / Resume Pattern

When the graph hits an interrupt point (`review` or `approve`), the bot handler sends an Adaptive Card and waits. When the user responds:

```python
# 1. Patch the existing state with the user's action
await graph.aupdate_state(config, state_update)

# 2. Resume execution from the last interrupt
result = await graph.ainvoke(None, config)
```

Resume state patches are built by `_build_resume_state()`:
- `resume_from="revision"` sets `status="revision_requested"` + `revision_feedback`
- `resume_from="output"` sets `status="approved"` + `approval_timestamp`

---

## 6. Azure Service Clients

All clients use the **singleton pattern** -- one instance per process lifetime, lazily initialized on first use.

### 6.1 AI Foundry Client

Source: `poc-backend/app/services/ai_foundry.py`

```python
async def call_llm(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, int]:
    """Returns (response_text, total_tokens_used)."""
```

- Uses `AsyncChatCompletionsClient` from `azure-ai-inference`
- Authenticates via `AzureKeyCredential`
- Logs `input_tokens` and `output_tokens` on every call
- Returns a tuple of `(content, total_tokens)` for audit tracking
- Defaults to `settings.ai_temperature` (0.3) and `settings.ai_max_tokens` (4000)

### 6.2 Cosmos DB Client

Source: `poc-backend/app/services/cosmos_db.py`

Three store classes, all using `motor` async MongoDB driver:

| Class | Collection | Key operations |
|---|---|---|
| `ConversationStore` | `conversations` | `get_or_create()` -- upserts conversation, increments `message_count` |
| `AuditStore` | `audit_log` | `log()` -- inserts immutable audit entry |
| `DocumentStore` | `generated_documents` | `save()` -- inserts approved document metadata |

All stores gracefully degrade if Cosmos DB is not configured (log a warning, return empty/noop).

### 6.3 Blob Storage Client

Source: `poc-backend/app/services/blob_storage.py`

```python
async def upload_pdf(pdf_bytes: bytes, blob_name: str) -> str:
    """Upload PDF to Blob Storage, return 24-hour SAS URL."""
```

- Uses `BlobServiceClient` (sync SDK) wrapped in `asyncio.to_thread()` for async compatibility
- Generates a read-only SAS token with 24-hour expiry
- Falls back to plain blob URL if credential does not support SAS generation (managed identity)
- Blob path convention: `twi/{conversation_id}/{uuid}.pdf`

---

## 7. Bot Framework & Adaptive Cards

### 7.1 AgentizeBotHandler

Source: `poc-backend/app/bot/bot_handler.py`

The handler extends `ActivityHandler` and routes incoming activities:

1. **Adaptive Card submit** (`activity.value` is set) --> `_handle_card_action()`
2. **Telegram text** (channel is telegram, no card value) --> `_handle_telegram_text()`
3. **Normal text** (all other cases) --> `_handle_text_message()` --> LangGraph `run_agent()`

Class methods:

| Method | Purpose |
|---|---|
| `__init__()` | Initialises conversation store; graph is lazy-loaded |
| `_get_graph()` | Lazy singleton access to the compiled LangGraph graph |
| `on_message_activity()` | Entry point for all incoming messages; dispatches to the three handlers above |
| `on_members_added_activity()` | Sends Welcome card when bot is added to a conversation |
| `_handle_text_message()` | Invokes `run_agent()`, sends Review card or error message |
| `_handle_card_action()` | Routes Adaptive Card submit actions (see table below) |
| `_handle_telegram_text()` | Parses Telegram text commands (`igen`, `nem`, `modositas`) and resumes graph |
| `_handle_telegram_response()` | Formats LangGraph result as Telegram markdown text |
| `_send_card()` | Static method; sends Adaptive Card on Teams or falls back to plain text on Telegram |

Module-level Telegram helpers (not class methods):

| Function | Purpose |
|---|---|
| `_is_telegram_channel(channel_id)` | Returns `True` if channel is Telegram |
| `_format_telegram_review(draft, metadata)` | Formats draft as Telegram markdown with approve/edit/reject options |
| `_format_telegram_approval(draft, metadata)` | Formats final approval prompt for Telegram |
| `_format_telegram_result(pdf_url, title, metadata)` | Formats result with download link for Telegram |

Card action routing:

| `action` value | Behaviour |
|---|---|
| `approve_draft` | Teams: send Approval card. Telegram: directly resume to PDF output |
| `request_edit` | Resume graph at `revision` with user feedback |
| `final_approve` | Resume graph at `output`, generate PDF |
| `reject` | Resume graph at `reject` node, which routes to audit, then inform user |

### 7.2 Adaptive Card Templates

Source: `poc-backend/app/bot/adaptive_cards.py`

All cards use Adaptive Card schema v1.4. Draft text is truncated to 2,000 characters (`MAX_DRAFT_DISPLAY_LENGTH`).

**Review Card** (`create_review_card`) -- Human-in-the-loop #1:
- Title: "TWI Vazlat -- Felulvizsgalat szukseges"
- EU AI Act warning with model + timestamp
- Draft text display
- Feedback text input field (optional, multiline)
- Actions: Approve / Edit / Reject

**Approval Card** (`create_approval_card`) -- Human-in-the-loop #2:
- Title: "Veglegesites -- Kotelezo Jovahagyas"
- Warning: "This document is AI-generated content. Please verify before finalizing."
- Draft text display
- Actions: Confirm approval / Back to editing

**Result Card** (`create_result_card`):
- Title: "Dokumentum elkeszult"
- FactSet: document title, format (PDF), model, approver
- Action: PDF download link (OpenUrl to SAS URL)

**Welcome Card** (`create_welcome_card`):
- Greeting message
- Description of capabilities
- Example prompt in monospace

### 7.3 Telegram Handling

Since Telegram does not support Adaptive Cards, the bot provides equivalent functionality via markdown-formatted text messages:

- `_format_telegram_review()` -- draft + options (Elfogadas / Modositas / Elutasitas)
- `_format_telegram_approval()` -- final confirmation (Igen / Nem)
- `_format_telegram_result()` -- title + approver + download link
- `_handle_telegram_text()` -- parses text commands: `igen/yes/elfogad`, `nem/no/elutasit`, `modositas/change/revise`

### 7.4 Authentication

Source: `poc-backend/app/main.py`

Every request to `/api/messages` undergoes Entra ID JWT token validation:

```python
credentials = SimpleCredentialProvider(settings.bot_app_id, settings.bot_app_password)
claims = await JwtTokenValidation.authenticate_request(activity, auth_header, credentials, "")
if not claims.is_authenticated:
    return Response(status_code=401)
```

---

## 8. Database Schema

Cosmos DB with MongoDB API, serverless mode. Database name: `agentize-poc-db`.

### 8.1 conversations

Active chat sessions with 90-day TTL.

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | Auto-generated |
| `conversation_id` | string | Bot Framework conversation ID |
| `user_id` | string | Entra ID user identifier |
| `tenant_id` | string | Tenant identifier ("poc-tenant" in PoC) |
| `channel` | string | "msteams" or "telegram" |
| `started_at` | ISODate | Conversation start time |
| `last_activity` | ISODate | Last message time (TTL anchor) |
| `message_count` | int | Incremented per message |
| `status` | string | "active", "completed", or "expired" |

**Indexes:** `{ conversation_id: 1 }` unique, `{ tenant_id: 1, user_id: 1 }`, `{ _ts: 1 }` TTL 90 days.

### 8.2 agent_state

LangGraph checkpoints managed by the `MongoDBSaver` checkpointer.

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | Auto-generated |
| `thread_id` | string | Conversation ID (partition key) |
| `checkpoint_id` | string | LangGraph checkpoint identifier |
| `parent_checkpoint_id` | string | Previous checkpoint (for history traversal) |
| `checkpoint` | object | LangGraph internal state blob |
| `channels` | object | Channel version metadata |
| `created_at` | ISODate | Checkpoint creation time |

**Indexes:** `{ thread_id: 1, checkpoint_id: 1 }` unique, `{ thread_id: 1, created_at: -1 }`.

### 8.3 generated_documents

Approved TWI documents with PDF references.

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | Auto-generated |
| `document_id` | string | UUID |
| `conversation_id` | string | Source conversation |
| `user_id` | string | Author |
| `tenant_id` | string | Tenant |
| `title` | string | Extracted from draft content |
| `content_type` | string | "twi" |
| `draft_content` | string | Final approved text |
| `pdf_blob_name` | string | Blob path: `twi/{conv_id}/{uuid}.pdf` |
| `pdf_url` | string | SAS URL (24h expiry) |
| `llm_model` | string | Model used for generation |
| `revision_count` | int | Number of revision rounds |
| `status` | string | "approved" |
| `created_at` | ISODate | Document creation time |
| `approved_at` | ISODate | Approval timestamp |
| `approved_by` | string | Approver user ID |

**Indexes:** `{ tenant_id: 1, created_at: -1 }`, `{ conversation_id: 1 }`.

### 8.4 audit_log

Immutable event trail for EU AI Act compliance.

| Field | Type | Description |
|---|---|---|
| `_id` | ObjectId | Auto-generated |
| `conversation_id` | string | Source conversation |
| `user_id` | string | Acting user |
| `tenant_id` | string | Tenant |
| `channel` | string | "msteams" or "telegram" |
| `event_type` | string | "twi_generated" |
| `intent` | string | Classified intent |
| `llm_model` | string | Model used |
| `llm_tokens_used` | int | Total tokens (input + output) |
| `revision_count` | int | Number of revision rounds |
| `pdf_blob_name` | string | Blob path of generated PDF |
| `status` | string | Final status |
| `approval_timestamp` | ISODate | When user approved |
| `created_at` | ISODate | Audit entry creation time |

**Indexes:** `{ tenant_id: 1, created_at: -1 }`, `{ event_type: 1 }`.

### 8.5 Pydantic Data Models

Source: `poc-backend/app/models/`

The `models` package provides validated Pydantic `BaseModel` classes that mirror the Cosmos DB collection schemas. They are used for type-safe construction and validation of documents before insertion.

| Model | Source file | Maps to collection | Key exports |
|---|---|---|---|
| `Conversation` | `conversation.py` | `conversations` | `Conversation`, `ConversationCreate` |
| `AuditEntry` | `audit_entry.py` | `audit_log` | `AuditEntry`, `AuditEventType` (Literal type) |
| `TWIDocument` | `twi_document.py` | `generated_documents` | `TWIDocument` |

`AuditEventType` is a `Literal["twi_generated", "twi_approved", "twi_rejected", "twi_revised"]` used to constrain the `event_type` field.

---

## 9. PDF Generation Pipeline

### 9.1 Pipeline

```
TWI draft text (markdown)
  --> markdown library (tables + fenced_code extensions) --> HTML fragment
  --> Jinja2 template rendering (twi_template.html) --> full HTML document
  --> WeasyPrint (HTML --> PDF, A4 page size)
  --> Blob Storage upload
  --> SAS URL (24-hour, read-only) returned to user
```

Source: `poc-backend/app/agent/tools/pdf_generator.py`

### 9.2 Jinja2 Template Variables

Source: `poc-backend/app/templates/twi_template.html`

| Variable | Source | Description |
|---|---|---|
| `{{ title }}` | Extracted from first non-warning line of draft | Document title (max 100 chars) |
| `{{ generated_at }}` | `draft_metadata.generated_at` | Generation timestamp |
| `{{ model }}` | `draft_metadata.model` | LLM model name |
| `{{ revision }}` | `draft_metadata.revision` | Revision round number |
| `{{ content_html }}` | Markdown-converted draft | Full TWI content as HTML (rendered with `| safe` filter) |
| `{{ approved }}` | Boolean | Whether to show approval box |
| `{{ approved_by }}` | `state.user_id` | Approver identifier |
| `{{ approved_at }}` | Current UTC time | Approval timestamp |

### 9.3 EU AI Act Footer

Rendered on every page via CSS `@page` rule:

```css
@bottom-center {
    content: "agentize.eu -- AI altal generalt tartalom -- " counter(page) "/" counter(pages);
    font-size: 8pt;
    color: #888;
}
```

### 9.4 PDF Styling

- A4 page size with 2cm margins
- Arial font, 11pt body, 1.5 line height
- Header: title in `#1b4f72`, 3px bottom border
- AI warning box: amber left border, `#fef5e7` background
- Steps: light grey cards with `#f8f9fa` background
- Approval box: green border `#27ae60`, `#eafaf1` background
- Tables: full-width, collapsed borders, header row in `#f1f3f4`

---

## 10. Infrastructure (Bicep)

Source: `poc-backend/infra/main.bicep` (~550 lines)

Deploy: `az deployment group create -g <rg> -f main.bicep -p @parameters.json`

### 10.1 Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `location` | string | `swedencentral` | Azure region (EU Data Zone Standard) |
| `projectPrefix` | string | `agentize-poc` | Naming prefix for all resources |
| `aiModel` | string | `gpt-4o` | AI Foundry model. Allowed: `gpt-4o`, `Mistral-Large-3`, `Mistral-medium-2505` |
| `minReplicas` | int | `1` | Container App min replicas (1 = no cold start) |
| `cosmosThroughputMode` | string | `serverless` | Cosmos DB mode. Allowed: `serverless`, `provisioned` |
| `botAppId` | string | (required) | Entra ID App Registration client ID |
| `botAppPassword` | secure string | (required) | Entra ID App Registration client secret |
| `telegramBotToken` | secure string | `""` | Telegram bot token (empty = skip channel) |
| `containerImage` | string | hello-world | Container image (override post-build) |

### 10.2 Key Resource Configurations

**NSG Rules:**
- `AllowHTTPSInbound` (priority 100): Internet --> port 443
- `AllowBotServiceInbound` (priority 110): AzureBotService tag --> port 443
- `DenyAllInbound` (priority 4096): deny all other inbound

**Container App:**
- `internal: false` (public IP so Bot Service can reach `/api/messages`)
- Secrets via Key Vault references (resolved at container start via managed identity)
- Liveness probe: `/health` every 30s, 3 failures before restart
- Readiness probe: `/health` every 10s, 3 failures before unready
- Scaling: min 1, max 5, HTTP rule at 20 concurrent requests

**AI Foundry:**
- `kind: AIServices`, `sku: S0`
- Model deployment: `DataZoneStandard` SKU (NOT `GlobalStandard`), 10K TPM capacity
- `disableLocalAuth: false` (key-based auth for PoC)

**Cosmos DB:**
- `kind: MongoDB`, serverless capabilities enabled
- MongoDB server version 7.0
- 4 collections with indexes defined in Bicep

**Key Vault:**
- RBAC authorization enabled
- Soft delete: 7 days
- Container App system identity granted `Key Vault Secrets User` role

---

## 11. Environment Variables

Source: `poc-backend/.env.example`

```
# Azure AI Foundry
AI_FOUNDRY_ENDPOINT=https://your-ai-foundry.swedencentral.inference.ai.azure.com
AI_FOUNDRY_KEY=<from Key Vault>
AI_MODEL=gpt-4o
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=4000

# Cosmos DB (MongoDB API)
COSMOS_CONNECTION=mongodb://<account>:<key>@<account>.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000
COSMOS_DATABASE=agentize-poc-db

# Blob Storage
BLOB_CONNECTION=DefaultEndpointsProtocol=https;AccountName=stagentizepoc;AccountKey=<key>;EndpointSuffix=core.windows.net
BLOB_CONTAINER=pdf-output

# Bot Framework
BOT_APP_ID=<Entra ID App Registration client ID>
BOT_APP_PASSWORD=<Entra ID App Registration client secret>

# Telegram (optional)
TELEGRAM_BOT_TOKEN=<from @BotFather>

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=<key>;IngestionEndpoint=https://swedencentral-1.in.applicationinsights.azure.com/

# App
ENVIRONMENT=poc
LOG_LEVEL=INFO
```

All variables are read by `pydantic-settings` (`BaseSettings` with `env_file=".env"`, case-insensitive). In production, these are injected via Container App environment variables backed by Key Vault secret references.

---

## 12. CI/CD & Containerization

### 12.1 Dockerfile

Source: `poc-backend/Dockerfile`

- Base image: `python:3.12-slim-bookworm`
- System dependencies for WeasyPrint: `libpango`, `libpangoft2`, `libharfbuzz`, `libffi-dev`, `libgdk-pixbuf2.0`
- Non-root user (`appuser`, UID 1000) for security
- Health check: `curl -f http://localhost:8000/health` every 30s
- Entrypoint: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`

### 12.2 GitHub Actions Pipeline

Source: `.github/workflows/deploy.yml`

Triggered on push to `main` branch (path filter: `poc-backend/**`).

Steps:
1. Checkout code
2. Login to Azure (`azure/login@v2`)
3. Set up Docker Buildx
4. Login to GitHub Container Registry (GHCR)
5. Build and push Docker image (tags: `${{ github.sha }}` + `latest`)
6. Deploy to Container App: `az containerapp update --image ghcr.io/agentize-eu/poc-backend:${{ github.sha }}`

### 12.3 Deployment

For full deployment instructions (infrastructure provisioning, Entra ID setup, Teams manifest sideloading, and end-to-end validation), see `go_live_guide.md`.

---

## 13. Cost Model

Monthly estimated costs (AI Search excluded from PoC scope):

| Component | Monthly Cost |
|---|---|
| Container Apps (1 app, minReplicas: 1) | ~$40-55 |
| Cosmos DB (serverless) | ~$10-30 |
| Blob Storage (LRS) | ~$3 |
| Key Vault | ~$1 |
| Private Endpoints (x3-4, MVP phase) | ~$22-30 |
| Application Insights | ~$5-15 |
| Bot Service (S1) | ~$0 (included) |
| **Platform infrastructure total** | **~$80-135/mo** |
| AI Foundry token cost (variable) | Agent vendor responsibility |

Sales price target: 2.5-3x markup --> ~$300-400/mo base.

---

## 14. Known Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| AI Foundry capacity in Sweden Central | Medium | Test on Day 1. Fallback: Germany West Central |
| Teams App sideload blocked by org policy | Low | Request admin permission, or demo via Telegram |
| WeasyPrint system dependencies in Docker | Low | Installed in Dockerfile (pango, harfbuzz, gdk-pixbuf) |
| Cosmos DB serverless cold start | Low | First query ~1-2s slower, then normal |
| Bot Framework token refresh | Low | Adapter handles refresh automatically |
| Adaptive Card size limit | Medium | Draft text truncated to 2,000 chars; full text in PDF |

---

## 15. Success Criteria

The PoC is considered complete when:

1. Bicep template deploys to Sweden Central in a single command
2. Full flow works from Teams: request --> generation --> review --> edit --> approval --> PDF
3. Same flow works from Telegram
4. PDF is downloadable, formatted, contains AI labeling and approval info
5. Audit log in Cosmos DB records: who, what, when, which model
6. EU AI Act labeling present on all AI-generated outputs
7. Multi-checkpoint approval works (review + final approval)
8. Revision loop works (edit request --> revision --> re-review)
9. 3-minute demo runs end-to-end without errors

---

## 16. Deviations from Original Spec

Changes made during implementation versus `archive/poc_technical_spec.md` v1.0:

| Area | Original Spec | Actual Implementation | Reason |
|---|---|---|---|
| Default AI model | `mistral-large-latest` | `gpt-4o` | Model availability; config default changed |
| Bicep model param | `['mistral-large-latest', 'gpt-4o']` | `['gpt-4o', 'Mistral-Large-3', 'Mistral-medium-2505']` | Expanded model options |
| Container App `internal` | `true` (VNET-only) | `false` (public IP) | Bot Service needs to reach `/api/messages` without Private Link |
| App Insights naming | `ai-agentize-poc-insights` | `appi-agentize-poc` | Azure naming convention updated |
| Log Analytics workspace | Not in spec | Added `log-agentize-poc` | Required for Container App + App Insights |
| Checkpointer | `MemorySaver` only | `MongoDBSaver` with `MemorySaver` fallback | Persistence across container restarts |
| AI Foundry client | Sync `ChatCompletionsClient` | Async `AsyncChatCompletionsClient` | Fixed sync-in-async issue |
| `call_llm` return type | `str` | `tuple[str, int]` | Added token tracking for audit |
| Blob upload | Sync `upload_blob()` | `asyncio.to_thread(upload_blob)` | Async-safe wrapping of sync SDK |
| Dockerfile | `python:3.12-slim`, runs as root | `python:3.12-slim-bookworm`, non-root user + HEALTHCHECK | Security hardening |
| Entra ID auth | Not in spec's code | `JwtTokenValidation.authenticate_request()` | Closed security gap |
| Graph resume | `graph.ainvoke(state_update, config)` | `graph.aupdate_state()` then `ainvoke(None)` | Correct LangGraph resume pattern |
| NSG rules | Not in spec | AllowHTTPS, AllowBotService, DenyAll | Network security |
| Key Vault soft delete | Not mentioned | `enableSoftDelete: true`, 7 days | Best practice |
| Container App RBAC | Not in spec | MI --> Key Vault Secrets User role | Managed identity integration |
| Container App probes | Not in spec | Liveness + Readiness on `/health` | Production readiness |

### 16.1 Dependency Version Drift

The original spec (`poc_technical_spec.md` v1.0) pinned dependencies with `==x.y.*`. During implementation the pinning strategy was changed to open floor versions (`>=x.y.z`) and several packages were upgraded to newer major/minor releases. A `requirements.lock` file now captures the exact resolved versions for reproducible Docker builds.

| Package | Spec Version | Code Version | Resolved Version | Risk | Notes |
|---|---|---|---|---|---|
| `langgraph` | `==0.3.*` | `>=1.0.0` | 1.1.2 | **Major** | 0.3 to 1.0 API jump; code migrated to `aupdate_state` + `ainvoke(None)` resume pattern |
| `langchain-core` | `==0.3.*` | `>=1.2.0` | 1.2.18 | **Major** | Only `RunnableConfig` import used; stable across versions |
| `langsmith` | `==0.2.*` | `>=0.7.0` | 0.7.16 | Medium | Transitive dependency of LangGraph; not directly imported |
| `fastapi` | `==0.115.*` | `>=0.135.0` | 0.135.1 | Low | No breaking API changes for our usage |
| `weasyprint` | `==63.*` | `>=68.0` | 68.1 | Medium | Rendering behavior may differ; PDF output should be re-validated |
| `botbuilder-core` | `==4.16.*` | `>=4.17.0` | 4.17.1 | Low | Minor version bump within same major |
| `pymongo` | `==4.10.*` | `>=4.16.0` | 4.16.0 | Low | Minor version bumps |
| `motor` | `==3.6.*` | `>=3.7.0` | 3.7.1 | Low | Minor |
| `pydantic` | `==2.10.*` | `>=2.12.0` | 2.12.5 | Low | Minor |
| `pydantic-settings` | `==2.7.*` | `>=2.13.0` | 2.13.1 | Low | Minor |
| `pytest-asyncio` | `==0.25.*` | `>=1.3.0` | 1.3.0 | Medium | Major version; `asyncio_mode = "auto"` in `pyproject.toml` handles the breaking change |
| `markdown` | *not in spec* | `>=3.10.0` | 3.10.2 | Low | Used in `pdf_generator.py` for markdown-to-HTML conversion; omitted from original spec |
| `opentelemetry-api` | `==1.29.*` | `>=1.36.0,<1.40.0` | 1.36.0 | Low | Capped upper bound |
| `opentelemetry-sdk` | `==1.29.*` | `>=1.36.0,<1.40.0` | 1.36.0 | Low | Capped upper bound |
| `uvicorn` | `==0.32.*` | `>=0.41.0` | 0.41.0 | Low | No breaking changes |
| `python-dotenv` | `==1.0.*` | `>=1.2.0` | 1.2.2 | Low | Minor |

---

*agentize.eu -- AI & Organizational Solutions*
*Implementation Specification v1.3 -- 2026-03-12*
