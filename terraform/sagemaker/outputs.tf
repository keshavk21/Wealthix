output "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.embedding_endpoint.name
}

output "sagemaker_endpoint_arn" {
  description = "ARN of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.embedding_endpoint.arn
}

output "setup_instructions" {
  description = "Instructions for setting up environment variables"
  value = "SageMaker endpoint deployed successfully!"
}