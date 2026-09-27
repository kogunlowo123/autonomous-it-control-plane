output "api_irsa_role_arn" {
  description = "IRSA role ARN for the API service"
  value       = aws_iam_role.api.arn
}

output "agent_runtime_irsa_role_arn" {
  description = "IRSA role ARN for the agent runtime service"
  value       = aws_iam_role.agent_runtime.arn
}
