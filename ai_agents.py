import json
import logging
import os
from dotenv import load_dotenv
from openai import OpenAI
import prompts
from chat_history_db import save_message, get_client_history, save_query, get_query_history
from files_finder import find_files

load_dotenv()

API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")
API_URL = os.getenv("API_URL")

client = OpenAI(api_key=API_KEY, base_url=API_URL)

logger = logging.getLogger(__name__)

def clean_llm_json(raw_response: str) -> str:
    """Remove markdown-style triple backticks from LLM JSON output."""
    # logger.info(f"Raw response from LLM:\n{raw_response}")
    lines = raw_response.strip().splitlines()
    # Remove lines that start or end code blocks
    lines = [line for line in lines if not line.strip().startswith("```")]
    clean_llm_json = "\n".join(lines)
    # logger.info(f"Cleaned LLM JSON:\n{clean_llm_json}")
    return clean_llm_json


def _prepare_query_messages(question, client_number):
    """Prepare the messages for the API call."""
    history = get_query_history(client_number, days_limit=2)
    prompt = prompts.get_query_prompt()
    messages = [
        {"role": "system", "content": prompt}
    ]
    # Use the history messages, excluding the current question if already saved
    for role, content in history:
        messages.append({"role": role, "content": content})
    
    responses_history = get_client_history(client_number, days_limit=1)
    if responses_history:
        response_model_last_response = responses_history[-1][1]
        response_model_last_response = response_model_last_response.replace("*", "")
        messages.extend([
            {"role": "assistant", "content": (
                "CONTEXT FOR FOLLOW-UP:\n"
                "The user was recently shown these results:\n"
                f"{response_model_last_response}\n\n"
                "For references like 'el primero' or '#2', modify our previous query "
                "to select that specific item from these results."
            )},
        ])
    messages.append({"role": "user", "content": question})
    
    return messages


def generate_query(question, client_number):
    
    messages = _prepare_query_messages(question, client_number)
    save_query(client_number, "user", question)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=400
    )
    model_response = response.choices[0].message.content
    logger.info(f"Question:\n{question}")
    logger.info(f"Query:\n{model_response}")
    save_query(client_number, "assistant", model_response)
    return json.loads(clean_llm_json(model_response))


def _prepare_messages(question, csv, client_number):
    """Prepare the messages for the API call."""
    # Get the conversation history from the last 2 days
    history = get_client_history(client_number, days_limit=2)
    
    # Prepare the messages for the API call
    prompt = prompts.get_response_prompt()
    messages = [{"role": "system", "content": prompt}]
    
    # Add all previous messages to the context
    for role, content in history[:-1]:  # exclude the current question which is already in history
        messages.append({"role": role, "content": content})
    
    has_rows = csv is not None and len(csv) > 0
    messages.append({"role": "system", "content": f"CSV data: {csv}" if has_rows else "CSV data: EMPTY"})
    # Add the current question (in case it wasn't saved yet)
    messages.append({"role": "user", "content": question})
    
    return messages


def generate_response(question, csv, client_number, negative_response):
    line_count = csv.count('\n') - 1
    has_rows  = line_count > 0
    if has_rows:
        csv = csv.replace("\n", " ").replace(",", ",\n")
        # Save the new question to the database
        save_message(client_number, "user", question)
        
        messages = _prepare_messages(question, csv, client_number)
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=False
        )

        model_response = response.choices[0].message.content
        # Clean the response to remove any unwanted formatting
        model_response = model_response.replace("**", "*").strip()
        
        # Save the assistant's response to the database
        save_message(client_number, "assistant", model_response)
        
        return model_response
    else:
        logger.info("No data found for the query.")
        return negative_response


def _prepare_get_parsed_list_messages(text):
    """Prepare the messages for the API call."""
    prompt = prompts.get_parse_list_prompt()
    messages = [
        {"role": "system", "content": prompt},
        {"role": "system", "content": (
                "### Task:\n"
                "Process the following input text: \n"
                "``` \n"
                f"{text}"
                "``` \n"
            )},
    ]
    
    return messages


def get_parsed_list(text_list):

    messages = _prepare_get_parsed_list_messages(text_list)
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=False
    )
    model_response = response.choices[0].message.content
    logger.info(f"Get Files input:\n{text_list}")
    logger.info(f"List:\n{model_response}")
    return json.loads(clean_llm_json(model_response))


def add_file_paths(parsed_list):

    for company, policies in parsed_list.items():
        for p in policies:
            for v in p["vehicles"]:
                ok, msg, soa_path, mer_path = find_files(
                    company=company,
                    policy_number=p["policy_number"],
                    license_plate=v.get("license_plate",None),
                    user_wants_mercosur_file=p["download_mer"]
                )
                v["ok"] = ok
                v["error_msg"] = msg
                v["soa_path"] = soa_path
                v["mer_path"] = mer_path
    return parsed_list


def get_file_list(parsed_list):
    file_list = []
    ok_count = error_count = 0 
    error_msg = None
    
    policy_list = add_file_paths(parsed_list)
    download_soa = parsed_list.get("download_soa", True)
    download_mer = parsed_list.get("download_mer", False)
    
    for _, policies in policy_list.items():
        for p in policies:
            for v in p["vehicles"]:
                if v["ok"]:
                    ok_count += 1
                    details = f"Poliza {p["policy_number"]} matricula {v["license_plate"]}"
                    if download_soa and v["soa_path"]:
                        file_list.append({
                            "path": v["soa_path"],
                            "name": f"Certificado SOA de {details}"
                        })
                    if download_mer and v["mer_path"]:
                        file_list.append({
                            "path": v["mer_path"],
                            "name": f"Certificado Mercosur de {details}"
                        })
                else:
                    error_count += 1
                    if not error_msg:
                        error_msg = v["error_msg"]
                    else:
                        error_msg = f"{error_msg}\n\n{v["error_msg"]}"
                
    return file_list, ok_count, error_count, error_msg
