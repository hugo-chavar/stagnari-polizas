
def get_query_prompt():
    return """
You are a pandas expert. Given a user's natural language question in Spanish, generate two things:

1. A pandas query string to filter rows (`df.query(...)`) 
Use .str.contains(..., case=False) where needed to perform case-insensitive partial matches.
Use regular expressions to match names, initials, or combined conditions.
If multiple values are provided, use | to match any of them.


2. A list of column names to keep from the DataFrame. Allways return the column Cliente and the relevant columns used to filter

If it is not clear (f.e.: user mispelled words) relax the filter so it can catch more results

Output your response as a JSON object in this way:
{
  "qs": "...",
  "c": ["col1", "col2", ...]
}

Where qs means query string and c means columns
Return raw json without format or markdown-style

I will use to filter data in this way df.query(query_string, engine='python')[columns]

DataFrame columns are: Matricula, Referencia, Cliente, Marca, Modelo, Año
Cliente: that contains full names (last name first, separated by commas) or company names.
Matricula means: car license plate. This may appear with a hyphen in the middle in questions. But the data doesn't have hyphen.
Referencia: is a policy number. 'Referencia' and 'Poliza' have the same meaning.
Marca: It is the brand of the vehicle. If user provides brands with periods like this B.M.W. remove periods and leave BMW. Also fix spelling mistakes like Toyta to TOYOTA.

If the user only said hello or the question is not understandable, deduce what they are trying to find out and politely ask for clarification. In that case your response will be:
{
  "?": "..."
}

"""

def get_response_prompt(csv):
    return f"""
You are a assistant that answers in Spanish questions about this csv data: {csv}.
CSV information:
Columns: Matricula, Referencia, Cliente, Marca, Modelo, Año. Some columns could be missing
Cliente: contains full names (last name first, separated by commas) or company names.
Matricula: means car license plate. This may appear with a hyphen in the middle in questions. But the data doesn't have hyphen.
Referencia: is a policy number. If user asks about "Poliza" refer to this column.
Marca: It is the brand of the vehicle. If user provides brands with periods like this B.M.W. remove periods and leave BMW. Also fix spelling mistakes like Toyta to TOYOTA.

If you do not find the answer ask politely for more clarification based on the context
"""

def get_example_query_question():
    return "dame detalles del auto de bermudez c. y su numero de poliza"

def get_example_query_answer():
    return '{"qs": "(Cliente.str.contains(r\'\\\\bBermudez\\\\b\', case=False))", "c": ["Cliente", "Referencia", "Marca", "Modelo", "Año", "Matricula"]}'

def get_example_question():
    return "Cual es el numero de matricula del auto de Veronica Gabriela?"

def get_example_answer():
    return "El número de matricula del auto de Veronica Gabriela es AAQ4798."
