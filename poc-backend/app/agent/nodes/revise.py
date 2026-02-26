from app.agent.state import AgentState


async def revise_node(state: AgentState) -> AgentState:
    """Increment the revision counter and carry user feedback into the next generate cycle."""
    revision_count = state.get("revision_count", 0) + 1
    return {
        **state,
        "revision_count": revision_count,
        "status": "revision_requested",
    }
