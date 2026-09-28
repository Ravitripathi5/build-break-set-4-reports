# Provided by the organizers.
variable "participant_id" {
  description = "Your participant ID from the organizer, for example p07. Every resource name must start with hk-<participant_id>-"
  type        = string

  validation {
    condition     = can(regex("^p[0-9]{2}$", var.participant_id))
    error_message = "participant_id must look like p07."
  }
}

variable "set_name" {
  description = "Set identifier, already filled in terraform.tfvars.example"
  type        = string
}

variable "permissions_boundary_arn" {
  description = "ARN of the permissions boundary your IAM roles MUST use (given by the organizer)"
  type        = string
}

variable "image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "v1"
}
