terraform {
  required_version = ">= 1.8.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }

  backend "s3" {
    bucket         = "autonomous-it-terraform-state-dev"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "autonomous-it-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

locals {
  environment = "dev"
  common_tags = {
    Project     = "autonomous-it-control-plane"
    Environment = local.environment
    ManagedBy   = "terraform"
    Owner       = "kogunlowo123"
  }
}

module "kms" {
  source       = "../../../aws/kms"
  project_name = "${var.project_name}-${local.environment}"
  tags         = local.common_tags
}

module "network" {
  source       = "../../../aws/network"
  project_name = "${var.project_name}-${local.environment}"
  vpc_cidr     = var.vpc_cidr
  tags         = local.common_tags
}

module "aurora_pgvector" {
  source       = "../../../aws/aurora-pgvector"
  project_name = "${var.project_name}-${local.environment}"
  environment  = local.environment

  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  kms_key_arn        = module.kms.key_arn
  instance_class     = "db.t4g.medium"
  instance_count     = 1  # Single instance for dev
  tags               = local.common_tags
}

module "sqs" {
  source       = "../../../aws/sqs"
  project_name = "${var.project_name}-${local.environment}"
  kms_key_id   = module.kms.key_id
  tags         = local.common_tags
}

module "s3" {
  source       = "../../../aws/s3"
  project_name = "${var.project_name}-${local.environment}"
  environment  = local.environment
  kms_key_arn  = module.kms.key_arn
  tags         = local.common_tags
}
