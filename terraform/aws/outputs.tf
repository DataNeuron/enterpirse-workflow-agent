output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "dynamodb_cache_table" {
  description = "DynamoDB cache table name"
  value       = aws_dynamodb_table.cache.name
}

output "dynamodb_state_table" {
  description = "DynamoDB agent state table name"
  value       = aws_dynamodb_table.agent_state.name
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.workflow.url
}

output "s3_logs_bucket" {
  description = "S3 logs bucket name"
  value       = aws_s3_bucket.logs.id
}

output "lambda_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda_exec.arn
}
