output "vector_bucket_name" {
  description = "Name of the S3 Vectors bucket"
  value       = aws_s3vectors_vector_bucket.vectors.vector_bucket_name
}

output "vector_index_name" {
  description = "Name of the vector index"
  value       = aws_s3vectors_index.financial_research.index_name
}

output "lambda_function_name" {
  description = "Name of the ingest Lambda function"
  value       = aws_lambda_function.ingest.function_name
}

output "api_endpoint" {
  description = "API Gateway endpoint URL for ingestion"
  value       = "${aws_api_gateway_stage.api.invoke_url}/ingest"
}

output "api_key_id" {
  description = "API Key ID (use aws cli to get the actual value)"
  value       = aws_api_gateway_api_key.api_key.id
}

output "api_key_value" {
  description = "API Key value"
  value       = aws_api_gateway_api_key.api_key.value
  sensitive   = true
}

output "setup_instructions" {
  description = "Next steps after deployment"
  value = <<-EOT

    ✅ Ingestion pipeline deployed successfully!

    Add the following to your .env file:
    VECTOR_BUCKET=${aws_s3vectors_vector_bucket.vectors.vector_bucket_name}
    WEALTHIX_API_ENDPOINT=${aws_api_gateway_stage.api.invoke_url}/ingest

    To get your API key value:
    aws apigateway get-api-key --api-key ${aws_api_gateway_api_key.api_key.id} --include-value --query 'value' --output text

    Then add to .env:
    WEALTHIX_API_KEY=<the-api-key-value>

    Test:
    cd backend/ingest
    python test_ingest.py
    python test_search.py

  EOT
}
