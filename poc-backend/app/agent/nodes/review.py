from app.agent.state import AgentState


async def review_node(state: AgentState) -> AgentState:
    """Human-in-the-loop checkpoint #1 — the graph is interrupted here.

    The bot sends a Review Adaptive Card to the user.
    The graph resumes when the user submits the card action
    (approve_draft / request_edit / reject).
    """
    # Node body is intentionally minimal — the actual logic runs in the bot handler
    # after the graph is resumed.  We just make the status explicit.
    return {**state, "status": "review_needed"}
