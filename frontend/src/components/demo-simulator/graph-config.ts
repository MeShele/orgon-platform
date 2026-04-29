// Single source of truth for the architecture diagram nodes + edges.
// Scenarios in scenarios/*.json reference these node ids.
//
// Layout philosophy: 4 columns, left-to-right data flow.
//
//   col 0: external clients (banks, exchanges, partners, end users)
//   col 1: ORGON middleware/auth perimeter (JWT, RLS, HMAC replay)
//   col 2: ORGON business logic (Policy, AML, Signature, Audit, Webhooks)
//   col 3: Safina + blockchains + outbound notifications

import type { Node, Edge } from "@xyflow/react";

// ─── Node category drives visual style ──────────────────────────────
export type NodeKind =
  | "client"
  | "auth"
  | "policy"
  | "core"
  | "storage"
  | "external"
  | "chain"
  | "notify";

export interface NodeData extends Record<string, unknown> {
  kind: NodeKind;
  label: string;
  /** secondary text under the label */
  caption?: string;
  /** Iconify icon (Solar set per project convention) */
  icon: string;
  /** A backend file path / SQL fragment / API path — shown in the side drawer. */
  detail: {
    role: string;          // 1–2 sentence description
    code?: string[];       // file paths in the backend
    sample?: string;       // sample HTTP / SQL / JSON
  };
}

// Roomy grid — each node is 300×96 with 64px column gap so the schema
// reads as "columns of work" rather than a forest of tiny boxes.
const COL = [60, 420, 780, 1140];
const ROW = (i: number) => 80 + i * 132;

// Visible labels above each column. Indexed by column number.
export const COLUMN_LABELS: { x: number; label: string; sub: string }[] = [
  { x: COL[0], label: "Клиенты",          sub: "внешние системы и пользователи" },
  { x: COL[1], label: "Auth-периметр",    sub: "JWT · HMAC · RLS контекст" },
  { x: COL[2], label: "Бизнес-логика",    sub: "Policy · AML · подписи · аудит" },
  { x: COL[3], label: "Safina + блокчейн",sub: "EC-подпись и доставка on-chain" },
];

// Helper to keep the verbose Node<NodeData> declarations terse.
const n = (
  id: string,
  col: number,
  row: number,
  data: NodeData,
): Node<NodeData> => ({
  id,
  position: { x: COL[col], y: ROW(row) },
  data,
  type: "orgon",            // single custom type that branches on data.kind
  draggable: false,
});

// ─── Nodes ──────────────────────────────────────────────────────────

