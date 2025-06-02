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
    filter_values = {}
    if "cl" in filter:
        filter_values['Cliente'] = filter.get("cl")
    if "lp" in filter:
        filter_values['Matricula'] = filter.get("lp")
    if "qs" in filter and "c" in filter:
        try:
            rows_filter, columns_filter = get_filters(filter)
            filtered_data = apply_filter(rows_filter, columns_filter, filter_values)
        except Exception as e:
            logger.error(f"Error applying filter: {e}")
            raise ValueError(f"Error: Hubo un error al procesar tu consulta. Por favor intenta de nuevo.")

    response = generate_response(incoming_message, filtered_data, to_number, negative_response)
    logger.info(f"Final response:\n{response}")
    return response

def get_filters(filter):
    rows_filter = filter["qs"]
    if not rows_filter.strip():
        raise ValueError("Error: Demasiados registros encontrados. Provea una consulta mas especifica.")
    rows_filter = rows_filter.replace("true", "True")
    rows_filter = rows_filter.replace("false", "False")
    columns_filter = filter["c"]
    if "p" in filter and filter["p"]:
        columns_filter = None
    if columns_filter:
        try:
                    # Fix old error
            i = columns_filter.index("Referencia")
            columns_filter[i] = "Poliza"
        except ValueError:
            pass
    return rows_filter,columns_filter
