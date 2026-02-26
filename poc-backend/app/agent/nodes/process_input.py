from app.agent.state import AgentState


async def process_input_node(state: AgentState) -> AgentState:
    """Structure and validate the user's TWI generation request.

    For PoC this is lightweight — future extensions could extract machine name,
    process type, safety requirements etc. via a dedicated LLM call.
    """
    processed = {
        "original_message": state["message"],
        "intent": state.get("intent"),
        "channel": state.get("channel"),
    }
    return {**state, "processed_input": processed}
