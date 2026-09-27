output "vpc_id" {
  description = "VPC ID"
  value       = module.network.vpc_id
}

output "aurora_endpoint" {
  description = "Aurora cluster endpoint"
  value       = module.aurora.cluster_endpoint
  sensitive   = true
}

output "approval_queue_url" {
  description = "SQS approval queue URL"
  value       = module.sqs.approval_queue_url
}

output "change_events_queue_url" {
  description = "SQS change events queue URL"
  value       = module.sqs.change_events_queue_url
}

output "runbooks_bucket_name" {
  description = "S3 runbooks bucket name"
  value       = module.s3.runbooks_bucket_name
}
