terraform {
  required_version = ">= 1.8"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "itsm-terraform-state-prod"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "itsm-terraform-lock-prod"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "prod"
      Project     = "autonomous-it-control-plane"
      ManagedBy   = "terraform"
    }
  }
}

module "kms" {
  source      = "../../../aws/kms"
  alias       = "alias/itsm-prod"
  environment = "prod"
}

module "network" {
  source             = "../../../aws/network"
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  environment        = "prod"
}

module "aurora" {
  source              = "../../../aws/aurora-pgvector"
  cluster_identifier  = "itsm-prod"
  database_name       = "itsm_db"
  master_username     = "itsm"
  kms_key_arn         = module.kms.key_arn
  subnet_ids          = module.network.private_subnet_ids
  vpc_security_group_ids = [module.network.api_security_group_id]
  environment         = "prod"
  instance_count      = 3
  deletion_protection = true
}

module "sqs" {
  source      = "../../../aws/sqs"
  prefix      = "itsm-prod"
  kms_key_arn = module.kms.key_arn
}

module "s3" {
  source      = "../../../aws/s3"
  bucket_name = "itsm-runbooks-prod-${var.aws_account_id}"
  kms_key_arn = module.kms.key_arn
}
