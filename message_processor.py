import logging
from policy_data import load_csv_data, apply_filter
from ai_agents import generate_query, generate_response, get_file_list, get_parsed_list
from filter_utils import remove_spanish_accents

logger = logging.getLogger(__name__)


def get_response_to_message(incoming_message: str, to_number: str):
    """
    Processes incoming WhatsApp message and returns appropriate response.

    Args:
        incoming_message: The received message

    Returns:
        str: The response to send back
    """

    incoming_message = remove_spanish_accents(incoming_message.lower()).strip()
    common_phrases = {
        "": "Hola! ¿En qué puedo ayudarte?",
        "hola": "Hola! ¿En qué puedo ayudarte?",
        "buenas": "Hola! ¿En qué puedo ayudarte?",
        "buenos dias": "Buenas! ¿En qué puedo ayudarte?",
        "buenas tardes": "Buenas! ¿En qué puedo ayudarte?",
        "buenas noches": "Buenas! ¿En qué puedo ayudarte?",
        "gracias": "De nada!",
        "adios": "Hasta luego!",
        "hasta luego": "Dale! Que tengas un buen día.",
        "muchas gracias": "De nada!.",
        "perfecto": "Ok!",
        "ok": "¡Entendido! ¿Te puedo ayudar en algo más?",
        "gracias por tu ayuda": "De nada",
        "genial": "Ok!",
        "muy bien": "Me alegro!",
        "todo bien": "Perfecto!",
        "todo correcto": "Perfecto!",
        "todo en orden": "Genial!",
        "todo claro": "Buenisimo!",
        "gracias por la informacion": "Estoy para servir!",
        "gracias por tu respuesta": "De nada che!",
    }

    if incoming_message in common_phrases:
        response = common_phrases[incoming_message]
        logger.info(f"Common phrase response: {response}")
        return response, None
    
    if len(incoming_message) < 3:
        return "Disculpa! No entendí. ¿En qué puedo ayudarte?", None

    load_csv_data()
    filter = generate_query(incoming_message, to_number)
    return process_incoming_message(filter, incoming_message, to_number)


def process_incoming_message(filter, incoming_message, to_number):
    # Check if model understood the message
    if "?" in filter:
        # If the model didn't understand the message, return the follow up message
        return filter["?"], None
    incoming_message, filtered_data, negative_response = get_filtered_data(
        filter, incoming_message
    )

    response = generate_response(
        incoming_message, filtered_data, to_number, negative_response
    )
    
    file_list = None
    if filter.get("soa", False) or filter.get("mer", False):
        parsed_list = get_parsed_list(response)
        file_list, tot_count, ok_count, error_count, error_msg = get_file_list(parsed_list)
        logger.info(f"FileList: {file_list}")
        if error_count > 0:
            if tot_count > 1:
                adj = ["Algunos", "no se"] if ok_count > 0 else ["Ninguno", "se"]
                title = f"{adj[0]} de los PDF solicitados {adj[1]} pueden descargar"
            else:
                title = "Hay documentos que no se puede descargar"
            response = (
                f"{response}\n\n"
                f"*{title}:*\n"
                f"{error_msg}"
            )
        if ok_count > 0:
            response = (
                f"{response}"
                f"{f'\n\n*Comienza la descarga de certificados de {ok_count} vehiculos ...*'}"
            )
    
    logger.info(f"Final response:\n{response}")
    return response, file_list


def get_filtered_data(filter, incoming_message):
    filtered_data = ""
    incoming_message = filter.get("r") or incoming_message
    negative_response = filter.get("n") or "Lo siento, no tengo información sobre eso."
    if "qs" in filter and "c" in filter:
        try:
            rows_filter, columns_filter, filter_values = get_filters(filter)
            filtered_data = apply_filter(rows_filter, columns_filter, filter_values)
        except Exception as e:
            logger.error(f"Error applying filter: {e}")
            raise ValueError(
                f"Error: Hubo un error al procesar tu consulta. Por favor intenta de nuevo."
            )
    return incoming_message, filtered_data, negative_response


def get_filters(filter):
    rows_filter = filter["qs"]
    if not rows_filter.strip():
        raise ValueError(
            "Error: Demasiados registros encontrados. Provea una consulta mas especifica."
        )
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
    filter_values = {}
    if "cl" in filter:
        filter_values["Cliente"] = filter.get("cl")
    if "lp" in filter:
        filter_values["Matricula"] = filter.get("lp")
    return rows_filter, columns_filter, filter_values
