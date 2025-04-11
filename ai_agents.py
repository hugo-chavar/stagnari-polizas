import json
import os
from openai import OpenAI
from prompts import get_query_prompt, get_response_prompt

client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")

def clean_llm_json(raw_response: str) -> str:
    """Remove markdown-style triple backticks from LLM JSON output."""
    lines = raw_response.strip().splitlines()
    # Remove lines that start or end code blocks
    lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(lines)


def generate_query(question):
    
    prompt = get_query_prompt()
    # TODO: replace accents
    example_question = "dame detalles del auto de bermudez c. y su numero de poliza"
    example_response = '{"qs": "(Cliente.str.contains(r\'\\\\bBermudez\\\\b\', case=False))", "c": ["Cliente", "Referencia", "Marca", "Modelo", "Año", "Matricula"]}'
    # question2 = "Quiero obtener vehiculos que son modelo 2016 o superior y que son marca ford"
    
    response = client.chat.completions.create(
        model="gemma3",
        messages=[
            {"role": "user", "content": prompt},
            {"role": "user", "content": example_question},
            {"role": "assistant", "content": example_response},
            {"role": "user", "content": question}
        ],
        max_tokens=200
    )

    return json.loads(clean_llm_json(response.choices[0].message.content))

def get_response(question, csv):
    prompt = get_response_prompt(csv)
    response = client.chat.completions.create(
        model="gemma3", #"deepseek-r1:1.5b",
        messages=[
            {"role": "system", "content": prompt}, #. Provide in the answer a json string with the entire rows you consider for this answer
            {"role": "user", "content": "Cual es el numero de matricula del auto de Veronica Gabriela?"},
            {"role": "assistant", "content": "El número de matricula del auto de Veronica Gabriela es AAQ4798."},
            {"role": "user", "content": question},
        ],
        stream=False
    )

    return response.choices[0].message.content