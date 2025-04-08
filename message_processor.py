def generate_response(incoming_message: str) -> str:
    """
    Processes incoming WhatsApp message and returns appropriate response.
    
    Args:
        incoming_message: The received message (lowercased)
        
    Returns:
        str: The response to send back
    """
    incoming_message = incoming_message.lower()
    
    if "hello" in incoming_message:
        return "Hi there! How can I help you?"
    elif "help" in incoming_message:
        return "I can help with X, Y, and Z. What do you need?"
    elif "bye" in incoming_message:
        return "Goodbye! Have a great day!"
    # Add more conditions as needed
    
    # Default response if no matches
    return "I didn't understand that. Type 'help' for options."