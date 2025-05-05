import re
import logging

logger = logging.getLogger(__name__)


def extract_strings_from_query(query_string, column_name):
    # Pattern matches: column_name.fillna('').str.contains('...')
    pattern = rf"{column_name}\.fillna\(''\)\.str\.contains\('([^']*)'"
    names = re.findall(pattern, query_string)
    return names

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
        '.': '.*',
        '_': '.*',
        '-': '.*',
        '(': '.*',
        ')': '.*',
    }
    
    fuzzy_chars = []
    for char in name.lower():
        # Apply substitutions if defined, otherwise keep the original
        if char not in ['*', '?']:
            new_char = substitutions.get(char, char)
            fuzzy_chars.append(f"{new_char}.?")  # Add optional character after each letter
        else:
            fuzzy_chars.append(char)    
    # Join with regex pattern and handle possible missing letters
    fuzzy_pattern = ''.join(fuzzy_chars)
    
    # Make beginning/end more flexible
    fuzzy_pattern = f"{fuzzy_pattern[:-2]}"  # Remove last .? to prevent too much fuzziness
    fuzzy_pattern = fuzzy_pattern.replace('.?.*', '.*').replace('.*.?', '.*').replace('.*.*', '.*').replace('**', '*')
    
    return fuzzy_pattern

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
        new_name = ''.join(processed_list) + '|' + ''.join(processed_list[::-1])
    except Exception as e:
        logger.info(f"Processed list: {processed_list}")
        logger.error(f"Error processing name: {name}. Error: {e}")
        raise e
    new_name = new_name.replace('.?.*', '.*').replace('.*.?', '.*')
    return new_name

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