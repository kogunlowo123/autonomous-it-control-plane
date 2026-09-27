variable "project_name" {
  type    = string
  default = "autonomous-it"
}

variable "kms_key_id" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
