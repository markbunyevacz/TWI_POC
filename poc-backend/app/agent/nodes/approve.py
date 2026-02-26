from app.agent.state import AgentState


async def approve_node(state: AgentState) -> AgentState:
    """Human-in-the-loop checkpoint #2 — the graph is interrupted here.

    The bot sends a Final Approval Adaptive Card.
    The graph resumes with status="approved" + approval_timestamp when the
    user clicks "Ellenőriztem és jóváhagyom".
    """
    return {**state, "status": "approved"}
