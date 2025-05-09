import re
import logging

logger = logging.getLogger(__name__)

def remove_spanish_accents(text):
    accents_mapping = {
        'á': 'a',
        'é': 'e',
        'í': 'i',
        'ó': 'o',
        'ú': 'u',
        'ü': 'u',
    }
    for accented, unaccented in accents_mapping.items():
        text = text.replace(accented, unaccented)
    return text

def clean_pattern_string(input_string):
    """
    Replaces non-alphanumeric characters (except '.', '|', '&', '*', '?') with '.*'
    and then consolidates consecutive '.*' patterns.
    
    Args:
        input_string (str): The string to be processed
        
    Returns:
        str: The processed string with special characters replaced and patterns cleaned
    """
    # Replace non-alphanumeric characters (except allowed ones) with '.*'
    pattern = r"[^\w\.\|\&\*\?]"
    processed = re.sub(pattern, '.*', input_string)
    
    # Clean consecutive '.*' patterns
    processed = re.sub(r'(\.\*)+', '.*', processed)
    
    return processed

def clean_string(input_string):
    result = remove_spanish_accents(input_string)
    result = clean_pattern_string(result)
    return result

def clean_fuzzy_pattern(fuzzy_pattern):
    """
    Cleans a fuzzy pattern by consolidating consecutive wildcards.
    Replaces combinations of .?, .*, etc. with their most efficient form.
    """
    # Combine all replacements into a single regex substitution
    return re.sub(
        r'(\.\??\*?|\*\.?\*?|\?\.?\*?)+', 
        lambda m: '.*' if '*' in m.group(0) else '.?', 
        fuzzy_pattern
    )

def extract_strings_from_query(query_string, column_name):
    # Pattern matches: column_name.fillna('').str.contains('...')
    pattern = rf"{column_name}\.fillna\(''\)\.str\.contains\('([^']*)'"
    names = re.findall(pattern, query_string)
    return [clean_string(name) for name in names]

def replace_words_in_query(query_string, column_name, new_words):
    # Split the query string while preserving column.contains() structure
    pattern = rf"({re.escape(column_name)}\.fillna\(''\)\.str\.contains\('[^']*')"
    parts = re.split(pattern, query_string)
    
    # Find all indices where column.contains() appears
    contains_indices = [
        i for i, part in enumerate(parts) 
        if part.startswith(f"{column_name}.fillna('').str.contains('")
    ]
    
    # Verify the number of words matches
    if len(contains_indices) != len(new_words):
        raise ValueError(
            f"Expected {len(contains_indices)} words to replace, but got {len(new_words)}"
        )
    
    # Replace each occurrence with the new word
    for idx, word in zip(contains_indices, new_words):
        parts[idx] = f"{column_name}.fillna('').str.contains('{word}'"
    
    # Rebuild the query string
    new_query_string = ''.join(parts).replace("regex=False", "regex=True")
    
    return new_query_string

def make_string_fuzzy_regex(name):
    # Define character substitutions for common mistakes
    substitutions = {
        'a': '[aeo]',
        'e': '[aeo]',
        'i': '[iyl1]',
        '1': '[il]',
        'o': '[aeo0]',
        'x': '[xks]',
        '0': '[0o]',
        'u': '[uw]',
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
        '.': '.*',
        '_': '.*',
        '-': '.*',
        '(': '.*',
        ')': '.*',
    }
    
    fuzzy_chars = []
    for char in name.lower():
        if char not in ['*', '?', '|', '&']:
            # Replace non-letter symbols with '.*' if not in substitutions
            if char not in substitutions:
                if not char.isalnum():
                    fuzzy_chars.append('.*')
                else:
                    fuzzy_chars.append(f"{char}.?")
            else:
                new_char = substitutions.get(char, char)
                fuzzy_chars.append(f"{new_char}.?")  # Add optional character after each letter
        else:
            fuzzy_chars.append(char)    
    # Join with regex pattern and handle possible missing letters
    fuzzy_pattern = ''.join(fuzzy_chars)
    
    # Make beginning/end more flexible
    fuzzy_pattern = f"{fuzzy_pattern[:-2]}"  # Remove last .? to prevent too much fuzziness
    
    return clean_fuzzy_pattern(fuzzy_pattern)

def make_fuzzy_words(words):
    return [make_string_fuzzy_regex(name) for name in words]

