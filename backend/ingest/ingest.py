"""
Wealthix Ingest Lambda — Gets embeddings from SageMaker, stores vectors in S3 Vectors.

Flow:
  1. Receive POST via API Gateway  (JSON: content, metadata, optional doc_id)
  2. Call SageMaker endpoint        (all-MiniLM-L6-v2 → 384-dim embedding)
  3. Store in S3 Vectors            (put_vectors → financial-research index)

Environment variables (set by Terraform):
  VECTOR_BUCKET      — S3 Vector bucket name
  VECTOR_INDEX       — Vector index name (default: financial-research)
  SAGEMAKER_ENDPOINT — SageMaker endpoint name
"""

import json
import os
import uuid
import logging

import boto3

# ─── Logging ────────────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ─── Environment ────────────────────────────────────────────────────────────
VECTOR_BUCKET      = os.environ.get("VECTOR_BUCKET", "")
VECTOR_INDEX       = os.environ.get("VECTOR_INDEX", "financial-research")
SAGEMAKER_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT", "")

# ─── AWS Clients (initialized once, reused across invocations) ──────────────
sagemaker_runtime = boto3.client("sagemaker-runtime")
s3vectors_client  = boto3.client("s3vectors")


# ═══════════════════════════════════════════════════════════════════════════
# Core Functions
# ═══════════════════════════════════════════════════════════════════════════

def get_embedding(text: str) -> list[float]:
    """
    Call SageMaker endpoint to convert text → 384-dim embedding.

    The model (all-MiniLM-L6-v2) returns shape [1][num_tokens][384].
    We mean-pool across tokens to get a single [384] vector.
    """
    payload = json.dumps({"inputs": text})

    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=payload,
    )

    # Parse response body
    result = json.loads(response["Body"].read().decode("utf-8"))

    # result shape: [[[token1_384], [token2_384], ...]]  (batch=1)
    # We need to mean-pool across all tokens to get a single 384-dim vector
    token_embeddings = result[0]  # Remove batch dimension → [num_tokens][384]
    num_tokens = len(token_embeddings)
    embedding_dim = len(token_embeddings[0])

    # Mean pool: average across all token positions
    embedding = [0.0] * embedding_dim
    for token_vec in token_embeddings:
        for i, val in enumerate(token_vec):
            embedding[i] += val
    embedding = [val / num_tokens for val in embedding]

    logger.info(f"Generated embedding: dim={len(embedding)}, tokens={num_tokens}")
    return embedding


def store_vector(doc_id: str, embedding: list[float], metadata: dict) -> dict:
    """
    Store a vector + metadata in S3 Vectors.

    Uses the s3vectors boto3 client (NOT regular S3).
    Vectors must be float32 format.
    """
    vector_data = {
        "key": doc_id,
        "data": {"float32": embedding},
        "metadata": metadata,
    }

    response = s3vectors_client.put_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=VECTOR_INDEX,
        vectors=[vector_data],
    )

    logger.info(f"Stored vector: doc_id={doc_id}, bucket={VECTOR_BUCKET}, index={VECTOR_INDEX}")
    return response


# ═══════════════════════════════════════════════════════════════════════════
# Lambda Handler
# ═══════════════════════════════════════════════════════════════════════════

def lambda_handler(event, context):
    """
    API Gateway proxy handler.

    Expected JSON body:
      {
        "content":  "Text to embed and store",        (required)
        "metadata": {"source": "...", "topic": "..."}, (optional, default {})
        "doc_id":   "custom-id"                        (optional, auto-generated UUID)
      }

    Returns:
      200 — {"doc_id": "...", "dimension": 384, "message": "..."}
      400 — {"error": "..."} for bad input
      500 — {"error": "..."} for internal errors
    """
    try:
        # ── Parse request body ──────────────────────────────────────────
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        content  = body.get("content", "").strip()
        metadata = body.get("metadata", {})
        doc_id   = body.get("doc_id", str(uuid.uuid4()))

        # ── Validate ────────────────────────────────────────────────────
        if not content:
            return _response(400, {"error": "Missing required field: 'content'"})

        if not VECTOR_BUCKET:
            return _response(500, {"error": "VECTOR_BUCKET environment variable not set"})

        if not SAGEMAKER_ENDPOINT:
            return _response(500, {"error": "SAGEMAKER_ENDPOINT environment variable not set"})

        logger.info(f"Ingesting doc_id={doc_id}, content_length={len(content)}")

        # ── Step 1: Get embedding from SageMaker ────────────────────────
        embedding = get_embedding(content)

        # ── Step 2: Add content to metadata for retrieval ───────────────
        # Store the original text in metadata so we can return it during search
        metadata["content"] = content
        metadata["doc_id"]  = doc_id

        # ── Step 3: Store vector in S3 Vectors ──────────────────────────
        store_vector(doc_id, embedding, metadata)

        # ── Success ─────────────────────────────────────────────────────
        return _response(200, {
            "message":   "Document ingested successfully",
            "doc_id":    doc_id,
            "dimension": len(embedding),
            "bucket":    VECTOR_BUCKET,
            "index":     VECTOR_INDEX,
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return _response(400, {"error": f"Invalid JSON: {str(e)}"})

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return _response(500, {"error": f"Ingestion failed: {str(e)}"})


def _response(status_code: int, body: dict) -> dict:
    """Build an API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
