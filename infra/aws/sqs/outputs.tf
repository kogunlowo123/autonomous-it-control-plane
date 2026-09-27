output "approvals_queue_url" {
  value = aws_sqs_queue.approvals.url
}

output "approvals_queue_arn" {
  value = aws_sqs_queue.approvals.arn
}

output "changes_queue_url" {
  value = aws_sqs_queue.changes.url
}

output "changes_queue_arn" {
  value = aws_sqs_queue.changes.arn
}

output "approvals_dlq_arn" {
  value = aws_sqs_queue.approvals_dlq.arn
}
