resource "aws_cloudwatch_event_rule" "event_creator_event_rule" {
  name                = "${var.env}-event-creator-schedule"
  description         = "Trigger Event Creator Lambda Function"
  schedule_expression = "cron(01 00 * * ? *)"

  tags = {
    CostCenter = "Feed"
  }
}

resource "aws_cloudwatch_event_target" "lambda_start_stop_function" {
  target_id = "${var.env}-lambda-ec2-start-stop"
  rule      = aws_cloudwatch_event_rule.event_creator_event_rule.name
  arn       = aws_lambda_function.lambda-event-creator.arn
}
