#!/usr/bin/env python3
"""
Test the researcher service using AWS CLI invoke (works behind corporate firewalls).
"""

import json
import subprocess
import sys


def invoke_lambda_directly():
    """Invoke Lambda directly via AWS CLI instead of HTTP."""
    print("Testing researcher Lambda via AWS CLI...")
    print("=" * 60)

    try:
        # Create event payload for Lambda Web Adapter
        event = {
            "requestContext": {
                "http": {
                    "method": "GET",
                    "path": "/health"
                }
            },
            "rawPath": "/health"
        }
        
        # Write payload to file to avoid escaping issues
        with open("payload.json", "w") as f:
            json.dump(event, f)
        
        # Invoke the lambda with file-based payload
        result = subprocess.run(
            [
                "aws",
                "lambda",
                "invoke",
                "--function-name",
                "alex-researcher",
                "--payload",
                "file://payload.json",
                "--region",
                "us-east-1",
                "response.json",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"❌ Lambda invocation failed: {result.stderr}")
            sys.exit(1)

        print("✅ Lambda invocation successful!")

        # Read the response
        with open("response.json", "r") as f:
            response_text = f.read()
        
        # The response is the actual body from FastAPI
        try:
            response = json.loads(response_text)
            print("\n" + "=" * 60)
            print("LAMBDA HEALTH CHECK RESPONSE:")
            print("=" * 60)
            print(json.dumps(response, indent=2))
            print("\n✅ Researcher Lambda is healthy and working!")
        except json.JSONDecodeError:
            print(response_text)

    except FileNotFoundError:
        print("❌ Error: AWS CLI not found. Make sure it's installed and in PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    invoke_lambda_directly()
