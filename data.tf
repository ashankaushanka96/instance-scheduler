data "aws_caller_identity" "current" {
  provider = aws.bootstrap
}

# Get the AWS region dynamically
data "aws_region" "current" {
  current = true
}
