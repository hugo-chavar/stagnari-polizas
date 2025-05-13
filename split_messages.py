def split_long_message(text: str, max_length: int = 1500, min_length: int = 1000) -> list[str]:
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    remaining_text = text
    
    while len(remaining_text) > max_length:
        # First try to split at double newlines
        split_pos = remaining_text.rfind("\n\n", 0, max_length)
        
        # If not found, try to split at ".\n" followed by a number
        if split_pos == -1:
            split_pos = find_dot_newline_number(remaining_text, max_length)
        
        # If not found, try to split at ".\n" followed by space and symbol
        if split_pos == -1:
            split_pos = find_dot_newline_symbol(remaining_text, max_length)
        
        # If not found, try to split at any newline
        if split_pos == -1:
            split_pos = remaining_text.rfind("\n", 0, max_length)
        
        # If still not found, try to split at sentence end
        if split_pos == -1:
            split_pos = remaining_text.rfind(". ", 0, max_length)
            if split_pos != -1:
                split_pos += 1  # include the dot
        
        # If all else fails, split at max_length
        if split_pos == -1:
            split_pos = max_length
        
        chunk = remaining_text[:split_pos].strip()
        chunks.append(chunk)
        remaining_text = remaining_text[split_pos:].strip()
    
    if remaining_text:
        # If remaining text is small, merge with last chunk
        if chunks and len(remaining_text) < min_length and (len(chunks[-1]) + len(remaining_text) + 1) <= max_length:
            chunks[-1] += "\n\n" + remaining_text
        else:
            chunks.append(remaining_text)
    
    return chunks

def find_dot_newline_number(text: str, max_pos: int) -> int:
    """Find position of ".\n" followed by a number before max_pos"""
    pos = 0
    while True:
        dot_pos = text.find(".\n", pos)
        if dot_pos == -1 or dot_pos > max_pos:
            return -1
        
        next_char_pos = dot_pos + 2
        if next_char_pos < len(text) and text[next_char_pos].isdigit():
            return dot_pos + 1  # include the dot and newline
        
        pos = dot_pos + 1

def find_dot_newline_symbol(text: str, max_pos: int) -> int:
    """Find position of ".\n" followed by space and symbol before max_pos"""
    symbols = {'-', '*', '•', '·', '>', '→'}
    pos = 0
    while True:
        dot_pos = text.find(".\n", pos)
        if dot_pos == -1 or dot_pos > max_pos:
            return -1
        
        next_char_pos = dot_pos + 2
        if (next_char_pos + 1 < len(text) and 
            text[next_char_pos] == ' ' and 
            text[next_char_pos + 1] in symbols):
            return dot_pos + 1  # include the dot and newline
        
        pos = dot_pos + 1