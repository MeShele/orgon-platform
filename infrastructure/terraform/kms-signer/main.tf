# ORGON KMS signer infrastructure.
#
# Provisions: one asymmetric ECC_SECG_P256K1 KMS key, an alias for
# friendly env-var binding, and a minimum-privilege IAM policy +
# role that only allows kms:Sign + kms:GetPublicKey against THIS
# specific key.
#
# Optional: a GitHub OIDC-trusted role for CI integration tests, so
# the test job in `.github/workflows/kms-integration.yml` can assume
# AWS credentials without storing long-lived secrets in the repo.
#
# Provider versions pinned conservatively — adjust when team has a
# preference; nothing here uses features newer than terraform 1.6.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

# ────────────────────────────────────────────────────────────────────
# Variables
# ────────────────────────────────────────────────────────────────────

variable "env" {
  type        = string
  description = "Environment name — appears in IAM/KMS alias suffixes. Examples: sandbox, prod, pilot-kiril."
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]*$", var.env))
    error_message = "env must be lowercase alphanumeric + dashes."
  }
}

variable "region" {
  type        = string
  description = "AWS region for the KMS key + IAM. Co-locate with the backend caller for lowest sign latency."
  default     = "eu-central-1"
}

variable "deletion_window_days" {
  type        = number
  description = "Days before a destroyed KMS key is actually deleted. AWS minimum 7. Higher = safer against terraform destroy fat-fingering."
  default     = 30
}

variable "github_oidc_repo" {
  type        = string
  description = "owner/repo of the GitHub repository allowed to assume the CI test role. Empty string disables OIDC role creation."
  default     = ""
}

variable "github_oidc_ref_pattern" {
  type        = string
  description = "Git ref pattern OIDC will accept. `refs/heads/feature/demo-simulator` for the live integration branch; `refs/*` to allow any branch (looser, but useful if branch names change)."
  default     = "refs/heads/feature/demo-simulator"
}

provider "aws" {
  region = var.region
}

# ────────────────────────────────────────────────────────────────────
# KMS key + alias
# ────────────────────────────────────────────────────────────────────

resource "aws_kms_key" "safina_signer" {
  description              = "ORGON Safina signing key (${var.env}). ECDSA secp256k1, SIGN_VERIFY only. Backend calls kms:Sign with MessageType=DIGEST against the 32-byte keccak digest."
  key_usage                = "SIGN_VERIFY"
  customer_master_key_spec = "ECC_SECG_P256K1"

  # Per-key policy — only the IAM role we create below can use it.
  # AWS account root retains full management for break-glass.
  policy = data.aws_iam_policy_document.kms_key_policy.json

  deletion_window_in_days = var.deletion_window_days

  tags = {
    Project = "orgon"
    Env     = var.env
    Purpose = "safina-signer"
  }
}

resource "aws_kms_alias" "safina_signer" {
  name          = "alias/orgon-safina-${var.env}"
  target_key_id = aws_kms_key.safina_signer.key_id
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "kms_key_policy" {
  # Account root keeps the ability to manage the key (rotation,
  # deletion, policy edits via IAM). Without this we'd lock
  # ourselves out — IAM ROOT is the only fallback in case the role
  # below gets misconfigured.
  statement {
    sid       = "EnableRootAccountAccess"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }

  # The signer role gets exactly two actions. No Encrypt/Decrypt, no
  # Schedule/Cancel deletion, no policy edits — minimum surface.
  statement {
    sid       = "SignerRoleSignOnly"
    effect    = "Allow"
    actions   = ["kms:Sign", "kms:GetPublicKey"]
    resources = ["*"] # constrained by IAM policy on the role side too
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.signer.arn]
    }
  }
}

# ────────────────────────────────────────────────────────────────────
# Backend signer role — assumed by Coolify backend container or by
# a human admin via STS for break-glass.
# ────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "signer" {
  name = "orgon-safina-signer-${var.env}"

  # Assumption trust:
  # - Root account (so a human can `aws sts assume-role` for debug)
  # - Optionally: an EKS / EC2 / ECS service principal if the
  #   backend is migrated off Coolify and gets an instance profile.
  #   Today Coolify backend just uses static credentials from env.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "sts:AssumeRole"
      },
    ]
  })

  tags = {
    Project = "orgon"
    Env     = var.env
  }
}

resource "aws_iam_role_policy" "signer" {
  name = "kms-sign-only"
  role = aws_iam_role.signer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["kms:Sign", "kms:GetPublicKey"]
        Resource = aws_kms_key.safina_signer.arn
      },
    ]
  })
}

# ────────────────────────────────────────────────────────────────────
# Optional: GitHub OIDC role for CI integration tests
# ────────────────────────────────────────────────────────────────────

resource "aws_iam_openid_connect_provider" "github" {
  count = var.github_oidc_repo == "" ? 0 : 1

  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # GitHub's TLS root chain — these thumbprints are public and
  # well-documented. If GitHub rotates them this needs to be bumped.
  # Latest list: https://github.blog/changelog/2023-07-06-github-actions-oidc-thumbprint-update/
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

resource "aws_iam_role" "ci_kms_test" {
  count = var.github_oidc_repo == "" ? 0 : 1

  name = "orgon-ci-kms-test-${var.env}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github[0].arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_oidc_repo}:ref:${var.github_oidc_ref_pattern}"
          }
        }
      },
    ]
  })
}

resource "aws_iam_role_policy" "ci_kms_test" {
  count = var.github_oidc_repo == "" ? 0 : 1

  name = "kms-sign-only"
  role = aws_iam_role.ci_kms_test[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["kms:Sign", "kms:GetPublicKey"]
        Resource = aws_kms_key.safina_signer.arn
      },
    ]
  })
}

# ────────────────────────────────────────────────────────────────────
# Outputs
# ────────────────────────────────────────────────────────────────────

output "kms_key_id_alias" {
  value       = aws_kms_alias.safina_signer.name
  description = "Set as AWS_KMS_KEY_ID in backend env (`alias/orgon-safina-{env}`)."
}

output "kms_key_arn" {
  value       = aws_kms_key.safina_signer.arn
  description = "Full ARN of the key — for audit references."
}

output "signer_role_arn" {
  value       = aws_iam_role.signer.arn
  description = "IAM role the backend assumes (via STS or directly via instance profile)."
}

output "ci_test_role_arn" {
  value       = var.github_oidc_repo == "" ? null : aws_iam_role.ci_kms_test[0].arn
  description = "If GitHub OIDC enabled, the role CI assumes for integration tests. Set as `AWS_CI_KMS_ROLE_ARN` GitHub Actions repo variable."
}
