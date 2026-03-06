from app.agent.state import AgentState
import re


# Common patterns for TWI requests
MACHINE_PATTERN = re.compile(r"(?:gep|machine|cnc)\s*([A-Z0-9\-]+)", re.IGNORECASE)
PROCESS_TYPE_PATTERN = re.compile(r"(?:karbantartas|maintenance|beallitas|setup|ellenorzes|check|javitas|repair|mukodtetes|operation)\b", re.IGNORECASE)


async def process_input_node(state: AgentState) -> AgentState:
    """Structure and validate the user's TWI generation request.

    Extracts structured fields from the user's message for better context.
    Future extensions could use a dedicated LLM call for more complex extraction.
    """
    message = state.get("message", "")
    
    # Extract machine identifier if present
    machine_match = MACHINE_PATTERN.search(message)
    machine_id = machine_match.group(1) if machine_match else None
    
    # Extract process type keywords
    process_types = PROCESS_TYPE_PATTERN.findall(message)
    
    processed = {
        "original_message": message,
        "intent": state.get("intent"),
        "channel": state.get("channel"),
        "extracted_machine_id": machine_id,
        "process_types": process_types if process_types else None,
    }
    return {**state, "processed_input": processed}
