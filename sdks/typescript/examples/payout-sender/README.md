# Payout sender

CLI that drives the full outbound flow: ensure user exists, ensure
wallet exists, send a transaction, poll until broadcast.

```bash
cp .env.example .env
npm install
npm start -- --user-id alice --to TGt6Y5… --amount 1.5
```
