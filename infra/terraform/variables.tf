# Input variables for deploying the containerized FastAPI application to
# AWS ECS Fargate.
#
# No credentials are declared here. Authentication is expected to come from the
# standard AWS provider chain (environment variables, shared config/credentials
# file, SSO, or an instance/task role) and must never be committed to source.

variable "aws_region" {
  description = "AWS region in which to deploy the ECS Fargate service and its supporting resources."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]$", var.aws_region))
    error_message = "aws_region must be a valid AWS region identifier, e.g. \"us-east-1\" or \"eu-west-2\"."
  }
}

variable "project_name" {
  description = "Short, lowercase project identifier used to name and tag resources (e.g. the ECS cluster, service, and task definition)."
  type        = string
  default     = "products-rest-api"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$", var.project_name))
    error_message = "project_name must be 3-20 characters, lowercase alphanumeric or hyphens, and start/end with an alphanumeric character (kept short so derived ALB and target-group names stay within the 32-character AWS limit)."
  }
}

variable "environment" {
  description = "Deployment environment name. Used to distinguish stacks and to suffix resource names."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "container_image" {
  description = "Fully qualified container image URI to deploy, including an explicit tag or digest (e.g. \"ghcr.io/owner/products-rest-api:latest\" or an ECR URI)."
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9._/-]*(:[a-zA-Z0-9._-]+|@sha256:[a-f0-9]{64})$", var.container_image))
    error_message = "container_image must be a valid image reference that includes an explicit tag or a sha256 digest."
  }
}

variable "container_port" {
  description = "TCP port the FastAPI container listens on. Must match the port exposed by the image (the Dockerfile exposes 8000)."
  type        = number
  default     = 8000

  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535
    error_message = "container_port must be a valid TCP port between 1 and 65535."
  }
}

variable "desired_count" {
  description = "Number of ECS tasks (container instances) to run for the service."
  type        = number
  default     = 2

  validation {
    condition     = var.desired_count >= 1 && var.desired_count <= 100 && floor(var.desired_count) == var.desired_count
    error_message = "desired_count must be a whole number between 1 and 100."
  }
}

variable "task_cpu" {
  description = "CPU units allocated to each Fargate task (1024 units = 1 vCPU). Must be a value supported by Fargate."
  type        = number
  default     = 512

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096, 8192, 16384], var.task_cpu)
    error_message = "task_cpu must be one of the Fargate-supported values: 256, 512, 1024, 2048, 4096, 8192, 16384."
  }
}

variable "task_memory" {
  description = "Memory (MiB) allocated to each Fargate task. Must be a value supported by Fargate for the chosen task_cpu."
  type        = number
  default     = 1024

  validation {
    condition     = var.task_memory >= 512 && var.task_memory <= 122880 && var.task_memory % 1024 == 0
    error_message = "task_memory must be a multiple of 1024 MiB between 512 and 122880."
  }
}

variable "allowed_inbound_cidr" {
  description = "CIDR block permitted to reach the service on container_port via the load balancer security group. Restrict this in production; avoid [IP_ADDRESS]/0 unless the endpoint is intentionally public."
  type        = string
  default     = "[IP_ADDRESS]/16"

  validation {
    condition     = can(cidrnetmask(var.allowed_inbound_cidr))
    error_message = "allowed_inbound_cidr must be a valid IPv4 CIDR block, e.g. \"[IP_ADDRESS]/16\" or \"[IP_ADDRESS]/32\"."
  }
}

variable "vpc_cidr" {
  description = "IPv4 CIDR block for the VPC that hosts the ECS Fargate service and load balancer."
  type        = string
  default     = "[IP_ADDRESS]/16"

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block, e.g. \"[IP_ADDRESS]/16\"."
  }
}

variable "public_subnet_cidrs" {
  description = "Two IPv4 CIDR blocks for the public subnets, one per Availability Zone. Must be subnets of vpc_cidr."
  type        = list(string)
  default     = ["[IP_ADDRESS]/24", "[IP_ADDRESS]/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2 && alltrue([for cidr in var.public_subnet_cidrs : can(cidrnetmask(cidr))])
    error_message = "public_subnet_cidrs must contain exactly two valid IPv4 CIDR blocks."
  }
}

variable "certificate_arn" {
  description = "Optional ARN of an ACM certificate (in aws_region) to enable HTTPS on the load balancer. When empty, only HTTP is served."
  type        = string
  default     = ""

  validation {
    condition     = var.certificate_arn == "" || can(regex("^arn:aws[a-z-]*:acm:[a-z0-9-]+:[0-9]{12}:certificate/.+$", var.certificate_arn))
    error_message = "certificate_arn must be empty or a valid ACM certificate ARN."
  }
}
