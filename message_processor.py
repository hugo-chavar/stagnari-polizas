from policy_data import load_csv_data, apply_filter
from ai_agents import generate_query, generate_response

def generate_response(incoming_message: str) -> str:
    """
    Processes incoming WhatsApp message and returns appropriate response.
    
    Args:
        incoming_message: The received message
        
    Returns:
        str: The response to send back
    """
    
    incoming_message = incoming_message.lower()
    load_csv_data()
    query = generate_query(incoming_message)
    filtered_data = apply_filter(query)
    return generate_response(filtered_data)
