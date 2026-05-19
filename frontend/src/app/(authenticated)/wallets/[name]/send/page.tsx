"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { networkName } from "@/lib/walletDisplay";
import { getNetworkConfig, explorerTxUrl } from "@/lib/networkConfig";

type Stage = "input" | "preview" | "signing" | "broadcasting" | "done" | "error";

export default function SendTransactionPage() {
  const params = useParams();
  const router = useRouter();
  const walletName = params.name as string;

  const [wallet, setWallet] = useState<Record<string, unknown> | null>(null);
  const [walletError, setWalletError] = useState("");

  // form fields
  const [toAddr, setToAddr] = useState("");
  const [value, setValue] = useState("");
  const [info, setInfo] = useState("");
  const [stage, setStage] = useState<Stage>("input");
  const [txUnid, setTxUnid] = useState<string>("");
  const [txHash, setTxHash] = useState<string>("");
  const [submitErr, setSubmitErr] = useState("");

  useEffect(() => {
    api.getWallet(walletName).then(setWallet).catch((e) => setWalletError(String(e?.message ?? e)));
  }, [walletName]);

  if (walletError) {
    return (
      <>
        <Header title="Отправка" />
        <div className="p-6">
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-xs text-destructive">
            {walletError}
          </div>
        </div>
      </>
    );
  }
  if (!wallet) {
    return (
      <>
        <Header title="Отправка" />
        <div className="p-6"><LoadingSpinner /></div>
      </>
    );
  }

  const primaryAddr =
    (wallet.addrs as string | null)?.split(",")[0]?.trim() ||
    (wallet.addr as string | null) ||
    "";
  const network = (wallet.network as number | string | null) ?? null;
  // Per-network config drives everything network-dependent on this page
  // (placeholders, currency label, explorer link). Fallback when an
  // unknown network slips through — render generic copy rather than
  // mis-labeling something as TRX.
  const netCfg = getNetworkConfig(network);
  const nativeSymbol = netCfg?.nativeSymbol ?? "—";
  const addrPlaceholder = netCfg?.addressPlaceholder ?? "адрес получателя";
  const explorerName = netCfg?.explorerName ?? "explorer";
  // Token string format Safina expects: "<network>:::<symbol>###<wallet_name>".
  // We only support the native token here for now.
  const tokenStr = `${String(network)}:::${nativeSymbol}###${String(wallet.name ?? walletName)}`;

  const canSubmit = toAddr.trim().length > 0 && Number(value) > 0;

  async function performSend() {
    setSubmitErr("");
    setStage("signing");

    try {
      // 1. Create the tx on Safina side. ?validate=false so our
      //    local-DB balance check (often 0 due to Safina's polling
      //    lag) doesn't block what is in fact a valid send.
      const created = (await api.sendTransaction(
        { token: tokenStr, to_address: toAddr.trim(), value: String(value), info: info.trim() },
        { validate: false },
      )) as { tx_unid: string };
      setTxUnid(created.tx_unid);

      // 2. Sign with our tenant EC via the v2 signatures endpoint.
      await api.signTransactionV2(created.tx_unid);

      setStage("broadcasting");

      // 3. Poll local DB (synced from Safina every minute) until a
      //    real on-chain tx_hash appears. Safina occasionally writes
      //    sentinel strings like "Transaction canceled, 1 day limit."
      //    into tx_hash — filter those out.
      const start = Date.now();
      const TIMEOUT_MS = 5 * 60 * 1000;
      while (Date.now() - start < TIMEOUT_MS) {
        await new Promise((r) => setTimeout(r, 6000));
        try {
          const tx = (await api.getTransaction(created.tx_unid)) as
            | { tx_hash?: string | null }
            | null;
          const h = tx?.tx_hash || "";
          if (h && !h.toLowerCase().includes("canceled") && !h.toLowerCase().includes("limit")) {
            setTxHash(h);
            setStage("done");
            return;
          }
        } catch {
          /* polling failure is non-fatal — try again */
        }
      }
      throw new Error("Не удалось подтвердить broadcast за 5 минут — проверьте статус позже на странице транзакций.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Неизвестная ошибка";
      setSubmitErr(msg);
      setStage("error");
      toast.error(`Ошибка отправки: ${msg}`);
    }
  }

  return (
    <>
      <Header title="Отправка транзакции" />
      <div className="space-y-4 p-2 sm:p-4 md:p-6 lg:p-8 max-w-2xl">
        <Card>
          <CardHeader
            title="Новая транзакция"
            subtitle={`Сеть: ${networkName(network)} · С: ${primaryAddr || "(адрес ещё не выдан)"}`}
            action={
              <Button variant="ghost" size="sm" onClick={() => router.back()}>
                <Icon icon="solar:arrow-left-linear" className="text-base" /> Назад
              </Button>
            }
          />

          <div className="p-4">
            <AnimatePresence mode="wait">
              {stage === "input" || stage === "preview" ? (
                <motion.div
                  key="input"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                  className="space-y-4"
                >
                  <Field label="Адрес получателя">
                    <input
                      type="text"
                      value={toAddr}
                      onChange={(e) => setToAddr(e.target.value)}
                      placeholder={addrPlaceholder}
                      className={inputClass + " font-mono"}
                    />
                  </Field>
                  <Field label={`Сумма (${nativeSymbol})`}>
                    <input
                      type="number"
                      step="0.000001"
                      min="0"
                      value={value}
                      onChange={(e) => setValue(e.target.value)}
                      placeholder="0.0"
                      className={inputClass + " font-mono"}
                    />
                  </Field>
                  <Field label="Описание (необязательно)">
                    <input
                      type="text"
                      value={info}
                      onChange={(e) => setInfo(e.target.value)}
                      placeholder="Например: payout #42"
                      className={inputClass}
                    />
                  </Field>

                  <PreviewBox
                    from={primaryAddr || "(адрес ещё не выдан)"}
                    to={toAddr}
                    amount={value}
                    symbol={nativeSymbol}
                  />

                  <div className="flex justify-end gap-2 pt-2">
                    <Button variant="secondary" size="md" onClick={() => router.back()}>
                      Отмена
                    </Button>
                    <Button
                      variant="primary"
                      size="md"
                      disabled={!canSubmit || !primaryAddr}
                      onClick={performSend}
                    >
                      <Icon icon="solar:plain-linear" className="text-base" />
                      Отправить
                    </Button>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="progress"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className="space-y-4"
                >
                  <ProgressList stage={stage} />

                  {stage === "done" ? (
                    <div className="rounded-lg border border-success/30 bg-success/5 p-4 space-y-2">
                      <div className="flex items-center gap-2 text-sm font-medium text-success">
                        <Icon icon="solar:check-circle-bold" /> Транзакция в сети
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Hash:{" "}
                        <span className="font-mono text-foreground break-all">{txHash}</span>
                      </p>
                      {explorerTxUrl(network, txHash) ? (
                        <a
                          href={explorerTxUrl(network, txHash) ?? "#"}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                        >
                          Открыть в {explorerName}
                          <Icon icon="solar:arrow-right-up-linear" className="text-sm" />
                        </a>
                      ) : null}
                      <div className="pt-2 flex flex-wrap gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => router.push(`/wallets/${walletName}`)}
                        >
                          К кошельку
                        </Button>
                        {txUnid ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => router.push(`/transactions/${txUnid}`)}
                          >
                            К транзакции
                          </Button>
                        ) : null}
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => router.push("/transactions")}
                        >
                          Все транзакции
                        </Button>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            setToAddr("");
                            setValue("");
                            setInfo("");
                            setTxHash("");
                            setTxUnid("");
                            setStage("input");
                          }}
                        >
                          Отправить ещё
                        </Button>
                      </div>
                    </div>
                  ) : null}

                  {stage === "error" ? (
                    <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 space-y-2">
                      <div className="flex items-center gap-2 text-sm font-medium text-destructive">
                        <Icon icon="solar:close-circle-bold" /> Не удалось отправить
                      </div>
                      <p className="text-xs text-muted-foreground">{submitErr}</p>
                      {txUnid ? (
                        <p className="text-[11px] text-muted-foreground">
                          UNID транзакции: <span className="font-mono">{txUnid}</span>
                        </p>
                      ) : null}
                      <div className="pt-2 flex gap-2">
                        <Button variant="secondary" size="sm" onClick={() => setStage("input")}>
                          Изменить и повторить
                        </Button>
                      </div>
                    </div>
                  ) : null}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </Card>
      </div>
    </>
  );
}

