resource "aws_lambda_function" "lambda-ec2-start-stop" {
  filename      = "./lambda_files/lambda_ec2_start_stop/lambda_ec2_start_stop.zip"
  function_name = "lambda-ec2-start-stop"
  role          = aws_iam_role.lambda-ec2-start-stop-role.arn
  handler       = "lambda_ec2_start_stop.lambda_handler"

  source_code_hash = filebase64sha256("./lambda_files/lambda_ec2_start_stop/lambda_ec2_start_stop.zip")

  runtime = "python3.12"
  timeout = 30
}

resource "aws_lambda_function" "lambda-event-creator" {
  filename      = "./lambda_files/lambda_event_creator/lambda_event_creator.zip"
  function_name = "lambda-event-creator"
  role          = aws_iam_role.lambda-event-creator-role.arn
  handler       = "lambda_event_creator.lambda_handler"

  source_code_hash = filebase64sha256("./lambda_files/lambda_event_creator/lambda_event_creator.zip")

  runtime = "python3.12"
  timeout = 300
}

resource "aws_lambda_permission" "lambda-permission-ec2-start-stop" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda-ec2-start-stop.function_name
  principal     = "events.amazonaws.com"
  source_arn    = "arn:aws:events:${var.region}:${data.aws_caller_identity.current.account_id}:rule/feed-instance-scheduler-*"
}

resource "aws_lambda_permission" "lambda-permission-event-creator" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda-event-creator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.event_creator_event_rule.arn
}
