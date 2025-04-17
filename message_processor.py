from policy_data import load_csv_data, apply_filter
from ai_agents import generate_query, generate_response

def get_response_to_message(incoming_message: str, to_number: str) -> str:
    """
    Processes incoming WhatsApp message and returns appropriate response.
    
    Args:
        incoming_message: The received message
        
    Returns:
        str: The response to send back
    """
    
    incoming_message = incoming_message.lower()
    load_csv_data()
    filter = generate_query(incoming_message)
    # Check if model understood the message
    if "?" in filter:
        # If the model didn't understand the message, return the follow up message
        return filter["?"]
    filtered_data = ""
    if "qs" in filter and "c" in filter:
        filtered_data = apply_filter(filter["qs"], filter["c"])
    return generate_response(incoming_message, filtered_data, to_number)
