variable "is_local_run" {
  type = bool
  default = false
  description = "Set to true if you want to run the lambda locally"
}

variable "lambda_function_name" {
  type = string
  default = "alfred-dev"
  description = "Name of the lambda function"
}

variable "image_repo" {
    type = string
    default = "471112537430.dkr.ecr.eu-west-1.amazonaws.com/alfred-dev-deployment-test"
    description = "ECR repository URI"
}

variable "image_tag" {
    type = string
    default = "aws-3"
    description = "ECR image tag"
}