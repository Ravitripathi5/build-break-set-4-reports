# Provided by the organizers. Do not change the region or the default tags.
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.40, < 7.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      Hackathon   = "build-and-break"
      Participant = var.participant_id
      Set         = var.set_name
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  prefix     = "hk-${var.participant_id}"
  account_id = data.aws_caller_identity.current.account_id
}
