# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# API Gateway for IDP Pipeline
resource "aws_api_gateway_rest_api" "idp_api" {
  name        = "idp-pipeline-api"
  description = "IDP Pipeline API"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# Upload URL resource
resource "aws_api_gateway_resource" "upload_url" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  parent_id   = aws_api_gateway_rest_api.idp_api.root_resource_id
  path_part   = "upload-url"
}

resource "aws_api_gateway_method" "upload_url_get" {
  rest_api_id   = aws_api_gateway_rest_api.idp_api.id
  resource_id   = aws_api_gateway_resource.upload_url.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "upload_url_integration" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  resource_id = aws_api_gateway_resource.upload_url.id
  http_method = aws_api_gateway_method.upload_url_get.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:995805900737:function:s3-upload-handler/invocations"
}

# Process resource
resource "aws_api_gateway_resource" "process" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  parent_id   = aws_api_gateway_rest_api.idp_api.root_resource_id
  path_part   = "process"
}

resource "aws_api_gateway_method" "process_post" {
  rest_api_id   = aws_api_gateway_rest_api.idp_api.id
  resource_id   = aws_api_gateway_resource.process.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "process_integration" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  resource_id = aws_api_gateway_resource.process.id
  http_method = aws_api_gateway_method.process_post.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:995805900737:function:idp-simple-test/invocations"
}

# CORS for process
resource "aws_api_gateway_method" "process_options" {
  rest_api_id   = aws_api_gateway_rest_api.idp_api.id
  resource_id   = aws_api_gateway_resource.process.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "process_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  resource_id = aws_api_gateway_resource.process.id
  http_method = aws_api_gateway_method.process_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "process_options_response" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  resource_id = aws_api_gateway_resource.process.id
  http_method = aws_api_gateway_method.process_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "process_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  resource_id = aws_api_gateway_resource.process.id
  http_method = aws_api_gateway_method.process_options.http_method
  status_code = aws_api_gateway_method_response.process_options_response.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# CORS for upload-url
resource "aws_api_gateway_method" "upload_url_options" {
  rest_api_id   = aws_api_gateway_rest_api.idp_api.id
  resource_id   = aws_api_gateway_resource.upload_url.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "upload_url_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  resource_id = aws_api_gateway_resource.upload_url.id
  http_method = aws_api_gateway_method.upload_url_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "upload_url_options_response" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  resource_id = aws_api_gateway_resource.upload_url.id
  http_method = aws_api_gateway_method.upload_url_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "upload_url_options_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
  resource_id = aws_api_gateway_resource.upload_url.id
  http_method = aws_api_gateway_method.upload_url_options.http_method
  status_code = aws_api_gateway_method_response.upload_url_options_response.status_code
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Lambda permissions
resource "aws_lambda_permission" "upload_handler_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = "s3-upload-handler"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.idp_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "process_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = "idp-simple-test"
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.idp_api.execution_arn}/*/*"
}

# Deployment
resource "aws_api_gateway_deployment" "idp_deployment" {
  depends_on = [
    aws_api_gateway_method.upload_url_get,
    aws_api_gateway_method.process_post,
    aws_api_gateway_integration.upload_url_integration,
    aws_api_gateway_integration.process_integration
  ]
  
  rest_api_id = aws_api_gateway_rest_api.idp_api.id
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.idp_deployment.id
  rest_api_id   = aws_api_gateway_rest_api.idp_api.id
  stage_name    = "prod"
}

# Output API URL
output "api_gateway_url" {
  value = "${aws_api_gateway_rest_api.idp_api.execution_arn}/prod"
}

output "api_gateway_invoke_url" {
  value = "https://${aws_api_gateway_rest_api.idp_api.id}.execute-api.us-east-1.amazonaws.com/prod"
}