"""
Test vector similarity search against S3 Vectors.

Embeds a query via SageMaker, then searches S3 Vectors for similar documents.
This tests the full retrieval pipeline that the Reporter agent will use.

Prerequisites:
  - At least one document ingested (run test_ingest.py first)
  - .env has VECTOR_BUCKET, SAGEMAKER_ENDPOINT set

Usage:
    python test_search.py
    python test_search.py "custom search query"
"""

import json
import os
import sys

import boto3

# ─── Load .env file ─────────────────────────────────────────────────────────
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


def get_embedding(text: str, endpoint: str, region: str) -> list[float]:
    """Get embedding from SageMaker endpoint with mean pooling."""
    client = boto3.client("sagemaker-runtime", region_name=region)

    response = client.invoke_endpoint(
        EndpointName=endpoint,
        ContentType="application/json",
        Body=json.dumps({"inputs": text}),
    )

    result = json.loads(response["Body"].read().decode("utf-8"))

    # Mean pool across tokens: [1][num_tokens][384] → [384]
    token_embeddings = result[0]
    num_tokens = len(token_embeddings)
    embedding_dim = len(token_embeddings[0])

    embedding = [0.0] * embedding_dim
    for token_vec in token_embeddings:
        for i, val in enumerate(token_vec):
            embedding[i] += val
    embedding = [val / num_tokens for val in embedding]

    return embedding


def search_vectors(query_embedding: list[float], bucket: str, index: str, region: str, top_k: int = 5):
    """Query S3 Vectors for similar documents."""
    client = boto3.client("s3vectors", region_name=region)

    response = client.query_vectors(
        vectorBucketName=bucket,
        indexName=index,
        queryVector={"float32": query_embedding},
        topK=top_k,
    )

    return response.get("vectors", [])


def test_search():
    """Run a similarity search against stored vectors."""
    load_env()

    vector_bucket = os.environ.get("VECTOR_BUCKET", "")
    sagemaker_ep  = os.environ.get("SAGEMAKER_ENDPOINT", "")
    aws_region    = os.environ.get("DEFAULT_AWS_REGION", "ap-south-1")
    vector_index  = "financial-research"

    if not vector_bucket:
        print("ERROR: VECTOR_BUCKET not set in .env")
        print("  Run: cd terraform/ingestion && terraform output vector_bucket_name")
        sys.exit(1)

    if not sagemaker_ep:
        print("ERROR: SAGEMAKER_ENDPOINT not set in .env")
        sys.exit(1)

    # Use command line arg or default query
    query = sys.argv[1] if len(sys.argv) > 1 else "Tesla quarterly earnings revenue"

    print(f"🔍 Search query: \"{query}\"")
    print(f"   Bucket: {vector_bucket}")
    print(f"   Index:  {vector_index}")
    print(f"   Region: {aws_region}")
    print()

    # Step 1: Embed the query
    print("⏳ Getting query embedding from SageMaker...")
    query_embedding = get_embedding(query, sagemaker_ep, aws_region)
    print(f"   Embedding dimension: {len(query_embedding)}")
    print()

    # Step 2: Search S3 Vectors
    print("⏳ Searching S3 Vectors...")
    results = search_vectors(query_embedding, vector_bucket, vector_index, aws_region)

    if not results:
        print("⚠️  No results found. Have you ingested any documents?")
        print("   Run: python test_ingest.py")
        return

    print(f"✅ Found {len(results)} result(s):\n")
    for i, result in enumerate(results, 1):
        key      = result.get("key", "N/A")
        distance = result.get("distance", "N/A")
        metadata = result.get("metadata", {})
        content  = metadata.get("content", "N/A")

        # Truncate content for display
        content_preview = content[:200] + "..." if len(content) > 200 else content

        print(f"  [{i}] Key:      {key}")
        print(f"      Distance: {distance}")
        print(f"      Content:  {content_preview}")
        if metadata.get("source"):
            print(f"      Source:   {metadata['source']}")
        print()


if __name__ == "__main__":
    test_search()
