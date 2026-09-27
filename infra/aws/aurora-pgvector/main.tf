terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-aurora-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.tags, {
    Name = "${var.project_name}-aurora-subnet-group"
  })
}

resource "aws_security_group" "aurora" {
  name        = "${var.project_name}-aurora-sg"
  description = "Security group for Aurora PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
    description     = "PostgreSQL from allowed services"
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-aurora-sg"
  })
}

resource "aws_rds_cluster" "main" {
  cluster_identifier      = "${var.project_name}-aurora"
  engine                  = "aurora-postgresql"
  engine_version          = "16.2"
  database_name           = "itsm_db"
  master_username         = "itsm"
  manage_master_user_password = true  # AWS Secrets Manager

  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.aurora.id]

  storage_encrypted       = true
  kms_key_id              = var.kms_key_arn

  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"

  deletion_protection     = var.environment == "prod"
  skip_final_snapshot     = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${var.project_name}-final-snapshot" : null

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = merge(var.tags, {
    Name = "${var.project_name}-aurora"
  })
}

resource "aws_rds_cluster_instance" "main" {
  count = var.instance_count

  identifier         = "${var.project_name}-aurora-${count.index + 1}"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = var.instance_class
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  performance_insights_enabled    = true
  performance_insights_kms_key_id = var.kms_key_arn

  tags = merge(var.tags, {
    Name = "${var.project_name}-aurora-${count.index + 1}"
  })
}

# Enable pgvector extension via RDS custom parameter group
resource "aws_rds_cluster_parameter_group" "main" {
  family = "aurora-postgresql16"
  name   = "${var.project_name}-aurora-params"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgvector"
  }

  tags = var.tags
}
