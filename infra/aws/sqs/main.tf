terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }
}

resource "aws_sqs_queue" "approvals" {
  name                        = "${var.project_name}-approvals.fifo"
  fifo_queue                  = true
  content_based_deduplication = true

  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400  # 24 hours
  receive_wait_time_seconds  = 20     # Long polling

  kms_master_key_id = var.kms_key_id

  tags = merge(var.tags, {
    Name    = "${var.project_name}-approvals"
    Purpose = "Change approval workflow notifications"
  })
}

resource "aws_sqs_queue" "changes" {
  name                        = "${var.project_name}-changes.fifo"
  fifo_queue                  = true
  content_based_deduplication = true

  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400

  kms_master_key_id = var.kms_key_id

  tags = merge(var.tags, {
    Name    = "${var.project_name}-changes"
    Purpose = "Change event emission"
  })
}

resource "aws_sqs_queue" "approvals_dlq" {
  name                        = "${var.project_name}-approvals-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = true

  message_retention_seconds = 1209600  # 14 days

  kms_master_key_id = var.kms_key_id

  tags = merge(var.tags, {
    Name    = "${var.project_name}-approvals-dlq"
    Purpose = "Dead letter queue for failed approval messages"
  })
}

resource "aws_sqs_queue_redrive_policy" "approvals" {
  queue_url = aws_sqs_queue.approvals.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.approvals_dlq.arn
    maxReceiveCount     = 3
  })
}
