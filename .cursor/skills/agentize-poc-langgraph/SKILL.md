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
    llm_tokens_used: Optional[int]
    approval_timestamp: Optional[str]
    messages: List[Any]
```

## Graph Topology

```
intent
  ├── generate_twi / edit_twi → process_input → generate → review (INTERRUPT)
  ├── question                               → generate → review (INTERRUPT)
  └── unknown                                              → clarify → END

review (INTERRUPT #1)
  ├── approved          → approve (INTERRUPT #2) → output → audit → END
  ├── revision_requested → revise → generate → review  (max 3 loops)
  └── rejected                                           → END
```

## Graph Compilation

```python
builder = StateGraph(AgentState)
# Add all nodes...
builder.compile(
    checkpointer=MemorySaver(),           # PoC: in-memory; Prod: Cosmos DB checkpointer
    interrupt_before=["review", "approve"],  # Human-in-the-loop breakpoints
)
```

**PoC uses `MemorySaver`** — for production, replace with a Cosmos DB checkpointer.

## Running / Resuming the Graph

```python
config = {"configurable": {"thread_id": conversation_id}}

# New conversation
await graph.ainvoke(initial_state, config)

# Resume after INTERRUPT (card action received)
await graph.ainvoke(resume_state_update, config)
```

Resume state updates:
- After review approve: `{"status": "approved"}`
- After revision request: `{"status": "revision_requested", "revision_feedback": "..."}`
- After final approval: `{"status": "approved", "approval_timestamp": "..."}`

## Node Implementation Pattern

Every node has this signature and returns full state with updates:

```python
async def node_name(state: AgentState) -> AgentState:
    # ... do work ...
    return {**state, "field": new_value}
```

## Key Nodes

### intent_node
Classifies user message. Calls LLM with `temperature=0.1, max_tokens=20`.
Returns one of: `generate_twi | edit_twi | question | unknown`.

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
After 3 revisions, `after_revision()` edge forces move to `approve`.

### approve_node (INTERRUPT)
Human-in-the-loop #2. Graph pauses here. Bot sends Final Approval Adaptive Card.
Card submit resumes with `status = "approved"` + `approval_timestamp`.

### output_node
1. `generate_twi_pdf(content, metadata, user_id)` → bytes
2. `upload_pdf(bytes, blob_name)` → SAS URL (24h)
3. Sets `pdf_url`, `pdf_blob_name`, `status = "completed"`

### audit_node
Saves to Cosmos DB `audit_log` collection:
`conversation_id, user_id, tenant_id, channel, intent, llm_model, revision_count, pdf_blob_name, status, approval_timestamp`.

## AI Foundry LLM Call

```python
# app/services/ai_foundry.py
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

async def call_llm(prompt, system_prompt=None, temperature=None, max_tokens=None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.complete(
        messages=messages,
        model=settings.ai_model,          # "mistral-large-latest"
        temperature=temperature or 0.3,
        max_tokens=max_tokens or 4000,
    )
    return response.choices[0].message.content
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
