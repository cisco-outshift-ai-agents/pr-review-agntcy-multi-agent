provider "aws" {
  region = "eu-west-1"
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
  package_type  = "Image"
  image_uri     = "${var.image_repo}:${var.image_tag}"
  description   = "Alfred code reviewer lambda function"
  role          = aws_iam_role.alfred-exec-role.arn


  environment {
    variables = {
      AZURE_OPENAI_API_KEY = var.azure_openai_api_key
      AZURE_OPENAI_API_VERSION = var.azure_openai_version
      AZURE_OPENAI_DEPLOYMENT  = var.azure_openai_deployment
      AZURE_OPENAI_ENDPOINT    = var.azure_openai_endpoint
      GITHUB_APP_ID            = var.github_app_id
      GITHUB_APP_PRIVATE_KEY   = var.github_app_private_key
      GITHUB_WEBHOOK_SECRET    = var.github_webhook_secret
      LANGCHAIN_API_KEY        = var.is_langsmith_enabled ? var.langchain_api_key : null
      LANGCHAIN_ENDPOINT       = var.is_langsmith_enabled ? var.langchain_endpoint : null
      LANGCHAIN_PROJECT        = var.is_langsmith_enabled ? var.langchain_project : null
      LANGCHAIN_TRACING_V2     = var.is_langsmith_enabled ? var.langchain_tracing_v2 : null
      LOG_LEVEL                = var.log_level
    }
  }
}

resource "aws_lambda_function_url" "alfred-lambda-url" {
  authorization_type = "NONE"
  function_name      = aws_lambda_function.alfred-lambda.function_name
}

resource "aws_lambda_permission" "allow_function_url" {
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.alfred-lambda.function_name
  principal              = "*"
  source_arn             = aws_lambda_function_url.alfred-lambda-url.function_arn
  function_url_auth_type = "AWS_IAM"
}
