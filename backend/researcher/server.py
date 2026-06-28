import os
import glob
from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel
from context import get_agent_instruction
from tool import ingest
from mcp_server import create_playwright_mcp_server

load_dotenv(find_dotenv(), override=True)

print("Bedrock auth present:", bool(os.environ.get("AWS_BEARER_TOKEN_BEDROCK")))
print("AWS region:", os.environ.get("AWS_REGION_NAME"))

app = FastAPI(title="Alex Researcher Service")

class ResearchRequest(BaseModel):
    topic: Optional[str] = None

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/research")
async def research(request: ResearchRequest):
    query = f"Research this investment topic: {request.topic}" if request.topic else "Research the latest stock market trends."

    model_name = os.environ.get("RESEARCHER_MODEL", "bedrock/us.")
    model = LitellmModel(model=model_name)

    async with create_playwright_mcp_server(timeout_seconds=120) as playwright_mcp:
        agent = Agent(
            name="Alex Investment Researcher",
            instructions=get_agent_instruction(),
            model=model,
            tools=[ingest],
            mcp_servers=[playwright_mcp]
        )

        result = await Runner.run(agent, input=query)
        return {"result": result.final_output}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)