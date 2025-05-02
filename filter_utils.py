import re
import logging

logger = logging.getLogger(__name__)


def extract_names_from_query(query_string):
    # This pattern matches only Cliente.contains('...')
    pattern = r"Cliente\.fillna\(''\)\.str\.contains\('([^']*)'"
    names = re.findall(pattern, query_string)
    return names

def replace_names_in_query(query_string, new_names):
    # Split the query string while preserving Cliente.contains() structure
    parts = re.split(r"(Cliente\.fillna\(''\)\.str\.contains\('[^']*')", query_string)
    
    # Find all the indices where Cliente.contains() appears
    contains_indices = [i for i, part in enumerate(parts) 
                       if part.startswith("Cliente.fillna('').str.contains('")]
    
    # Verify the number of names matches
    if len(contains_indices) != len(new_names):
        raise ValueError(f"Number of names to replace ({len(contains_indices)}) doesn't match new names provided ({len(new_names)})")
    
    # Replace each Cliente.contains() with the new name
    for idx, name in zip(contains_indices, new_names):
        parts[idx] = f"Cliente.fillna('').str.contains('{name}'"
    
    # Rebuild the query string
    return ''.join(parts)

def make_fuzzy_regex(name):
    # Define character substitutions for common mistakes
    substitutions = {
        'a': '[aeo]',
        'á': '[aeo]',
        'e': '[aeo]',
        'é': '[aeo]',
        'i': '[iyl1]',
        'í': '[iyl1]',
        '1': '[il]',
        'o': '[aeo0]',
        'ó': '[aeo0]',
        'x': '[xks]',
        '0': '[0o]',
        'u': '[uw]',
        'ú': '[uw]',
        'w': '[uw]',
        'c': '[ckq]',
        'n': '[mnñ]',
        'm': '[mnñ]',
        'l': '[li]',
        't': '[td]',
        'ñ': '[mnñ]',
        's': '[szx]',
        'z': '[zs]',
        'y': '[yi]',
        'j': '[jg]',
        'g': '[gj]',
        'b': '[bv]',
        'v': '[vb]',
        'k': '[kcq]',
        'q': '[qkc]',
        '’': '.?',
        "'": '.?',
        ' ': '.*',  # Allow any characters in between
    }
    
    fuzzy_chars = []
    for char in name.lower():
        # Apply substitutions if defined, otherwise keep the original
        if char not in ['.', ' ', '*', '?']:
            new_char = substitutions.get(char, char)
            fuzzy_chars.append(f"{new_char}.?")  # Add optional character after each letter
        else:
            fuzzy_chars.append(char)    
    # Join with regex pattern and handle possible missing letters
    fuzzy_pattern = ''.join(fuzzy_chars)
    
    # Make beginning/end more flexible
    fuzzy_pattern = f"{fuzzy_pattern[:-2]}"  # Remove last .? to prevent too much fuzziness
    fuzzy_pattern = fuzzy_pattern.replace('.?.*', '.*')
    
    return fuzzy_pattern

def make_fuzzy(names):
    return [make_fuzzy_regex(name) for name in names]


def relax_filter(query_string):
    logger.info(f"Original query: {query_string}" )

    names = extract_names_from_query(query_string)
    logger.info(f"Extracted names: {names}")

    new_names = make_fuzzy(names)
    new_query = replace_names_in_query(query_string, new_names)
    new_query = new_query.replace("true", "True")
    new_query = new_query.replace("false", "False")
    logger.info(f"Updated query: {new_query}")
    return new_query
