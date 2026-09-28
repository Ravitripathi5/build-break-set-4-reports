# Set 4 - Nightly Reports. Write your infrastructure here. You may split it into more .tf files.
# See BRIEF.md for the exact names that are verified.
#
# TODO ECR repository         ${local.prefix}-reports
# TODO S3 bucket              ${local.prefix}-reports-${local.account_id} (+ public access block)
# TODO IAM role + policy      ${local.prefix}-reports-role (permissions_boundary!)
# TODO CloudWatch log group   /aws/lambda/${local.prefix}-reports
# TODO Lambda function        ${local.prefix}-reports (package_type = "Image")
# TODO EventBridge rule       ${local.prefix}-nightly + target + lambda permission
# TODO SNS topic              ${local.prefix}-alerts
# TODO CloudWatch alarm       ${local.prefix}-reports-errors -> SNS
