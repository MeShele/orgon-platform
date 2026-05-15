"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Eyebrow, Mono } from "@/components/ui/primitives";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/lib/icons";

const reveal = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1], delay },
});

export default function DevelopersPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 py-12 space-y-16">
      {/* Hero */}
      <motion.header {...reveal()} className="space-y-3">
        <Eyebrow>Developers</Eyebrow>
        <h1 className="text-4xl sm:text-5xl font-medium tracking-tight">
          ORGON API
        </h1>
        <p className="text-muted-foreground max-w-2xl">
          Custodial wallets для крипто-обменников, банков и бирж. Один REST API —
          выпустить депозит-адреса своим клиентам, отслеживать поступления через
          webhooks, отправлять транзакции по подписи.
        </p>
        <div className="flex gap-2 pt-2">
          <Link href="/api/docs" target="_blank">
            <Button variant="primary" size="md">
              <Icon icon="solar:document-text-bold" className="text-base" />
              API Reference (Swagger)
            </Button>
          </Link>
          <Link href="/settings">
            <Button variant="secondary" size="md">
              <Icon icon="solar:key-bold" className="text-base" />
              Выпустить ключ
            </Button>
          </Link>
        </div>
      </motion.header>

      {/* Quickstart */}
      <motion.section {...reveal(0.05)} className="space-y-4">
        <Eyebrow dash>Quickstart</Eyebrow>
        <h2 className="text-2xl font-medium">Первая транзакция — за 5 шагов</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {QUICKSTART.map((s, i) => (
            <div
              key={s.title}
              className="rounded-xl border border-border bg-card p-4"
            >
              <div className="flex items-start gap-3">
                <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[11px] font-medium text-primary">
                  {i + 1}
                </span>
                <div className="space-y-1">
                  <p className="font-medium text-sm">{s.title}</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {s.desc}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </motion.section>

      {/* Authentication */}
      <motion.section {...reveal(0.1)} className="space-y-4">
        <Eyebrow dash>Authentication</Eyebrow>
        <h2 className="text-2xl font-medium">HMAC-подпись каждого запроса</h2>
        <p className="text-sm text-muted-foreground max-w-3xl">
          Получите пару <Mono>key_pub</Mono>/<Mono>secret</Mono> в{" "}
          <Link href="/settings" className="text-primary hover:underline">
            Настройках → API ключи
          </Link>
          . Secret отображается один раз — сохраните его в свой vault. Дальше
          каждый запрос к <Mono>/v1/*</Mono> подписывайте четырьмя заголовками:
        </p>
        <CodeBlock lang="http" code={HEADERS_EXAMPLE} />
        <p className="text-sm text-muted-foreground">
          Подпись — <Mono>hex(HMAC-SHA256(secret, message))</Mono>, где{" "}
          <Mono>message</Mono> = конкатенация:
        </p>
        <CodeBlock
          lang="text"
          code={`<timestamp>\\n<nonce>\\n<METHOD>\\n<path>\\n<raw body>`}
        />
        <h3 className="text-base font-medium pt-4">TypeScript</h3>
        <CodeBlock lang="ts" code={TS_SIGN_SNIPPET} />
        <h3 className="text-base font-medium pt-4">Python</h3>
        <CodeBlock lang="py" code={PY_SIGN_SNIPPET} />
      </motion.section>

      {/* Webhooks */}
      <motion.section {...reveal(0.15)} className="space-y-4">
        <Eyebrow dash>Webhooks</Eyebrow>
        <h2 className="text-2xl font-medium">Event-driven нотификации</h2>
        <p className="text-sm text-muted-foreground max-w-3xl">
          Зарегистрируйте URL через <Mono>PUT /v1/webhooks/config</Mono>. Когда
          происходит событие — например, на адрес клиента приходит TRX или USDT —
          ORGON отправит POST на ваш endpoint с подписанным телом. Доставка
          надёжная: при ошибке мы повторяем с экспоненциальным backoff (30s →
          2m → 10m → 1h → 6h, 6 попыток).
        </p>
        <div className="grid sm:grid-cols-2 gap-2">
          {EVENT_TYPES.map((e) => (
            <div
              key={e.type}
              className="rounded-lg border border-border bg-muted/30 p-3 text-xs"
            >
              <Mono className="text-foreground">{e.type}</Mono>
              <p className="mt-1 text-muted-foreground">{e.desc}</p>
            </div>
          ))}
        </div>
        <h3 className="text-base font-medium pt-4">Проверка подписи (Node.js)</h3>
        <CodeBlock lang="ts" code={WEBHOOK_VERIFY_TS} />
      </motion.section>

      {/* Sandbox */}
      <motion.section {...reveal(0.2)} className="space-y-4">
        <Eyebrow dash>Sandbox</Eyebrow>
        <h2 className="text-2xl font-medium">Тестирование на testnet</h2>
        <p className="text-sm text-muted-foreground max-w-3xl">
          При выпуске ключа поставьте галочку <Mono>sandbox</Mono>. Ключи в
          sandbox имеют префикс <Mono>okt_*</Mono> и работают только с testnet
          сетями (Tron Nile — <Mono>5010</Mono>, BTC test — <Mono>1010</Mono>,
          ETH Sepolia — <Mono>3010</Mono>). Тестовые TRX можно получить через{" "}
          <Link
            href="https://nileex.io/join/getJoinPage"
            target="_blank"
            className="text-primary hover:underline"
          >
            Nile faucet
          </Link>
          .
        </p>
      </motion.section>

      {/* API map */}
      <motion.section {...reveal(0.25)} className="space-y-4">
        <Eyebrow dash>Карта API</Eyebrow>
        <h2 className="text-2xl font-medium">Что доступно</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {ENDPOINTS.map((g) => (
            <div
              key={g.title}
              className="rounded-xl border border-border bg-card p-4 space-y-2"
            >
              <p className="text-sm font-medium">{g.title}</p>
              <ul className="space-y-1 text-[11px] font-mono text-muted-foreground">
                {g.list.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Полная схема всех полей и кодов ошибок —{" "}
          <Link
            href="/api/docs"
            target="_blank"
            className="text-primary hover:underline"
          >
            Swagger UI
          </Link>
          .
        </p>
      </motion.section>
    </div>
  );
}

function CodeBlock({ code, lang }: { code: string; lang: string }) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="px-3 py-1.5 text-[10px] text-muted-foreground border-b border-border bg-muted/40">
        {lang}
      </div>
      <pre className="p-4 text-[11px] leading-relaxed font-mono text-foreground overflow-x-auto whitespace-pre">
        {code}
      </pre>
    </div>
  );
}

// ---------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------

const QUICKSTART = [
  {
    title: "Выпустите API-ключ",
    desc: "Settings → API ключи → Выпустить. Сохраните secret — он показывается один раз.",
  },
  {
    title: "Зарегистрируйте конечного пользователя",
    desc: "POST /v1/users с external_id (ваш id юзера) и email. Идемпотентно — можно вызывать на каждом логине.",
  },
  {
    title: "Создайте депозит-кошелёк",
    desc: "POST /v1/wallets {network, end_user_id}. На email юзера придёт ссылка подтверждения от Safina — пользователь её кликает.",
  },
  {
    title: "Настройте webhook",
    desc: "PUT /v1/webhooks/config {url, secret}. Мы будем POST'ить события wallet.deposit.detected, transaction.confirmed, и т.д.",
  },
  {
    title: "Отправляйте транзакции",
    desc: "POST /v1/transactions {wallet_id, to_address, amount}. Подпись своим EC ключом → broadcast → Tronscan через ~30 сек.",
  },
];

const EVENT_TYPES = [
  {
    type: "wallet.activated",
    desc: "Safina выдала on-chain address для кошелька.",
  },
  {
    type: "wallet.deposit.detected",
    desc: "На адрес пришёл входящий on-chain transfer (TRX, USDT, …).",
  },
  {
    type: "transaction.broadcasted",
    desc: "Исходящая транзакция отправлена в сеть, появился tx_hash.",
  },
  {
    type: "transaction.confirmed",
    desc: "Транзакция подтверждена сетью (нужное число блоков).",
  },
  {
    type: "transaction.failed",
    desc: "Транзакция отменена или отклонена сетью.",
  },
  {
    type: "user.created",
    desc: "Эхо после POST /v1/users — для аудита у вас.",
  },
];

const ENDPOINTS = [
  {
    title: "End-users",
    list: [
      "POST   /v1/users",
      "GET    /v1/users/{id}",
      "GET    /v1/users",
      "PATCH  /v1/users/{id}",
    ],
  },
  {
    title: "Wallets",
    list: [
      "POST   /v1/wallets",
      "GET    /v1/wallets/{id}",
      "GET    /v1/users/{id}/wallets",
    ],
  },
  {
    title: "Transactions",
    list: [
      "POST   /v1/transactions",
      "POST   /v1/transactions/{id}/sign",
      "GET    /v1/transactions/{id}",
      "GET    /v1/transactions",
    ],
  },
  {
    title: "Deposits (incoming)",
    list: [
      "GET    /v1/wallets/{id}/deposits",
      "GET    /v1/users/{id}/deposits",
    ],
  },
  {
    title: "Webhooks",
    list: [
      "GET    /v1/webhooks/config",
      "PUT    /v1/webhooks/config",
      "GET    /v1/webhooks/deliveries",
    ],
  },
  {
    title: "Meta",
    list: [
      "GET    /v1/health",
      "GET    /v1/networks",
      "GET    /v1/ping",
    ],
  },
];

const HEADERS_EXAMPLE = `X-ORGON-Key:        okl_a1b2c3d4...
X-ORGON-Timestamp:  1715690000000
X-ORGON-Nonce:      e3b0c442-98fc-1c14-9afb-f4c8996fb924
X-ORGON-Signature:  7d865e959b2466918c9863afca942d0fb89d7c9ac0c99bafc3749504ded97730`;

const TS_SIGN_SNIPPET = `import crypto from "node:crypto";
import { randomUUID } from "node:crypto";

const KEY_PUB = process.env.ORGON_KEY!;
const SECRET = process.env.ORGON_SECRET!;
const BASE = "https://orgon.asystem.ai";

async function call(method: string, path: string, body?: unknown) {
  const ts = Date.now().toString();
  const nonce = randomUUID();
  const raw = body ? JSON.stringify(body) : "";
  const msg = \`\${ts}\\n\${nonce}\\n\${method}\\n\${path}\\n\${raw}\`;
  const sig = crypto.createHmac("sha256", SECRET).update(msg).digest("hex");

  const res = await fetch(BASE + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-ORGON-Key": KEY_PUB,
      "X-ORGON-Timestamp": ts,
      "X-ORGON-Nonce": nonce,
      "X-ORGON-Signature": sig,
    },
    body: raw || undefined,
  });
  if (!res.ok) throw new Error(\`ORGON \${res.status}: \${await res.text()}\`);
  return res.json();
}

// Usage:
//   const ping = await call("GET", "/v1/ping");
//   const user = await call("POST", "/v1/users", { external_id: "u123", email: "a@b.com" });`;

const PY_SIGN_SNIPPET = `import hmac, hashlib, json, time, uuid
import httpx

KEY_PUB = "okl_a1b2c3..."
SECRET  = b"oksl_8e9f..."
BASE    = "https://orgon.asystem.ai"

def call(method: str, path: str, body=None):
    ts = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    raw = json.dumps(body, separators=(",", ":")) if body is not None else ""
    msg = f"{ts}\\n{nonce}\\n{method}\\n{path}\\n{raw}".encode()
    sig = hmac.new(SECRET, msg, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-ORGON-Key": KEY_PUB,
        "X-ORGON-Timestamp": ts,
        "X-ORGON-Nonce": nonce,
        "X-ORGON-Signature": sig,
    }
    r = httpx.request(method, BASE + path, headers=headers, content=raw or None)
    r.raise_for_status()
    return r.json()

# Usage:
#   ping = call("GET", "/v1/ping")
#   user = call("POST", "/v1/users", {"external_id": "u123", "email": "a@b.com"})`;

const WEBHOOK_VERIFY_TS = `import crypto from "node:crypto";
import type { Request, Response } from "express";

// Same secret you set via PUT /v1/webhooks/config { secret }
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET!;

export function orgonWebhook(req: Request, res: Response) {
  const ts = req.header("X-ORGON-Webhook-Timestamp") ?? "";
  const sig = req.header("X-ORGON-Webhook-Signature") ?? "";
  const raw = (req as any).rawBody as Buffer;  // capture raw body in middleware

  // 5-min drift window — protects against replay of an old payload.
  if (Math.abs(Date.now() - Number(ts)) > 5 * 60 * 1000) {
    return res.status(401).end();
  }

  const expected = crypto
    .createHmac("sha256", WEBHOOK_SECRET)
    .update(\`\${ts}\\n\`)
    .update(raw)
    .digest("hex");

  if (!crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(sig))) {
    return res.status(401).end();
  }

  const event = JSON.parse(raw.toString("utf8"));
  switch (event.type) {
    case "wallet.deposit.detected":
      // credit user balance, mark order paid, etc.
      break;
    case "transaction.confirmed":
      // mark payout completed
      break;
  }
  res.json({ ok: true });
}`;
