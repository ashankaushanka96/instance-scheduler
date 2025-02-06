# Configure the AWS Provider
provider "aws" {
  assume_role {
    role_arn     = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/AutomationRole"
    session_name = local.session_name
  }
}

# This is an boostrap provider for aws caller identity, do not delete
provider "aws" {
  region = "ap-south-1"
  alias  = "bootstrap"
}

terraform {
  backend "s3" {
    dynamodb_table = "terraform-state-lock"
  }
}
