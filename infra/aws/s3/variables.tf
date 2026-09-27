variable "project_name" {
  type    = string
  default = "autonomous-it"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "kms_key_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
