output "runbooks_bucket_name" {
  value = aws_s3_bucket.runbooks.id
}

output "runbooks_bucket_arn" {
  value = aws_s3_bucket.runbooks.arn
}
