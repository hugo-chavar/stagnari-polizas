import re
import logging
import pandas as pd
from thefuzz import fuzz

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
    # Pattern matches: 
    # column_name.fillna('').str.contains('...') or
    # column_name.str.contains('...')
    pattern = rf"{column_name}(?:\.fillna\(''\))?\.str\.contains\('([^']*)'"
    names = re.findall(pattern, query_string)
    return [clean_string(name) for name in names]

def replace_words_in_query(query_string, column_name, new_words):
    # Split the query string while preserving column.contains() structure
    # Pattern now matches both with and without .fillna('')
    pattern = rf"({re.escape(column_name)}(?:\.fillna\(''\))?\.str\.contains\('[^']*')"
    parts = re.split(pattern, query_string)
    
    # Find all indices where column.contains() appears (with or without fillna)
    contains_indices = [
        i for i, part in enumerate(parts) 
        if re.match(rf"^{re.escape(column_name)}(?:\.fillna\(''\))?\.str\.contains\('", part)
    ]
    
    # Verify the number of words matches
    if len(contains_indices) != len(new_words):
        raise ValueError(
            f"Expected {len(contains_indices)} words to replace, but got {len(new_words)}"
        )
    
    # Replace each occurrence with the new word (preserving original fillna structure)
    for idx, word in zip(contains_indices, new_words):
        # Check if the original had fillna or not
        original_part = parts[idx]
        if f"{column_name}.fillna('').str.contains('" in original_part:
            parts[idx] = f"{column_name}.fillna('').str.contains('{word}'"
        else:
            parts[idx] = f"{column_name}.str.contains('{word}'"
    
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
        if char not in ['*', '?', '|', '&', '(', ')']:
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


def weighted_fuzzy_search(df, target_column, target_string, top_n=10):
    """
    Perform weighted fuzzy matching and return top N results plus any ties with the Nth score.
    
    Args:
        df: pandas DataFrame
        target_column: column name to search in
        target_string: string to match against
        top_n: minimum number of top results to return
        
    Returns:
        DataFrame with top matches sorted by weighted score (including ties for last position)
    """
    # Split target into words and create decreasing weights
    target_words = target_string.upper().split()
    num_words = len(target_words)
    weights = [1 / (i + 1) for i in range(num_words)]  # Decreasing weights
    weights = [w / sum(weights) for w in weights]  # Normalize to sum to 1
    
    def calculate_weighted_score(candidate):
        if pd.isna(candidate):
            return 0
        candidate = str(candidate).upper()
        total_score = 0
        for word, weight in zip(target_words, weights):
            # Use partial_ratio for substring matching
            score = fuzz.partial_ratio(word, candidate)
            total_score += score * weight
        return round(total_score, 1)
    
    # Calculate scores for all rows
    df['match_score'] = df[target_column].fillna('').apply(calculate_weighted_score)
    
    # Sort by score descending
    df_sorted = df.sort_values('match_score', ascending=False)
    
    # Get all rows with score >= Nth score
    if len(df_sorted) > top_n:
        nth_score = df_sorted.iloc[top_n-1]['match_score']
        result = df_sorted[df_sorted['match_score'] >= nth_score]
    else:
        result = df_sorted
    
    result = result.drop(columns=['match_score'])
    return result
