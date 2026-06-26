terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Local backend — state stored in terraform.tfstate in this directory
  # Automatically gitignored for security
}

provider "aws" {
  region = var.aws_region
}
