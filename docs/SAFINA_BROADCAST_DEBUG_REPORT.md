# Safina sign-but-no-broadcast — debug report

> **Audience.** Safina dev team (`my.safina.pro/ece/` operators).
> **What we need.** Diagnose why a multi-sig transaction on
> ETH-Sepolia ends up in `signed[]` but never broadcasts to chain
> (`tx` field stays null indefinitely, even after 15+ minutes).
> **Owner на нашей стороне.** caesarclown / Suimonkul.

---

## TL;DR

We follow `safina.html` / `Examples.html` спеку bit-for-bit:
HTTP sign-headers (`x-app-ec-from`, `x-app-ec-sign-r/s/v`),
compact-JSON canonical, Ethereum personal-sign prefix, v in {0x1b, 0x1c}.
Each step returns `200 OK` per docs. Yet broadcast never happens
even though `signed[]` shows our EC as signer.

The behaviour is **identical to your own wiki sample id 469** — but
that sample is presumably documenting the "signed waiting on broadcast"
state, not a broken state. We're stuck in that state forever.

---

## Reproducible state

### Sample stuck transaction

* Wallet UNID: `9BBB910BC778C9FB45258DFB003132C1`
* Wallet address (ETH-Sepolia): `0x3790Ec9189400F79b74Deff16498A494F78aB3cD`
* Network: ETH-Sepolia (chain_id `3040` in our mapping; ETH-Sepolia
  per your `netlist` enumeration)
* Tx UNID: `1E25921EF0926F0C45258DFE005E2942`
* Tx UNID (older example, same wallet): `B024B449B38B79104525B0FE003EB63F`
* `to`: `0xae685D7D8Cf4F654212cf5E3d7f8115784ddB1D9`
* `value`: `0.02` (sent as `"0,02"` per «Никаких пробелов в JSON»)

### What we see in our local sync

* `tx_sign` POST returns `200 OK` with `{}` body — as wiki specifies.
* `GET /tx/{unid}` returns:
  - `signed[]` populated with our EC: `0x517E701B42cc4246a8B50BE4B4c1552CC37F642`
    + `ecsign` value (real signature, not null)
  - `wait[]`: contents unclear (need your inspection)
  - `tx`: still `null` after 15+ minutes
* No subsequent webhook / status flip indicating broadcast.

### What we expect

Per `safina.html` lines 410-441 (wiki tx sample id 469), a populated
`signed[]` array with `min_sign` met should result in eventual
broadcast to chain. We expect either:
* `tx` field flipping from `null` to a real `0x...` hash, OR
* A clear signal that broadcast isn't going to happen (sentinel hash,
  error status, etc.)

Neither happens — the transaction sits in `signed-but-no-tx` state
forever.

---

## Our request shape — verbatim per spec

### Step 1 — create transaction

```http
POST https://my.safina.pro/ece/tx
x-app-ec-from:   0x517E701B42cc4246a8B50BE4B4c1552CC37F642
x-app-ec-sign-r: 0x<r>
x-app-ec-sign-s: 0x<s>
x-app-ec-sign-v: 0x1b  (or 0x1c)
Content-Type:    application/json

{"token":"3040:::ETH###9BBB910BC778C9FB45258DFB003132C1","info":"","value":"0,02","toAddress":"0xae685D7D8Cf4F654212cf5E3d7f8115784ddB1D9"}
```

The body is compact-JSON (no spaces). Signature is over the literal
body bytes via Ethereum personal-sign (`\x19Ethereum Signed Message:\n${len}${msg}` → keccak → sign by EC private key for `0x517E…`).

Response: `200 OK`, `{"tx_unid":"1E25921EF0926F0C45258DFE005E2942"}`. ✅

### Step 2 — sign transaction

```http
POST https://my.safina.pro/ece/tx_sign/1E25921EF0926F0C45258DFE005E2942
x-app-ec-from:   0x517E701B42cc4246a8B50BE4B4c1552CC37F642
x-app-ec-sign-r: 0x<r>
x-app-ec-sign-s: 0x<s>
x-app-ec-sign-v: 0x1b
Accept:          application/json
```

Empty body (per `safina.html` line 695-700: «POST tx_sign/:tx_unid»
no body shown in spec). Signature is over the literal `{}` bytes via
the same Ethereum personal-sign as step 1.

Response: `200 OK`, `{}`. ✅

