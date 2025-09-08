# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# HTTP API Gateway with CORS
resource "aws_apigatewayv2_api" "idp_api" {
  name          = "idp-pipeline-api"
  protocol_type = "HTTP"
  description   = "IDP Pipeline API with CORS"

  cors_configuration {
    allow_origins     = ["http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com"]
    allow_methods     = ["GET", "POST", "PUT", "OPTIONS"]
    allow_headers     = ["Content-Type", "Authorization", "Idempotency-Key", "x-amz-meta-userid", "x-amz-meta-docid"]
    expose_headers    = ["ETag"]
    max_age          = 3600
    allow_credentials = false
  }
}

# Upload URL route
resource "aws_apigatewayv2_route" "upload_url" {
  api_id    = aws_apigatewayv2_api.idp_api.id
  route_key = "GET /upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.upload_url_integration.id}"
}

resource "aws_apigatewayv2_integration" "upload_url_integration" {
  api_id           = aws_apigatewayv2_api.idp_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = "arn:aws:lambda:us-east-1:995805900737:function:s3-upload-handler"
  integration_method = "POST"
}

# Process route
resource "aws_apigatewayv2_route" "process" {
  api_id    = aws_apigatewayv2_api.idp_api.id
  route_key = "POST /process"
  target    = "integrations/${aws_apigatewayv2_integration.process_integration.id}"
}

resource "aws_apigatewayv2_integration" "process_integration" {
  api_id           = aws_apigatewayv2_api.idp_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = "arn:aws:lambda:us-east-1:995805900737:function:api-gateway-processor"
  integration_method = "POST"
}

# S3 bucket CORS for presigned PUT
resource "aws_s3_bucket_cors_configuration" "uploads_cors" {
  bucket = "taxflowsai-uploads"

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "GET", "HEAD"]
    allowed_origins = ["http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Stage with auto-deploy
resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.idp_api.id
  name        = "prod"
  auto_deploy = true
}

# Lambda permissions
resource "aws_lambda_permission" "upload_handler_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = "s3-upload-handler"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.idp_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "process_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = "api-gateway-processor"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.idp_api.execution_arn}/*/*"
}

# Output API URL
output "api_gateway_url" {
  value = "${aws_apigatewayv2_api.idp_api.execution_arn}/prod"
}

output "api_gateway_invoke_url" {
  value = "https://${aws_apigatewayv2_api.idp_api.id}.execute-api.us-east-1.amazonaws.com/prod"
}