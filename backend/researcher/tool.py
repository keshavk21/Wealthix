import httpx
import json
import os
from agents import function_tool

@function_tool
def ingest(payload: str) -> str:
    """
    Ingests data to the Wealthix API endpoint.
    
    Args:
        payload: A JSON-formatted string representing the data to be ingested.
        
    Returns:
        The response from the server as a JSON string.
    """
    try:
        wealthix_api_endpoint = os.environ.get("WEALTHIX_API_ENDPOINT")
        if not wealthix_api_endpoint:
            return json.dumps({"success": False, "error": "WEALTHIX_API_ENDPOINT is not configured."})
            
        parsed_payload = json.loads(payload)
        with httpx.Client() as client:
            response = client.post(wealthix_api_endpoint, json=parsed_payload, timeout=30.0)
            response.raise_for_status()
            return response.text
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
