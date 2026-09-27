variable "domain_name" {
  description = "OpenSearch domain name"
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

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "kms_key_arn" {
  description = "KMS key ARN for encryption"
  type        = string
}

variable "master_user_arn" {
  description = "IAM ARN for the OpenSearch master user"
  type        = string
}

variable "instance_type" {
  description = "OpenSearch instance type"
  type        = string
  default     = "t3.medium.search"
}

variable "master_instance_type" {
  description = "OpenSearch dedicated master instance type"
  type        = string
  default     = "t3.medium.search"
}

variable "instance_count" {
  description = "Number of OpenSearch data nodes"
  type        = number
  default     = 1
}

variable "ebs_volume_size" {
  description = "EBS volume size in GB per node"
  type        = number
  default     = 20
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access OpenSearch"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
