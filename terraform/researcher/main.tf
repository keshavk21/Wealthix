terraform {
  required_version = ">=1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">=6.28.0"
    }
  }
}


# Data source for current caller identity
data "aws_caller_identity" "current" {}

# ECR repository for the researcher Docker image
resource "aws_ecr_repository" "researcher" {
    name ="wealthix-researcher"
    image_tag_mutability = "MUTABLE"
    force_delete = true

    image_scanning_configuration{
        scan_on_push = false
    }

    tags ={
        Project ="wealthix"
    }
}
