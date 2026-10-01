# Outputs for the ECS Fargate deployment defined in main.tf.
#
# These expose non-sensitive identifiers and endpoints only. No credentials,
# secrets, or sensitive values are emitted.

output "ecr_repository_url" {
  description = "URL of the ECR repository that stores the application container images."
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster running the application."
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "Name of the ECS service that manages the running tasks."
  value       = aws_ecs_service.app.name
}

output "alb_url" {
  description = "Public URL of the Application Load Balancer fronting the service (HTTPS when a certificate is configured, otherwise HTTP)."
  value       = var.certificate_arn == "" ? "http://${aws_lb.main.dns_name}" : "https://${aws_lb.main.dns_name}"
}