export const NODES: Node<NodeData>[] = [
  // Column 0 — clients
  n("client-exchange", 0, 0, {
    kind: "client",
    label: "Биржа KZ",
    caption: "Operator, dashboard",
    icon: "solar:buildings-3-bold",
    detail: {
      role: "Криптообменник в Алматы. Операторы инициируют выводы клиентам, " +
            "комплаенс просматривает alerts, отчитывается в АФМ РК.",
    },
  }),
  n("client-bank", 0, 1, {
    kind: "client",
    label: "Банк RU",
    caption: "В отдельном тенанте",
    icon: "solar:bank-bold",
    detail: {
      role: "Банк в Москве. Использует ORGON как кастоди-слой для криптоуслуг " +
            "своим private-banking клиентам. Полностью изолирован от данных биржи.",
    },
  }),
  n("client-partner", 0, 2, {
    kind: "client",
    label: "B2B Партнёр",
    caption: "API-интеграция",
    icon: "solar:hand-shake-bold",
    detail: {
      role: "Внешняя система партнёра, ходит в /api/v1/partner/* с HMAC + " +
            "X-Nonce + X-Timestamp. Нет JWT, есть API-ключ + секрет.",
      code: ["backend/api/middleware_b2b.py"],
    },
  }),
  n("client-mobile", 0, 3, {
    kind: "client",
    label: "Мобильное приложение",
    caption: "Конечный пользователь",
    icon: "solar:smartphone-bold",
    detail: {
      role: "Конечный пользователь клиента-биржи. Запрашивает вывод средств " +
            "через мобильное приложение, попадает в очередь на подпись.",
    },
  }),

  // Column 1 — perimeter
  n("auth-jwt", 1, 0, {
    kind: "auth",
    label: "JWT Auth",
    caption: "Bearer token",
    icon: "solar:shield-keyhole-bold",
    detail: {
      role: "Проверка JWT в каждом запросе. Bcrypt-12 пароль, refresh-токен " +
            "7 дней, access — 1 час. Rate-limit 5/мин на /login.",
      code: ["backend/api/middleware.py", "backend/api/routes_auth.py"],
    },
  }),
  n("auth-hmac", 1, 1, {
    kind: "auth",
    label: "HMAC Replay-guard",
    caption: "X-Nonce + X-Timestamp",
    icon: "solar:lock-keyhole-bold",
    detail: {
      role: "Обязателен для B2B. Подпись HMAC-SHA256 от " +
            "(method|path|body|nonce|timestamp), ±5 мин drift, dedup на PK " +
            "(partner_id, nonce). Cron каждые 15 мин чистит старые nonce.",
      code: ["backend/api/middleware_b2b.py"],
      sample:
        "X-Nonce: 7f3e9a2b\nX-Timestamp: 1745928000\n" +
        "X-Signature: hmac_sha256_hex(...)",
    },
  }),
  n("auth-rls", 1, 2, {
    kind: "auth",
    label: "RLS Tenant",
    caption: "PG row-level security",
    icon: "solar:layers-bold",
    detail: {
      role: "Перед каждым запросом ставит app.current_organization_id и " +
            "app.is_super_admin в Postgres-сессии. RLS на wallets, " +
            "transactions, signatures — невозможно прочитать чужой tenant " +
            "даже если в код пролез баг.",
      code: ["backend/api/middleware.py:RLSMiddleware"],
      sample:
        "SELECT set_config('app.current_organization_id', $1, true);\n" +
        "SELECT set_config('app.is_super_admin', $2, true);",
    },
  }),

  // Column 2 — core business logic
  n("policy", 2, 0, {
    kind: "policy",
    label: "Policy Engine",
    caption: "preview · Q3 2026",
    icon: "solar:filter-bold",
    detail: {
      role: "PREVIEW: программируемые правила (whitelists, time-locks, " +
            "amount thresholds, geo). Сейчас правила сохраняются в " +
            "policies_draft, не enforce'ятся. Реально включится в Q3 2026.",
    },
  }),
  n("aml", 2, 1, {
    kind: "policy",
    label: "AML / Sanctions",
    caption: "OFAC, UN, EU lists",
    icon: "solar:shield-warning-bold",
    detail: {
      role: "Проверка адреса получателя по санкционным спискам. На прод-этапе " +
            "интеграция с Sumsub / Chainalysis (planned). Сейчас — таблица " +
            "aml_alerts + ручной review-queue для compliance-офицера.",
      code: ["backend/services/aml_service.py", "aml_alerts table"],
    },
  }),
  n("signature", 2, 2, {
    kind: "core",
    label: "Signature Service",
    caption: "M-of-N + replay-guard",
    icon: "solar:pen-new-square-bold",
    detail: {
      role: "Обработка signature requests. UNIQUE INDEX (tx_unid, signer, " +
            "action) блокирует replay/double-sign. Запись в signature_history " +
            "перед роутом в Safina. EC-recovery primitive готов (Wave 13).",
      code: ["backend/services/signature_service.py"],
      sample: "INSERT INTO signature_history (tx_unid, signer_address, action) ...",
    },
  }),
  n("postgres", 2, 3, {
    kind: "storage",
    label: "PostgreSQL 16",
    caption: "60 таблиц, RLS active",
    icon: "solar:database-bold",
    detail: {
      role: "Канон-схема (Wave 11): 60 таблиц, 15 функций, 7 RLS политик, " +
            "311 индексов. Append-only триггеры на audit_log + signature_history.",
      code: ["backend/migrations/000_canonical_schema.sql"],
    },
  }),
  n("audit", 2, 4, {
    kind: "storage",
    label: "Audit Log",
    caption: "append-only · DB trigger",
    icon: "solar:document-text-bold",
    detail: {
      role: "BEFORE UPDATE OR DELETE триггер на audit_log RAISE EXCEPTION. " +
            "Невозможно изменить или удалить запись даже на уровне СУБД.",
      sample:
        "CREATE TRIGGER orgon_immutable_audit_log BEFORE DELETE OR UPDATE\n" +
        "ON public.audit_log FOR EACH ROW\n" +
        "EXECUTE FUNCTION public.orgon_block_update_delete();",
    },
  }),
  n("webhook", 2, 5, {
    kind: "core",
    label: "Webhook Dispatcher",
    caption: "retry, signed",
    icon: "solar:bolt-bold",
    detail: {
      role: "Доставка событий партнёрам. HMAC-подпись по " +
            "partner_webhooks.secret. Retry с exponential backoff на " +
            "5xx-ответах. Состояние в webhook_events.",
      code: ["backend/services/webhook_service.py"],
    },
  }),

  // Column 3 — Safina + blockchains + outbound
  n("safina-signer", 3, 0, {
    kind: "external",
    label: "Safina Signer",
    caption: "EC SECP256k1 · ETH-personal-sign",
    icon: "solar:key-bold",
    detail: {
      role: "Wave 12 абстракция SignerBackend. Сейчас EnvSignerBackend (key " +
            "in env). KMS / Vault stubs готовы. SafinaSigner делегирует " +
            "sign_msg_hash в backend.",
      code: ["backend/safina/signer.py", "backend/safina/signer_backends.py"],
    },
  }),
  n("safina-api", 3, 1, {
    kind: "external",
    label: "Safina Pay API",
    caption: "13/13 endpoints live-verified",
    icon: "solar:cloud-bold",
    detail: {
      role: "Wave 7 верификация: 13/13 endpoints прошли против " +
            "https://my.safina.pro/ece/. SafinaPayClient обёртывает все " +
            "методы (newWallet, send_transaction, sign, reject, ...).",
      code: ["backend/safina/client.py"],
    },
  }),
  n("chain-trx", 3, 2, {
    kind: "chain",
    label: "TRX testnet",
    caption: "5010",
    icon: "solar:cube-bold",
    detail: { role: "Tron Nile testnet — основная тестовая сеть для USDT-TRC20 операций." },
  }),
  n("chain-btc", 3, 3, {
    kind: "chain",
    label: "BTC testnet",
    caption: "1010",
    icon: "solar:bitcoin-bold",
    detail: { role: "Bitcoin testnet для long-term холодного хранения." },
  }),
  n("chain-eth", 3, 4, {
    kind: "chain",
    label: "ETH Sepolia",
    caption: "3010",
    icon: "solar:cube-bold",
    detail: { role: "Ethereum Sepolia testnet для USDT-ERC20 / USDC." },
  }),

  // Column 3 — outbound notifications
  n("notify-telegram", 3, 5, {
    kind: "notify",
    label: "Telegram",
    caption: "оператору / комплаенсу",
    icon: "solar:chat-round-bold",
    detail: {
      role: "Уведомления через TelegramNotifier — pending signature, AML alert, " +
            "failed delivery. Каналы по ролям.",
      code: ["backend/services/telegram_notifier.py"],
    },
  }),
  n("notify-email", 3, 6, {
    kind: "notify",
    label: "Email",
    caption: "SMTP / FileBackend",
    icon: "solar:letter-bold",
    detail: {
      role: "Wave 16 единый сервис: 5 HTML шаблонов + типизированные " +
            "send_password_reset / send_invite. SMTP в проде, FileBackend в dev.",
      code: ["backend/services/email_service.py"],
    },
  }),
  n("notify-partner-hook", 3, 7, {
    kind: "external",
    label: "Партнёрский endpoint",
    caption: "получатель webhook",
    icon: "solar:plain-bold",
    detail: {
      role: "Внешний URL партнёра, на который ORGON шлёт подписанный webhook " +
            "при изменении статуса транзакции.",
    },
  }),
];

