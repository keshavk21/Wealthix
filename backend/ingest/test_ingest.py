"""
Test the deployed ingest Lambda via API Gateway.

Sends a sample financial document and verifies it gets stored in S3 Vectors.

Prerequisites:
  - terraform apply completed in terraform/ingestion/
  - .env has WEALTHIX_API_ENDPOINT and WEALTHIX_API_KEY set

Usage:
    python test_ingest.py
"""

import json
import os
import sys
import urllib.request
import urllib.error

# ─── Load .env file (simple parser, no dependencies) ────────────────────────
def load_env():
    """Load variables from the root .env file."""
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if not os.path.exists(env_path):
        print(f"⚠️  .env file not found at {os.path.abspath(env_path)}")
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def test_ingest():
    """Send a test document to the ingest API."""
    load_env()

    api_endpoint = os.environ.get("WEALTHIX_API_ENDPOINT", "")
    api_key      = os.environ.get("WEALTHIX_API_KEY", "")

    if not api_endpoint:
        print("ERROR: WEALTHIX_API_ENDPOINT not set in .env")
        print("  Run: cd terraform/ingestion && terraform output api_endpoint")
        sys.exit(1)

    if not api_key:
        print("ERROR: WEALTHIX_API_KEY not set in .env")
        print("  Run: cd terraform/ingestion && terraform output -raw api_key_value")
        sys.exit(1)

    # Sample financial document
    payload = {
        "content": (
            "Tesla reported Q4 2025 revenue of $25.7 billion, "
            "exceeding analyst expectations of $24.3 billion. "
            "The company's energy generation and storage segment "
            "grew 113% year-over-year, becoming a significant "
            "contributor to overall profitability. "
            "Free cash flow reached $4.4 billion for the quarter."
        ),
        "metadata": {
            "source": "test_ingest.py",
            "topic": "earnings",
            "company": "Tesla",
            "quarter": "Q4-2025",
        },
    }

    print(f"🚀 Sending test document to: {api_endpoint}")
    print(f"   Content length: {len(payload['content'])} chars")
    print()

    # Make the request
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_endpoint,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))

            print(f"✅ Status: {status}")
            print(f"   Response: {json.dumps(body, indent=2)}")

            if body.get("doc_id"):
                print(f"\n   📄 Document stored with ID: {body['doc_id']}")
                print(f"   📐 Embedding dimension: {body.get('dimension', 'N/A')}")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        print(f"   Response: {error_body}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_ingest()
