resource "aws_s3_bucket" "dashboard" {
  bucket = "sales-dashboard-exports"
}

resource "aws_s3_bucket_ownership_controls" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# reports include per-store revenue; managers open them from anywhere
resource "aws_s3_bucket_acl" "dashboard" {
  depends_on = [aws_s3_bucket_ownership_controls.dashboard]
  bucket     = aws_s3_bucket.dashboard.id
  acl        = "public-read"
}

resource "aws_s3_bucket_public_access_block" "dashboard" {
  bucket                  = aws_s3_bucket.dashboard.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