// ─── Edges ──────────────────────────────────────────────────────────
//
// Edges define POSSIBLE connections; scenarios animate a subset of them
// in a specific order. Edge id format: "<from>__<to>".
//
// We keep them static (not animated by default) — animation kicks in
// only on the active scenario step.

const e = (from: string, to: string): Edge => ({
  id: `${from}__${to}`,
  source: from,
  target: to,
  type: "smoothstep",
  animated: false,
  style: { stroke: "var(--border)", strokeWidth: 1.5 },
});

export const EDGES: Edge[] = [
  // Clients → perimeter
  e("client-exchange",  "auth-jwt"),
  e("client-bank",      "auth-jwt"),
  e("client-mobile",    "auth-jwt"),
  e("client-partner",   "auth-hmac"),

  e("auth-jwt",         "auth-rls"),
  e("auth-hmac",        "auth-jwt"),

  // Perimeter → core
  e("auth-rls",         "policy"),
  e("auth-rls",         "aml"),
  e("auth-rls",         "signature"),
  e("auth-rls",         "postgres"),

  // Core internal
  e("policy",           "aml"),
  e("aml",              "signature"),
  e("signature",        "postgres"),
  e("signature",        "audit"),
  e("policy",           "audit"),
  e("aml",              "audit"),

  // Core → Safina + chains
  e("signature",        "safina-signer"),
  e("safina-signer",    "safina-api"),
  e("safina-api",       "chain-trx"),
  e("safina-api",       "chain-btc"),
  e("safina-api",       "chain-eth"),

  // Notifications outbound
  e("signature",        "webhook"),
  e("aml",              "notify-telegram"),
  e("signature",        "notify-telegram"),
  e("auth-jwt",         "notify-email"),
  e("webhook",          "notify-partner-hook"),
];

/** Lookup by id — used by scenario player. */
export const NODES_BY_ID: Record<string, Node<NodeData>> = NODES.reduce(
  (acc, node) => {
    acc[node.id] = node;
    return acc;
  },
  {} as Record<string, Node<NodeData>>,
);