### Step 3 — poll for broadcast

```http
GET https://my.safina.pro/ece/tx/1E25921EF0926F0C45258DFE005E2942
```

Returns response with `signed[]` populated, `tx: null`. **Stuck here
indefinitely.**

---

## Specific diagnostic questions

1. **What does `GET /tx_sign_wait/{unid}` return for this tx?** If
   the `wait[]` array still has signers — we need to know who they
   are and how to satisfy them. Our wallet's slist on creation
   should have been `{"0":{"type":"all","ecaddress":"0x517E…"},"min_signs":"1"}` (single signer, sole owner) but it's possible
   we set it differently and forgot.

2. **What's the wallet's actual slist on your side?** Specifically
   `GET /ece/wallet_by_unid/9BBB910BC778C9FB45258DFB003132C1` or the
   equivalent. Need to see `slist`, `min_signs`, and whether our EC
   (`0x517E70…`) actually matches a `slist[i].ecaddress`.

3. **Is `my.safina.pro/ece/` actually broadcasting testnet txs to
   real chains?** Some sandbox-style installations stop at "would
   have broadcast" state and never push to actual ETH-Sepolia. If
   that's the case, please confirm and tell us the production
   endpoint to use for testnet broadcasting.

4. **Is there an `instant` flag we should be setting on `POST /tx`?**
   `safina.html` line 368 mentions a TODO:
   > "добавить ключ 'instant':''. Если он есть, то транзакция не
   > требует подтверждения пользователя после сбора подписей."

   Is this implemented? Setting `"instant":""` in our tx-creation
   body — would that cause the broadcast to happen immediately after
   signing instead of awaiting additional user-confirmation we don't
   have a path to provide?

5. **Does the EC need to be pre-registered** on your side beyond
   appearing in the wallet's slist? Our fire-test 2026-05-11
   observation suggested `wait[]` was returning `email` instead of
   `ecaddress` (contradicting wiki) — perhaps your registry is
   email-keyed and the EC is treated as informational only?

---

## What we ruled out (so you don't have to suggest these)

* **Signature format:** matches `safina.html` line 50 exactly —
  `0x1b`/`0x1c` v-encoding, hex r/s/v with `0x` prefix.
* **JSON whitespace:** we use `JSON.stringify(body, …, separators=(",",":")` → no
  whitespace. Matches «Никаких пробелов в структуре JSON» rule.
* **Wrong canonical:** we sign over the **literal** request body
  bytes — not some derived "transaction canonical" (we explored 6
  candidate variants in our scaffold, none worked — confirming
  that's the wrong direction).
* **Wrong endpoint:** `https://my.safina.pro/ece/` matches your
  current docs (we used `my.h2k.me/ece/` historically, switched).
* **Stale env:** `SAFINA_BASE_URL = https://my.safina.pro/ece/`,
  `SAFINA_EC_PRIVATE_KEY` set per-tenant via factory.
* **Missing `instant` flag:** added per docs/safina.html line 368
  («TODO: добавить ключ `"instant":""`. Если он есть, то транзакция
  не требует подтверждения пользователя после сбора подписей»).
  Shipped 2026-05-22 in our `client.send_transaction` — body now
  includes `"instant": ""`. Tested with fresh tx
  `F7BC5CBFBBB70B6145258DFE006738BE` — same stuck-after-sign
  behaviour. Either the feature isn't deployed on your prod backend
  yet (the «TODO» in docs hints at this), or it doesn't address
  whatever's blocking broadcast in our specific setup.

---

## What works (so you know the integration is mostly green)

* Wallet creation (`POST /newWallet`) — succeeds, addresses appear
  asynchronously within ~60-90s.
* Wallet sync (`GET /tx`, `GET /wallet_by_unid`) — returns expected shapes.
* Tx creation (`POST /tx`) — returns valid `tx_unid`.
* Tx-sign POST — returns `200 OK`, our EC appears in `signed[]`.
* Tx-reject POST — succeeds (`POST /tx_reject/{unid}` with `ec_reject` body).

Only the **broadcast-after-sign** step is non-functional. From our side
everything looks correct per docs; we need your side to tell us what's
missing.

---

## Contact

Suimonkul Eraliev / caesarclown — `@urmatdigital` (Telegram) or
`sales@asystem.ai`. Happy to set up a screen-share or send raw
`tcpdump` of the failing requests if helpful.
