variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "sagemaker_image_uri" {
  description = "URI of SageMaker container image"
  type        = string
  default     = "763104351884.dkr.ecr.ap-south-1.amazonaws.com/huggingface-pytorch-inference:1.13.1-transformers4.26.0-cpu-py39-ubuntu20.04"
}

variable "embedding_model_name" {
  description = "Embedding model to use"
  type        = string
  default     = "sentence-transformers/all-MiniLM-L6-v2"
}