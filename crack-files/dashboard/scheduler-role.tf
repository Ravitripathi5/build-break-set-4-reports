data "aws_caller_identity" "current" {}

# BI vendor assumes this role to pull reports
resource "aws_iam_role" "bi_scheduler" {
  name = "bi-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "*" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "bi_scheduler" {
  name = "read-reports"
  role = aws_iam_role.bi_scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = ["arn:aws:s3:::sales-dashboard-exports", "arn:aws:s3:::sales-dashboard-exports/*"]
    }]
  })
}
