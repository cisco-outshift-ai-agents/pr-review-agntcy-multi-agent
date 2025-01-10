provider "aws" {
  region = "eu-west-1"
}

terraform {
  backend "s3" {
    bucket = "alfred-tf-state-euw1"
    key    = "dev/terraform.tfstate"
    region = "eu-west-1"
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.54.1"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "2.4.2"
    }
  }
}

data "aws_secretsmanager_secret" "openapi-secret-metadata" {
  arn = "arn:aws:secretsmanager:eu-west-1:471112537430:secret:alfred-dev-azure-openai-EWEaNW"
}

data "aws_secretsmanager_secret_version" "openai-secret" {
  secret_id = data.aws_secretsmanager_secret.openapi-secret-metadata.id
}

data "aws_secretsmanager_secret" "gh-secret-metadata" {
  arn = "arn:aws:secretsmanager:eu-west-1:471112537430:secret:alfred-dev-gh-tf78gN"
}

data "aws_secretsmanager_secret_version" "gh-secret" {
  secret_id = data.aws_secretsmanager_secret.gh-secret-metadata.id
}

resource "aws_iam_role" "alfred-exec-role" {
  name = "alfred-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "alfred_lambda_basic_execution" {
  role       = aws_iam_role.alfred-exec-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "alfred-lambda" {
  function_name = var.lambda_function_name
  package_type = "Image"
  image_uri = "${var.image_repo}:${var.image_tag}"
  description = "Alfred code reviewer lambda function"
  role = aws_iam_role.alfred-exec-role.arn


  environment {
    variables = {
      AZURE_OPENAI_API_KEY = jsondecode(data.aws_secretsmanager_secret_version.openai-secret.secret_string)["key_1"]
      AZURE_OPENAI_API_VERSION = "2024-08-01-preview"
      AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
      AZURE_OPENAI_ENDPOINT = "https://prcoach-project-agents.openai.azure.com"
      GITHUB_APP_ID = 1065077
      GITHUB_APP_PRIVATE_KEY = jsondecode(data.aws_secretsmanager_secret_version.gh-secret.secret_string)["gh_app_private_key"]
      LOG_LEVEL = "DEBUG"
    }
  }
}

resource "aws_lambda_function_url" "alfred-lambda-url" {
  authorization_type = "NONE"
  function_name      = aws_lambda_function.alfred-lambda.function_name
}

resource "aws_lambda_permission" "allow_function_url" {
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.alfred-lambda.function_name
  principal     = "*"
  source_arn = aws_lambda_function_url.alfred-lambda-url.function_arn
  function_url_auth_type = "AWS_IAM"
}

resource "aws_apigatewayv2_api" "lambda_local_api" {
  count = var.is_local_run ? 1 : 0
  name          = "AlfredAPI"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_local_integration" {
  count = var.is_local_run ? 1 : 0
  api_id           = aws_apigatewayv2_api.lambda_local_api[0].id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.alfred-lambda.arn
}

resource "aws_apigatewayv2_route" "get_route" {
  count = var.is_local_run ? 1 : 0
  api_id    = aws_apigatewayv2_api.lambda_local_api[0].id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_local_integration[0].id}"
}