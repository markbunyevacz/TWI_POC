---
name: agentize-poc-langgraph
description: LangGraph agent implementation guide for the agentize.eu PoC. Covers AgentState, all graph nodes, conditional edges, human-in-the-loop interrupt pattern, revision loop, and graph compilation. Use when implementing or modifying agent nodes, adding new intents, changing the workflow, or debugging graph execution.
---

# LangGraph Agent — agentize.eu PoC

## AgentState (TypedDict)

```python
class AgentState(TypedDict):
    user_id: str
    tenant_id: str
    conversation_id: str
    channel: str          # "msteams" | "telegram"
    message: str

    intent: Optional[str]          # "generate_twi" | "edit_twi" | "question" | "unknown"
    processed_input: Optional[dict]
    draft: Optional[str]
    draft_metadata: Optional[dict] # {model, generated_at, revision}

    revision_feedback: Optional[str]
    revision_count: int

    status: str   # "processing" | "review_needed" | "revision_requested" | "approved" | "completed" | "error"
    pdf_url: Optional[str]
    pdf_blob_name: Optional[str]

    llm_model: Optional[str]
    llm_tokens_input: Optional[int]
    llm_tokens_output: Optional[int]
    approval_timestamp: Optional[str]
    messages: list[Any]
```

## Graph Topology

```
classify_intent
  ├── generate_twi / edit_twi → process_input → generate → review (INTERRUPT)
  ├── question                               → generate → review (INTERRUPT)
  └── unknown                                              → clarify → END

review (INTERRUPT #1)
  ├── approved          → approve (INTERRUPT #2) → output → audit → END
  ├── revision_requested → revise (audit: twi_revised) → generate → review  (max 3 loops)
  └── rejected          → reject → audit (twi_rejected) → END
```

## Graph Compilation

```python
async def create_agent_graph():
    builder = StateGraph(AgentState)
    # Add all 10 nodes (including reject)...
    checkpointer = await _get_checkpointer()  # MongoDB or MemorySaver fallback
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["review", "approve"],
    )
```

`create_agent_graph()` is **async** because `_get_checkpointer()` attempts MongoDB (`MongoDBSaver`) initialization and falls back to `MemorySaver` if Cosmos DB is not configured.

## Running / Resuming the Graph

```python
config = {"configurable": {"thread_id": conversation_id}}

# New conversation
await graph.ainvoke(initial_state, config)

# Resume after INTERRUPT (card action received)
await graph.aupdate_state(config, state_update)
result = await graph.ainvoke(None, config)
```

Resume state updates (built by `_build_resume_state()`):
- After revision request: `{"status": "revision_requested", "revision_feedback": "..."}`
- After final approval: `{"status": "approved", "approval_timestamp": "..."}`
- Unknown `resume_from` value: raises `ValueError`

## Node Implementation Pattern

Every node has this signature and returns full state with updates:

```python
async def node_name(state: AgentState) -> AgentState:
    # ... do work ...
    return {**state, "field": new_value}
```

## Key Nodes

### intent_node (graph name: `classify_intent`)
Classifies user message. Calls LLM with `temperature=0.1, max_tokens=20`.
Returns one of: `generate_twi | edit_twi | question | unknown`.
Falls back to `unknown` if the LLM response is not a valid intent.

### generate_node
- If `revision_feedback` present: includes previous draft + feedback in prompt
- Always prepends: `"⚠️ AI által generált tartalom — emberi felülvizsgálat szükséges."`
- Uses `temperature=0.3, max_tokens=4000`
- Sets `status = "review_needed"`

### review_node (INTERRUPT)
Human-in-the-loop #1. Graph pauses here. Bot sends Review Adaptive Card.
Card submit resumes graph with `status = "approved" | "revision_requested" | "rejected"`.

### revise_node
Increments `revision_count`. Passes feedback back into generate cycle.
Logs an inline `twi_revised` audit event via `AuditStore` (failure does not block the flow).
After 3 revisions, `after_revision()` edge forces move to `approve`.

### approve_node (INTERRUPT)
Human-in-the-loop #2. Graph pauses here. Bot sends Final Approval Adaptive Card.
Card submit resumes with `status = "approved"` + `approval_timestamp`.

### output_node
1. `generate_twi_pdf(content, metadata, user_id)` → bytes
2. `upload_pdf(bytes, blob_name)` → SAS URL (24h)
3. Sets `pdf_url`, `pdf_blob_name`, `status = "completed"`

### reject_node (inline in `graph.py`)
Sets `status = "rejected"` and routes to `audit_node` so rejection events are logged.

### clarify_node (inline in `graph.py`)
Returns `status = "clarification_needed"` for unknown intents. Minimal placeholder — flow ends immediately after.

### audit_node
Derives `event_type` from state status (`completed` → `twi_generated`, `rejected` → `twi_rejected`).
Saves to Cosmos DB `audit_log` collection:
`conversation_id, user_id, tenant_id, channel, event_type, intent, llm_model, llm_tokens_input, llm_tokens_output, revision_count, pdf_blob_name, status, approval_timestamp`.

## AI Foundry LLM Call

```python
# app/services/ai_foundry.py
from azure.ai.inference.aio import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

async def call_llm(
    prompt: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, int, int]:
    """Returns (response_text, prompt_tokens, completion_tokens)."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = await client.complete(
        messages=messages,
        model=settings.ai_model,          # "gpt-4o"
        temperature=temperature or 0.3,
        max_tokens=max_tokens or 4000,
    )
    content = response.choices[0].message.content
    usage = response.usage
    return content, usage.prompt_tokens, usage.completion_tokens
```

## TWI Generation Prompt Structure

System prompt defines output format:
1. CÍM (Title)
2. CÉL (Goal)
3. SZÜKSÉGES ANYAGOK ÉS ESZKÖZÖK (Materials & Tools)
4. BIZTONSÁGI ELŐÍRÁSOK (Safety)
5. LÉPÉSEK (Steps) — each with: main action + key points + rationale
6. MINŐSÉGI ELLENŐRZÉS (Quality check)

Rule: if insufficient info → ask back, never invent details.

## PDF Generation

```python
# app/agent/tools/pdf_generator.py
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

async def generate_twi_pdf(content: str, metadata: dict, user_id: str) -> bytes:
    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("twi_template.html")
    html = template.render(content=content, metadata=metadata, user_id=user_id)
    return HTML(string=html).write_pdf()
```

Template: `app/templates/twi_template.html` (Jinja2) + `app/templates/twi_style.css`.

## Testing

```bash
pytest tests/test_graph.py tests/test_generation.py tests/test_pdf.py
```

Key test scenarios:
- Intent classification for each category
- Draft generation includes EU AI Act label
- Revision loop increments count and incorporates feedback
- PDF bytes non-empty and valid PDF header
- Audit event_type derived correctly for completed / rejected states
- Split token counts (llm_tokens_input, llm_tokens_output) written to audit log
- Revision audit inline log fires twi_revised event
- Audit failure does not block the user flow
