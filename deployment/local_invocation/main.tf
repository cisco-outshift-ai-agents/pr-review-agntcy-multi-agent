module "aws-lambda" {
  source = "../lambda"
}

resource "aws_apigatewayv2_api" "lambda_local_api" {
  name          = "AlfredAPI"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_local_integration" {
  api_id           = aws_apigatewayv2_api.lambda_local_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = module.aws-lambda.lambda_invoke_arn
}

resource "aws_apigatewayv2_route" "get_route" {
  api_id    = aws_apigatewayv2_api.lambda_local_api.id
  route_key = "POST /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_local_integration.id}"
}