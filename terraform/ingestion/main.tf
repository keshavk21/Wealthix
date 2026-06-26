# Data source for current AWS account ID
data "aws_caller_identity" "current" {}

# ========================================
# S3 Vectors Bucket + Index
# ========================================

# S3 Vector Bucket (NOT a regular S3 bucket — this is the S3 Vectors service)
resource "aws_s3vectors_vector_bucket" "vectors" {
  vector_bucket_name = "wealthix-vectors-${data.aws_caller_identity.current.account_id}"

  encryption_configuration {
    sse_type = "AES256"
  }
}

# Vector Index inside the bucket
# 384 dimensions = all-MiniLM-L6-v2 output size
# cosine = best for sentence similarity
resource "aws_s3vectors_index" "financial_research" {
  index_name         = "financial-research"
  vector_bucket_name = aws_s3vectors_vector_bucket.vectors.vector_bucket_name
  data_type          = "float32"
  dimension          = 384
  distance_metric    = "cosine"
}

# ========================================
# Lambda Function for Ingestion
# ========================================

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "wealthix-ingest-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project = "wealthix"
    Phase   = "3-ingestion"
  }
}

# IAM Policy — least privilege: CloudWatch logs, SageMaker invoke, S3 Vectors operations
resource "aws_iam_role_policy" "lambda_policy" {
  name = "wealthix-ingest-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs — write only
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      # SageMaker — invoke endpoint only (not full access)
      {
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint"
        ]
        Resource = "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:endpoint/${var.sagemaker_endpoint_name}"
      },
      # S3 Vectors — put, query, get, delete vectors
      {
        Effect = "Allow"
        Action = [
          "s3vectors:PutVectors",
          "s3vectors:QueryVectors",
          "s3vectors:GetVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:ListVectors"
        ]
        Resource = "arn:aws:s3vectors:${var.aws_region}:${data.aws_caller_identity.current.account_id}:bucket/${aws_s3vectors_vector_bucket.vectors.vector_bucket_name}/index/*"
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "ingest" {
  function_name = "wealthix-ingest"
  role          = aws_iam_role.lambda_role.arn

  # Deployment package — created by backend/ingest/package.py
  filename         = "${path.module}/../../backend/ingest/lambda_function.zip"
  source_code_hash = fileexists("${path.module}/../../backend/ingest/lambda_function.zip") ? filebase64sha256("${path.module}/../../backend/ingest/lambda_function.zip") : null

  handler     = "ingest.lambda_handler"
  runtime     = "python3.12"
  timeout     = 60
  memory_size = 512

  environment {
    variables = {
      VECTOR_BUCKET      = aws_s3vectors_vector_bucket.vectors.vector_bucket_name
      VECTOR_INDEX       = aws_s3vectors_index.financial_research.index_name
      SAGEMAKER_ENDPOINT = var.sagemaker_endpoint_name
    }
  }

  tags = {
    Project = "wealthix"
    Phase   = "3-ingestion"
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.lambda_logs
  ]
}

# CloudWatch Log Group — 7-day retention to control costs
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/wealthix-ingest"
  retention_in_days = 7

  tags = {
    Project = "wealthix"
    Phase   = "3-ingestion"
  }
}

# ========================================
# API Gateway (REST API with API Key auth)
# ========================================

# REST API
resource "aws_api_gateway_rest_api" "api" {
  name        = "wealthix-api"
  description = "Wealthix Financial Planner — Ingestion API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Project = "wealthix"
    Phase   = "3-ingestion"
  }
}

# /ingest resource
resource "aws_api_gateway_resource" "ingest" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "ingest"
}

# POST /ingest — requires API key
resource "aws_api_gateway_method" "ingest_post" {
  rest_api_id      = aws_api_gateway_rest_api.api.id
  resource_id      = aws_api_gateway_resource.ingest.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

# Lambda proxy integration
resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.ingest.id
  http_method = aws_api_gateway_method.ingest_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ingest.invoke_arn
}

# Allow API Gateway to invoke the Lambda function
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# Deployment — triggers redeployment when resources change
resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.ingest.id,
      aws_api_gateway_method.ingest_post.id,
      aws_api_gateway_integration.lambda.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Stage — prod
resource "aws_api_gateway_stage" "api" {
  deployment_id = aws_api_gateway_deployment.api.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "prod"

  tags = {
    Project = "wealthix"
    Phase   = "3-ingestion"
  }
}

# API Key
resource "aws_api_gateway_api_key" "api_key" {
  name = "wealthix-api-key"

  tags = {
    Project = "wealthix"
    Phase   = "3-ingestion"
  }
}

# Usage Plan — rate limits to prevent accidental cost spikes
resource "aws_api_gateway_usage_plan" "plan" {
  name = "wealthix-usage-plan"

  api_stages {
    api_id = aws_api_gateway_rest_api.api.id
    stage  = aws_api_gateway_stage.api.stage_name
  }

  quota_settings {
    limit  = 10000
    period = "MONTH"
  }

  throttle_settings {
    rate_limit  = 100
    burst_limit = 200
  }
}

# Link API Key to Usage Plan
resource "aws_api_gateway_usage_plan_key" "plan_key" {
  key_id        = aws_api_gateway_api_key.api_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.plan.id
}
