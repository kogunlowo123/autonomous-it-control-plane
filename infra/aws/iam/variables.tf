variable "prefix" {
  description = "Resource name prefix"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "eks_oidc_provider_url" {
  description = "OIDC provider URL from the EKS cluster"
  type        = string
}

variable "sqs_queue_arns" {
  description = "SQS queue ARNs to grant access to"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
