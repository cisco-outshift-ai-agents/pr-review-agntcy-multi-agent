terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.54.1"
    }
    local = {
      source  = "hashicorp/local"
      version = "2.1.0"
    }
  }
}

locals {
  envs = {for tuple in regexall("(.*)=(.*)", file("../../.env")) : tuple[0] => trim(tuple[1], "'\"")}
}

data "local_file" "github_app_private_key" {
  filename = "../../${local.envs["GITHUB_APP_PRIVATE_KEY_FILE"]}"
}

module "aws_lambda" {
  source = "../lambda"

  lambda_function_name = "alfred_lambda_local"

  aws_region = "eu-west-1"
  aws_secret_region      = "eu-west-1"
  aws_secret_name        = local.envs["AWS_SECRET_NAME"]
  aws_gcp_sa_secret_name = local.envs["AWS_GCP_SA_SECRET_NAME"]

  image_repo = "alfred"
  image_tag  = "local"

  azure_openai_deployment = local.envs["AZURE_OPENAI_DEPLOYMENT"]
  azure_openai_version    = local.envs["AZURE_OPENAI_API_VERSION"]
  azure_openai_api_key    = local.envs["AZURE_OPENAI_API_KEY"]
  azure_openai_endpoint   = local.envs["AZURE_OPENAI_ENDPOINT"]

  github_app_id = tonumber(local.envs["GITHUB_APP_ID"])
  github_app_private_key = coalesce(local.envs["GITHUB_APP_PRIVATE_KEY"], data.local_file.github_app_private_key.content)
  github_webhook_secret = local.envs["GITHUB_WEBHOOK_SECRET"]

  log_level   = "DEBUG"
  environment = "local"
  is_langsmith_enabled = false
}

resource "aws_apigatewayv2_api" "lambda_local_api" {
  name          = "AlfredAPI"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_local_integration" {
  api_id           = aws_apigatewayv2_api.lambda_local_api.id
  integration_type = "AWS_PROXY"
  integration_uri = module.aws_lambda.lambda_invoke_arn
}

resource "aws_apigatewayv2_route" "get_route" {
  api_id    = aws_apigatewayv2_api.lambda_local_api.id
  route_key = "POST /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_local_integration.id}"
}