def make_number_fuzzy_regex(string_number):
    # Split into numeric segments (groups of digits) and non-numeric separators
    segments = re.split(r'([0-9]+)', string_number)
    
    # Process each segment: remove leading zeros from numeric segments
    processed_segments = []
    for segment in segments:
        if segment.isdigit():
            # Remove leading zeros and keep at least one digit (in case of all zeros)
            processed_segment = segment.lstrip('0') or '0'
            processed_segments.append(processed_segment)
        else:
            # For non-digit segments, replace with .*
            processed_segments.append('.*')
    
    # Combine the processed segments
    fuzzy_number = ''.join(processed_segments)
    return fuzzy_number
    

def make_fuzzy_numbers(words):
    return [make_number_fuzzy_regex(name) for name in words]

def relax_string_beginning_and_end(name):
    word_list = re.findall(r'([a-zA-Z]+|[^a-zA-Z]+)', name)
    vowels = {'a', 'e', 'i', 'o', 'u', '.', 'á', 'é', 'í', 'ó', 'ú', '?'}
    processed_list = []
    
    for word in word_list:
        # Only process words that contain letters (skip pure non-letter sequences)
        if re.fullmatch(r'[a-zA-Z]+', word):
            new_word = word
            if len(word) >= 2:
                # Check beginning of word
                first_two = word[:2].lower()
                if first_two[0] not in vowels and first_two[1] not in vowels:
                    new_word = '.?' + word[1:]
            
                # Check end of word
                last_two = new_word[-2:].lower()
                if last_two[0] not in vowels and last_two[1] not in vowels:
                    new_word = new_word[:-1] + '.?'
                if last_two[1] == 'z':
                    new_word = new_word[:-1] + '.?'
            
            processed_list.append(new_word)
        else:
            processed_list.append(word)
    try:
        new_name = ''.join(processed_list)
        if '|' not in new_name:
            new_name = new_name + '|' + ''.join(processed_list[::-1])
    except Exception as e:
        logger.info(f"Processed list: {processed_list}")
        logger.error(f"Error processing name: {name}. Error: {e}")
        raise e
    
    return clean_fuzzy_pattern(new_name)

def relax_beginning_and_end_all(names):
    return [relax_string_beginning_and_end(name) for name in names]


def relax_cliente_filter_level1(query_string):
    logger.info(f"Original query. Level 1: {query_string}" )

    column_name = "Cliente"
    names = extract_strings_from_query(query_string, column_name)
    logger.info(f"Extracted names: {names}")

    new_names = relax_beginning_and_end_all(names)
    new_query = replace_words_in_query(query_string, column_name, new_names)
    logger.info(f"Updated query: {new_query}")
    return new_query

def relax_cliente_filter_level2(query_string):
    logger.info(f"Original query. Level 2: {query_string}" )

    column_name = "Cliente"
    names = extract_strings_from_query(query_string, column_name)
    logger.info(f"Extracted names: {names}")

    new_names = make_fuzzy_words(names)
    new_query = replace_words_in_query(query_string, column_name, new_names)
    logger.info(f"Updated query: {new_query}")
    return new_query

def relax_telefono_filter(query_string):
    logger.info(f"Original query Tel1: {query_string}" )

    column_name = "Tel1"
    numbers = extract_strings_from_query(query_string, column_name)
    logger.info(f"Extracted phone numbers: {numbers}")

    new_numbers = make_fuzzy_numbers(numbers)
    new_query = replace_words_in_query(query_string, column_name, new_numbers)
    logger.info(f"Updated query: {new_query}")
    return new_query

def relax_marca_filter(query_string):
    logger.info(f"Original query marca filter: {query_string}" )

    column_name = "Marca"
    words = extract_strings_from_query(query_string, column_name)
    logger.info(f"Extracted words: {words}")

    new_words = make_fuzzy_words(words)
    new_query = replace_words_in_query(query_string, column_name, new_words)
    logger.info(f"Updated query: {new_query}")
    return new_query

def relax_modelo_filter(query_string):
    logger.info(f"Original query. Modelo filter: {query_string}" )

    column_name = "Modelo"
    words = extract_strings_from_query(query_string, column_name)
    logger.info(f"Extracted words: {words}")

    new_words = make_fuzzy_words(words)
    new_query = replace_words_in_query(query_string, column_name, new_words)
    logger.info(f"Updated query: {new_query}")
    return new_query