const inputClass =
  "w-full rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground dark:border-border dark:bg-card/50 dark:text-white focus:outline-none focus:ring-1 focus:ring-primary/30 dark:focus:ring-slate-600 transition-colors";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs font-medium text-muted-foreground mb-1.5 block">{label}</label>
      {children}
    </div>
  );
}

function PreviewBox({
  from,
  to,
  amount,
  symbol,
}: {
  from: string;
  to: string;
  amount: string;
  symbol: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3 text-xs space-y-1.5 dark:bg-card/30">
      <Row label="С">
        <span className="font-mono text-foreground break-all">{from}</span>
      </Row>
      <Row label="На">
        <span className="font-mono text-foreground break-all">{to || "—"}</span>
      </Row>
      <Row label="Сумма">
        <span className="font-mono text-foreground">
          {amount || "0"} {symbol}
        </span>
      </Row>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[4rem_1fr] gap-2 items-baseline">
      <span className="text-muted-foreground">{label}</span>
      <span>{children}</span>
    </div>
  );
}

function ProgressList({ stage }: { stage: Stage }) {
  // Marker mapping. We don't show "input/preview" here — list only
  // renders while the request is in flight.
  const steps: Array<{ key: Stage; label: string; sublabel: string }> = [
    { key: "signing", label: "Подписание", sublabel: "Подписываем нашим EC ключом" },
    { key: "broadcasting", label: "Отправка в сеть", sublabel: "Safina передаёт транзакцию в блокчейн" },
    { key: "done", label: "Подтверждение", sublabel: "Транзакция принята сетью" },
  ];
  // Cursor positions:
  //   signing       (1) → step #1 active
  //   broadcasting  (2) → step #1 done, #2 active
  //   done          (4) → all three done (cursor past the last step)
  //   error         → caller renders the error card instead, list hidden
  const order: Record<Stage, number> = {
    input: 0,
    preview: 0,
    signing: 1,
    broadcasting: 2,
    done: 4,
    error: -1,
  };
  const cur = order[stage];

  return (
    <ol className="space-y-2">
      {steps.map((s, i) => {
        const idx = i + 1;
        const done = cur > idx;
        const active = cur === idx;
        return (
          <li
            key={s.key}
            className={
              done
                ? "rounded-lg border border-success/30 bg-success/5 px-3 py-2"
                : active
                ? "rounded-lg border border-primary/30 bg-primary/5 px-3 py-2"
                : "rounded-lg border border-border bg-muted/30 px-3 py-2"
            }
          >
            <div className="flex items-center gap-3">
              {done ? (
                <Icon icon="solar:check-circle-bold" className="text-success text-lg" />
              ) : active ? (
                <Icon icon="solar:refresh-bold" className="text-primary text-lg animate-spin" />
              ) : (
                <Icon icon="solar:clock-circle-linear" className="text-muted-foreground text-lg" />
              )}
              <div>
                <p className={done || active ? "text-xs font-medium text-foreground" : "text-xs font-medium text-muted-foreground"}>
                  {s.label}
                </p>
                <p className="text-[10px] text-muted-foreground">{s.sublabel}</p>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
