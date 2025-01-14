variable "lambda_function_name" {
  type        = string
  description = "Name of the lambda function"

  default = "alfred-cd-test"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "eu-west-1"
}

variable "image_repo" {
  type        = string
  description = "ECR repository URI"

  default = "471112537430.dkr.ecr.eu-west-1.amazonaws.com/alfred"
}

variable "image_tag" {
  type        = string
  description = "ECR image tag"

  default = "latest"
}

variable "azure_openai_version" {
  type        = string
  description = "Set AZURE_OPENAI_API_VERSION environment variable"
  default     = "2024-08-01-preview"
}

variable "azure_openai_deployment" {
  type        = string
  description = "Set AZURE_OPENAI_DEPLOYMENT environment variable"
  default     = "gpt-4o"
}

variable "azure_openai_endpoint" {
  type        = string
  description = "Set AZURE_OPENAI_ENDPOINT environment variable"
  default     = "https://prcoach-project-agents.openai.azure.com"
}

variable "azure_openai_api_key" {
  type        = string
  description = "Set AZURE_OPENAI_API_KEY environment variable"
  default     = ""

  validation {
    condition = var.azure_openai_api_key != ""
    error_message = "AZURE_OPENAI_API_KEY is required"
  }
}

variable "github_app_id" {
  type        = number
  description = "Set GITHUB_APP_ID environment variable"

  default = 1065077
}

variable "github_app_private_key" {
  type        = string
  description = "Set GITHUB_APP_PRIVATE_KEY environment variable"
  default = "gapk"

  validation {
    condition = var.github_app_private_key != ""
    error_message = "GITHUB_APP_PRIVATE_KEY is required"
  }
}

variable "github_webhook_secret" {
  type        = string
  description = "Set GITHUB_WEBHOOK_SECRET environment variable"
  default = "gws"
}

variable "is_langsmith_enabled" {
  type        = bool
  description = "Enable langsmith"
  default     = true
}

variable "langchain_api_key" {
  type        = string
  description = "Set LANGCHAIN_API_KEY environment variable"
  default = "lak"

  validation {
    condition = !var.is_langsmith_enabled || var.langchain_api_key != ""
    error_message = "LANGCHAIN_API_KEY is required when is_langsmith_enabled is true"
  }
}

variable "langchain_endpoint" {
  type        = string
  description = "Set LANGCHAIN_ENDPOINT environment variable"
  default     = "https://langsmith.outshift.io/api/v1"

  validation {
    condition = !var.is_langsmith_enabled || var.langchain_endpoint != ""
    error_message = "LANGCHAIN_ENDPOINT is required when is_langsmith_enabled is true"
  }
}

variable "langchain_project" {
  type        = string
  description = "Set LANGCHAIN_PROJECT environment variable"
  default = "alfred-cd-test"

  validation {
    condition = !var.is_langsmith_enabled || var.langchain_project != ""
    error_message = "LANGCHAIN_PROJECT is required when is_langsmith_enabled is true"
  }
}

variable "langchain_tracing_v2" {
  type        = bool
  description = "Set LANGCHAIN_TRACING_V2 environment variable"
  default     = true
}

variable "log_level" {
  type        = string
  description = "Set LOG_LEVEL environment variable"
  default     = "INFO"
}