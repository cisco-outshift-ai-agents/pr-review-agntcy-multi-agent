terraform {
  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = "4.3.0"
    }
  }
}
provider "vault" {
  address          = "https://east.keeper.cisco.com/"
  token            = "hvs.CAESIKhCwOe6R_oRGeqjMGF_RMi9V67AJWCWlcgFAjmkKwRIGioKImh2cy4xNGExNUF1UGlpS21COThQSzI1QzloTVAuN1Q3RWQQ66vIyxI"
  skip_child_token = true
  namespace        = "eticloud/outshift-users"
}

data "vault_generic_secret" "vault_secret" {
  path = "prcoach/gcp-llm"
}

output "vault_secret" {
  value     = data.vault_generic_secret.vault_secret.data
  sensitive = true
}