"""
Package the ingest Lambda function into a zip for deployment.

Since ingest.py only uses boto3 (built into the Lambda Python 3.12 runtime),
we just need to zip the single file — no pip install required.

Usage:
    python package.py
"""

import os
import zipfile

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE  = os.path.join(SCRIPT_DIR, "ingest.py")
OUTPUT_ZIP   = os.path.join(SCRIPT_DIR, "lambda_function.zip")


def package():
    """Create lambda_function.zip containing ingest.py."""
    if not os.path.exists(SOURCE_FILE):
        print(f"ERROR: {SOURCE_FILE} not found")
        return

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add ingest.py at the root of the zip (not nested in a directory)
        zf.write(SOURCE_FILE, "ingest.py")

    size_kb = os.path.getsize(OUTPUT_ZIP) / 1024
    print(f"[OK] Created {OUTPUT_ZIP} ({size_kb:.1f} KB)")
    print(f"     Handler: ingest.lambda_handler")


if __name__ == "__main__":
    package()
