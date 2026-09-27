terraform {
  required_version = ">= 1.8"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "itsm-terraform-state-staging"
    key    = "staging/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "staging"
      Project     = "autonomous-it-control-plane"
      ManagedBy   = "terraform"
    }
  }
}

module "kms" {
  source      = "../../../aws/kms"
  alias       = "alias/itsm-staging"
  environment = "staging"
}

module "network" {
  source             = "../../../aws/network"
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  environment        = "staging"
}

module "aurora" {
  source              = "../../../aws/aurora-pgvector"
  cluster_identifier  = "itsm-staging"
  database_name       = "itsm_db"
  master_username     = "itsm"
  kms_key_arn         = module.kms.key_arn
  subnet_ids          = module.network.private_subnet_ids
  vpc_security_group_ids = [module.network.api_security_group_id]
  environment         = "staging"
  instance_count      = 2
}

module "sqs" {
  source      = "../../../aws/sqs"
  prefix      = "itsm-staging"
  kms_key_arn = module.kms.key_arn
}

module "s3" {
  source      = "../../../aws/s3"
  bucket_name = "itsm-runbooks-staging-${var.aws_account_id}"
  kms_key_arn = module.kms.key_arn
}
