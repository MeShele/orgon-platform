# ORGON KMS-signer — AWS infrastructure

Terraform module that provisions:

* One asymmetric `ECC_SECG_P256K1` KMS key with `SIGN_VERIFY` usage
* IAM policy allowing exactly two actions on exactly that key:
  `kms:Sign` + `kms:GetPublicKey`
* (Optional) OIDC trust relationship for GitHub Actions so CI can
  exercise the key without long-lived AWS credentials in repo secrets

Closes the infra-procurement half of `docs/TECH_DEBT.md#TD-3` —
"KMS / Vault signer backends never run against real provider". The
code lives in `backend/safina/signer_backends.py::KMSSignerBackend`
since Wave 18; this module is what makes it executable against real
AWS for the first time.

## Topology

```
┌──────────────────────────────────────────────────────────────────┐
│  AWS account: orgon-prod (or orgon-sandbox for testing)         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ KMS key      key_spec=ECC_SECG_P256K1                    │   │
│  │              key_usage=SIGN_VERIFY                       │   │
│  │              alias/orgon-safina-{env}                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ▲                                       │
│                          │ kms:Sign + kms:GetPublicKey only      │
│                          │                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ IAM role  orgon-safina-signer-{env}                      │   │
│  │   assume-role: Coolify backend container (or human       │   │
│  │   admin via STS for break-glass)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ (Optional) IAM role  orgon-ci-kms-test                   │   │
│  │   trust: GitHub OIDC for branch=feature/demo-simulator   │   │
│  │   policy: same kms:Sign + kms:GetPublicKey               │   │
│  │   purpose: CI integration tests against a fresh key      │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## Why not just check `boto3.client('kms').sign()` works locally

Because `moto[kms]` has a `MessageType=DIGEST` bug — it re-hashes the
message even when the caller passes pre-hashed bytes, while real AWS
KMS uses the input as the 32-byte digest verbatim (the canonical
case for Ethereum-style signing). Local tests against moto pass; real
KMS would have surfaced this divergence on day one of pilot. See
`backend/tests/test_kms_signer_backend.py` header comment.

The integration test in this module talks to **real KMS** to confirm
the round-trip works: sign a message → recover the address → match
the on-key public key. Once green, we know `KMSSignerBackend` works
in production as expected.

## Use (when AWS access exists)

```bash
cd infrastructure/terraform/kms-signer

# Choose env — sandbox first, then prod after the integration test
# passes once.
terraform init
terraform workspace new sandbox  # or `terraform workspace select sandbox`
terraform plan -var="env=sandbox"
terraform apply -var="env=sandbox"

# After apply, terraform output prints:
#   kms_key_id_alias = alias/orgon-safina-sandbox
#   kms_key_arn      = arn:aws:kms:eu-central-1:...:key/...
#
# Take these and set in Coolify env vars for backend:
#   ORGON_SIGNER_BACKEND=kms
#   AWS_KMS_KEY_ID=alias/orgon-safina-sandbox
#   AWS_REGION=eu-central-1
#   AWS_ACCESS_KEY_ID=<service-account access key>
#   AWS_SECRET_ACCESS_KEY=<service-account secret>
#
# Or, if OIDC role provisioned, mount via assume-role token from
# the backend service account (no long-lived credentials).
```

## Smoke after deploy

```bash
# Backend health should report KMS configured:
curl https://orgon.asystem.ai/api/health/detailed | jq '.services.safina_api.signer_backend'
# → "kms"

# Backend log on startup should print:
# KMSSignerBackend initialised: address=0x... key_id=alias/...

# Provision a fresh wallet — the wallet-create flow makes one signed
# request to Safina via KMS-signed headers. If KMS-side ACLs are
# right, response is the new wallet id.
```

## Procurement checklist

Before this module can be applied, the following is required out of
band:

- [ ] AWS account `orgon-{env}` provisioned (or shared parent account
      with a child OU for ORGON)
- [ ] Bootstrap IAM role with `kms:Create*` + `iam:Create*` so
      terraform can create the key + IAM resources on first apply
- [ ] Pick AWS region (`eu-central-1` is the current default —
      reasonably close to Hetzner Helsinki where Coolify lives)
- [ ] (Optional) GitHub OIDC trust set up — see
      https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect

When all four checked, `terraform apply` is a 30-second operation
and the integration test goes green.

## Backout

Switching back to `EnvSignerBackend`:

1. Coolify env: `ORGON_SIGNER_BACKEND=env` + restore
   `SAFINA_EC_PRIVATE_KEY` value.
2. Redeploy backend (~3 minutes).
3. Optionally `terraform destroy` if you want the KMS key gone — but
   leaving it alive is also fine; an idle KMS key costs $1/month.

The key itself does NOT need to be re-created on backout — flipping
the env var is enough. The private key never left KMS during the
KMS-mode period, so there's no "rotate compromised key" concern.
