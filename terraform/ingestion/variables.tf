variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "sagemaker_endpoint_name" {
  description = "Name of the SageMaker embedding endpoint (from Phase 2)"
  type        = string
  default     = "wealthix-embedding-endpoint"
}
