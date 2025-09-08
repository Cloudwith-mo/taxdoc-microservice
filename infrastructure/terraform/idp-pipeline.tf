# AWS IDP Pipeline Infrastructure
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "comprehend_endpoint_arn" {
  description = "Comprehend custom classifier endpoint ARN"
  type        = string
  default     = ""
}

# S3 Bucket for uploads
resource "aws_s3_bucket" "uploads" {
  bucket = "taxflowsai-uploads-${var.environment}"
}

resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# SQS Queue for processing
resource "aws_sqs_queue" "ingest" {
  name                      = "idp-ingest-queue-${var.environment}"
  message_retention_seconds = 1209600
  visibility_timeout_seconds = 300
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })
}

resource "aws_sqs_queue" "dlq" {
  name = "idp-ingest-dlq-${var.environment}"
}

# DynamoDB Table
resource "aws_dynamodb_table" "docs" {
  name           = "TaxFlowsAI_Metadata_${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "docType"
    type = "S"
  }

  attribute {
    name = "processedAt"
    type = "N"
  }

  global_secondary_index {
    name               = "docType-index"
    hash_key           = "docType"
    range_key          = "processedAt"
    projection_type    = "ALL"
  }

  server_side_encryption {
    enabled = true
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "idp-processor-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "idp-processor-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObjectTagging"
        ]
        Resource = "${aws_s3_bucket.uploads.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.docs.arn,
          "${aws_dynamodb_table.docs.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "textract:AnalyzeDocument",
          "textract:DetectDocumentText",
          "textract:AnalyzeExpense"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "comprehend:ClassifyDocument"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:DeleteMessage",
          "sqs:ReceiveMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.ingest.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

output "upload_bucket" {
  value = aws_s3_bucket.uploads.id
}

output "metadata_table" {
  value = aws_dynamodb_table.docs.name
}