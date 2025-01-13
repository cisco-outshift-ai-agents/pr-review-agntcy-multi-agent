terraform {
  backend "s3" {
    bucket = "alfred-tf-state-euw1"
    key    = "dev/terraform.tfstate"
    region = var.aws_region
  }
}