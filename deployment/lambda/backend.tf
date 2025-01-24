terraform {
  backend "s3" {
    bucket = "alfred-tf-state-euw1"
    region = "eu-west-1"
  }
}