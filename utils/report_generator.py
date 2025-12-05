"""
Report generation utility using OpenAI GPT-4o.
Analyzes extracted PDF data and generates trustworthiness assessment.
"""

import os
import httpx
from openai import OpenAI

# Load prompt template
PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "report_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    PROMPT_TEMPLATE = f.read()


def generate_vetting_report(documents_text, web_research):
    """
    Generate a comprehensive vetting report using GPT-4o.
    
    Args:
        documents_text (str): Combined extracted text from all uploaded PDFs
        web_research (str): Web research findings in JSON format
        
    Returns:
        str: Formatted markdown report with trustworthiness assessment
    """
    try:
        # Initialize OpenAI client with explicit http_client to avoid proxy issues on Streamlit Cloud
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=httpx.Client()
        )
        
        # Format the prompt with the extracted PDF data and web research
        prompt = PROMPT_TEMPLATE.format(
            documents_text=documents_text,
            web_research=web_research
        )
        
        print("Sending request to GPT-4o...")
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert business analyst specializing in client vetting and risk assessment for event organizing services in Australia."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=2000
        )
        
        # Extract the report from the response
        report = response.choices[0].message.content
        
        print("Report generated successfully!")
        
        return report
    
    except Exception as e:
        raise Exception(f"Error generating report: {str(e)}")

