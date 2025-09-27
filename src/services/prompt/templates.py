"""
Prompt Templates Module

This module provides a collection of prompt templates for various tasks.
Each template can be loaded and customized by the prompt manager service.
"""

# Simple conversation prompts
CONVERSATION_PROMPTS = {
    "greeting": """
        You are a helpful AI assistant. Please respond to the user's greeting in a friendly and professional manner.
        
        User message: {user_message}
        
        Respond warmly and ask how you can help them today.
    """.strip(),
    "question_answer": """
        You are a knowledgeable AI assistant. Please provide a clear and accurate answer to the following question.
        
        Question: {question}
        
        Provide a helpful response that directly addresses the question.  
    """.strip(),
}

# Text analysis prompts
TEXT_ANALYSIS_PROMPTS = {
    "sentiment_analysis": """
        Analyze the sentiment of the following text and classify it as POSITIVE, NEGATIVE, or NEUTRAL.
        
        Text: {text}
        
        Respond in this format:
        Sentiment: [POSITIVE/NEGATIVE/NEUTRAL]
        Confidence: [0.0-1.0]
        Reasoning: [Brief explanation]
    """.strip(),
    "text_summary": """
        Please provide a concise summary of the following text in {max_sentences} sentences or less.
        
        Text: {text}
        
        Summary:
    """.strip(),
    "key_extraction": """
        Extract the key information from the following text and present it in a structured format.
        
        Text: {text}
        
        Key Information:
        - Main Topic: 
        - Key Points:
        - Important Details:
    """.strip(),
    "issue_resolution_flow_time": """
        Please review the following text describing an aircraft issue and its resolution process. Your task is to:

        1. Identify the exact point in the text where the issue is resolved and the aircraft is cleared to fly again.
        2. Determine the total flow time taken to resolve the issue, defined as the elapsed time from when the issue was first identified to when the aircraft is ready to fly.
        3. Provide a clear rationale explaining how you determined the flow time, including any assumptions made about timestamps, events, or indicators in the text.

        Text: {text}
    """.strip(),
}

# Data processing prompts
DATA_PROCESSING_PROMPTS = {
    "categorization": """
        Categorize the following item into one of these categories: {categories}
        
        Item: {item}
        
        Respond in this format:
        Category: [Selected category]
        Confidence: [0.0-1.0]
        Justification: [Brief explanation]
    """.strip(),
    "data_validation": """
        Validate the following data entry and check for any potential issues or inconsistencies.
        
        Data: {data}
        Expected format: {format_description}
        
        Respond in this format:
        Status: [VALID/INVALID/WARNING]
        Issues: [List any problems found]
        Suggestions: [Recommendations for improvement]
    """.strip(),
}

# All available prompts organized by category
ALL_PROMPTS = {
    "conversation": CONVERSATION_PROMPTS,
    "text_analysis": TEXT_ANALYSIS_PROMPTS,
    "data_processing": DATA_PROCESSING_PROMPTS,
}
