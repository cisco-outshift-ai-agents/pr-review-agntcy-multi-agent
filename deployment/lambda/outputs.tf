output "lambda_function_name" {
  value = aws_lambda_function.alfred-lambda.function_name
}

output "lambda_function_url" {
  value = aws_lambda_function_url.alfred-lambda-url.function_url
}

output "lambda_invoke_arn" {
  value = aws_lambda_function.alfred-lambda.invoke_arn
}