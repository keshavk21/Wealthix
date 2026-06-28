import json
import os
import tempfile
from agents.mcp import MCPServerStdio

def create_playwright_mcp_server(timeout_seconds=120):
    config_path = os.path.join(tempfile.gettempdir(), "playwright-mcp.config.json")
    config = {
        "browser": {
            "launchOptions": {
                "args": ["--single-process", "--no-zygote", "--disable-gpu"]
            }
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)

    params = {
        "command": "npx.cmd" if os.name == "nt" else "npx",
        "args": [
            "-y",
            "@playwright/mcp@0.0.41",  # pin to a known-good version — check npm for latest stable
            "--headless",
            "--isolated",
            "--no-sandbox",
            "--ignore-https-errors",
            "--config", config_path
        ],
        "env": {}
    }

    return MCPServerStdio(params=params, client_session_timeout_seconds=timeout_seconds)
