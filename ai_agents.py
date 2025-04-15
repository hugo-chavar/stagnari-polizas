import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import prompts

load_dotenv()

API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")
API_URL = os.getenv("API_URL")

client = OpenAI(api_key=API_KEY, base_url=API_URL)

def clean_llm_json(raw_response: str) -> str:
    """Remove markdown-style triple backticks from LLM JSON output."""
    lines = raw_response.strip().splitlines()
    # Remove lines that start or end code blocks
    lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(lines)


def generate_query(question):
    
    prompt = prompts.get_query_prompt()
    # TODO: replace accents
    example_question = prompts.get_example_query_question()
    example_response = prompts.get_example_query_answer()
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "user", "content": example_question},
            {"role": "assistant", "content": example_response},
            {"role": "user", "content": question}
        ],
        max_tokens=200
    )
    model_response = response.choices[0].message.content
    print(f"Question:\n{question}")
    print(f"Query:\n{model_response}")
    return json.loads(clean_llm_json(model_response))

def generate_response(question, csv):
    prompt = prompts.get_response_prompt(csv)
    example_question = prompts.get_example_question()
    example_answer = prompts.get_example_answer()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": example_question},
            {"role": "assistant", "content": example_answer},
            {"role": "user", "content": question},
        ],
        stream=False
    )

    model_response = response.choices[0].message.content
    print(f"Final response:\n{model_response}")    
    return model_response
