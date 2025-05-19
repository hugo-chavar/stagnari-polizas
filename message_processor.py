import logging
from policy_data import load_csv_data, apply_filter
from ai_agents import generate_query, generate_response

logger = logging.getLogger(__name__)

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
    filter = generate_query(incoming_message, to_number)
    # Check if model understood the message
    if "?" in filter:
        # If the model didn't understand the message, return the follow up message
        return filter["?"]
    filtered_data = ""
    incoming_message = filter.get("r") or incoming_message
    negative_response = filter.get("n") or "Lo siento, no tengo información sobre eso."
    if "qs" in filter and "c" in filter:
        try:
            rows_filter = filter["qs"]
            columns_filter = filter["c"]
            if "p" in filter and filter["p"]:
                columns_filter = None
            filtered_data = apply_filter(rows_filter, columns_filter)
        except Exception as e:
            logger.error(f"Error applying filter: {e}")
            return f"Error: Hubo un error al procesar tu consulta. Por favor intenta de nuevo."

    response = generate_response(incoming_message, filtered_data, to_number, negative_response)
    logger.info(f"Final response:\n{response}")
    return response
