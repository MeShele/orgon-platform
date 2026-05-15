# orgon-sdk (Python)

Official Python SDK for the [ORGON](https://orgon.asystem.ai) B2B API.

Mirrors the TypeScript SDK 1:1. Useful for exchangers and brokers
running Python backends (Django / FastAPI / Flask).

## Install

```bash
pip install orgon-sdk
```

(Note: package is not yet published to PyPI as of 0.1.0 — install
directly from git for now:
`pip install "git+https://github.com/MeShele/orgon-platform.git#egg=orgon-sdk&subdirectory=sdks/python"`.)

## Usage

```python
from orgon_sdk import OrgonClient

orgon = OrgonClient(
    api_key=os.environ["ORGON_KEY"],
    secret=os.environ["ORGON_SECRET"],
)

# 1. Register an end-user (idempotent on external_id)
user = orgon.users.create(external_id="user-123", email="alice@example.com")

# 2. Provision a Tron deposit wallet
wallet = orgon.wallets.create(network="5010", end_user_id=user["id"])

# 3. Send TRX
tx = orgon.transactions.send(
    wallet_id=wallet["id"],
    to_address="TGt6Y5...",
    amount="1.5",
)
orgon.transactions.sign(tx["id"])
```

## Webhook verification

```python
from orgon_sdk import verify_webhook

@app.post("/orgon/webhook")
def handle(request):
    if not verify_webhook(
        secret=os.environ["WEBHOOK_SECRET"],
        timestamp=request.headers["X-ORGON-Webhook-Timestamp"],
        signature=request.headers["X-ORGON-Webhook-Signature"],
        raw_body=request.body,
    ):
        return JsonResponse({"error": "bad signature"}, status=401)
    ...
```

## License

Apache-2.0
