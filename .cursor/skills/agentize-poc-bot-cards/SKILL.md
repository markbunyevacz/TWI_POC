---
name: agentize-poc-bot-cards
description: Bot Framework and Adaptive Cards guide for the agentize.eu PoC. Covers AgentizeBotHandler message routing, card action handling, graph resume patterns, all four Adaptive Card templates (Review, Approval, Result, Welcome), Cosmos DB schema, and Teams App Manifest. Use when implementing bot message handling, creating or modifying Adaptive Cards, registering channels, or debugging Teams/Telegram interactions.
---

# Bot Framework + Adaptive Cards — agentize.eu PoC

## Bot Handler Message Routing

`AgentizeBotHandler` in `app/bot/bot_handler.py` extends `ActivityHandler`.

Two entry paths in `on_message_activity`:

| Condition | Handler | Description |
|-----------|---------|-------------|
| `activity.value` present | `_handle_card_action()` | Adaptive Card submit action |
| plain text | `_handle_text_message()` | New user message → LangGraph |

## Text Message Flow

```python
async def _handle_text_message(self, turn_context, text, conversation_id, user_id, channel_id):
    await turn_context.send_activity("⏳ Feldolgozom a kérésedet...")
    result = await run_agent(graph=self.graph, message=text, user_id=user_id,
                             conversation_id=conversation_id, channel=channel_id)

    if result["status"] == "review_needed":
        card = create_review_card(draft=result["draft"], metadata=result["metadata"])
        await turn_context.send_activity(Activity(type=ActivityTypes.message,
                                                  attachments=[CardFactory.adaptive_card(card)]))
    elif result["status"] == "clarification_needed":
        await turn_context.send_activity(result["message"])
    elif result["status"] == "error":
        await turn_context.send_activity(f"❌ Hiba: {result['message']}")
```

## Card Action Routing

`activity.value["action"]` determines the branch:

| Action value | Bot response | Graph resume | `as_node` |
|---|---|---|---|
| `approve_draft` | Send `create_approval_card()` | No graph resume yet | — |
| `request_edit` | Send thinking, then `create_review_card()` | `resume_from="revision"` | `"review"` (always) |
| `final_approve` | Send thinking, then `create_result_card()` | `resume_from="output"` | `"approve"` |
| `reject` | Send rejection message | `resume_from="rejection"` | `"review"` |

**CRITICAL:** Every resume call passes `as_node` so LangGraph evaluates the outgoing edge directly instead of re-running the interrupted node.

## Adaptive Card Templates

All cards: `$schema: http://adaptivecards.io/schemas/adaptive-card.json`, `version: "1.4"`.

### create_review_card — Human-in-the-loop #1

Body: Title block + AI label (model/timestamp) + draft text (max 2000 chars) + `Input.Text` for feedback.

Actions:
- `✅ Jóváhagyom a vázlatot` → `{"action": "approve_draft", "draft": ..., "metadata": ...}`
- `✏️ Szerkesztés kérem` → `{"action": "request_edit", "draft": ..., "metadata": ..., "feedback": <Input.Text value>}`
- `🗑️ Elvetés` (destructive) → `{"action": "reject"}`

### create_approval_card — Human-in-the-loop #2

Warning header (color: attention) + EU AI Act warning text + full draft.

Actions:
- `✅ Ellenőriztem és jóváhagyom` (positive) → `{"action": "final_approve", "draft": ..., "metadata": ..., "timestamp": "__CURRENT_TIMESTAMP__"}`
- `↩️ Vissza a szerkesztéshez` → `{"action": "request_edit", ...}`

### create_result_card — Download link

FactSet: title, format (PDF), model, approver.

Actions:
- `📥 PDF letöltés` (`Action.OpenUrl`) → SAS URL (24h expiry)

### create_welcome_card — New member

Shown on `on_members_added_activity`. Explains bot purpose + example prompt.

## Sending Adaptive Cards

```python
from botbuilder.core import CardFactory
from botbuilder.schema import Activity, ActivityTypes

await turn_context.send_activity(
    Activity(type=ActivityTypes.message,
             attachments=[CardFactory.adaptive_card(card_dict)])
)
```

## Cosmos DB Collections

| Collection | Purpose | Key Indexes |
|------------|---------|-------------|
| `conversations` | Bot conversation state | `{conversation_id:1}` unique; TTL 90 days |
| `agent_state` | LangGraph checkpoints (auto-managed) | `{thread_id:1, checkpoint_ns:1, checkpoint_id:-1}` unique |
| `agent_state_writes` | LangGraph pending writes (auto-managed) | `{thread_id:1, checkpoint_ns:1, checkpoint_id:1, task_id:1, idx:1}` unique |
| `generated_documents` | Approved TWI docs + PDF links | `{tenant_id:1, created_at:-1}` |
| `audit_log` | Full audit trail per event | `{tenant_id:1, created_at:-1}`, `{event_type:1}` |

`agent_state` and `agent_state_writes` are managed automatically by the `MongoDBSaver` checkpointer — do not write to them manually.

## Teams App Manifest (sideload)

File: `teams-app/manifest.json`

Key fields:
- `"id": "{{BOT_APP_ID}}"` — replace with actual Entra ID App Registration client ID
- `"validDomains": ["{{BACKEND_FQDN}}"]` — Container App FQDN
- Bot scopes: `["personal", "team", "groupChat"]`
- Commands: `Új TWI` (new instruction), `Segítség` (help)

Sideload via Teams Admin Center or `Upload an app` in Teams.

## Channel Registration

Teams channel: `Microsoft.BotService/botServices/channels` resource `MsTeamsChannel`.
Telegram: conditional on `telegramBotToken != ''` — single config toggle.

Bot messaging endpoint must be HTTPS: `https://<container-app-fqdn>/api/messages`.

## Error Handling

Bot adapter global error handler:
```python
async def on_error(context, error):
    logger.error(f"Bot error: {error}", exc_info=True)
    await context.send_activity("Hiba történt. Kérlek próbáld újra.")
adapter.on_turn_error = on_error
```

Individual node errors should set `state["status"] = "error"` with `state["message"]` — the bot handler maps this to a user-facing error message.

## PDF Template Notes

`app/templates/twi_template.html` (Jinja2) generates A4 PDF via WeasyPrint.
- Page footer: `"agentize.eu — AI által generált tartalom — {page}/{pages}"`
- AI warning box: amber left-border callout
- Approval box: green border, shows `approved_at` + `approved_by`
- Required system packages in Dockerfile: `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi-dev libgdk-pixbuf2.0-0`
