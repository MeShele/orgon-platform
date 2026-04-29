"use client";

import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

export default function KeysPage() {
  return (
    <>
      <Header title="Управление ключами" />
      <div className="space-y-4 p-2 sm:p-4 md:p-6 lg:p-8 max-w-2xl">
        <Card>
          <CardHeader
            title="EC-ключ подписи"
            subtitle="Приватный ключ SECP256k1 для аутентификации в Safina Pay API"
            action={<HelpTooltip text={helpContent.keys.ecKey.text} diagram={helpContent.keys.ecKey.diagram} />}
          />
          <div className="space-y-3 p-4">
            <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/5 p-3">
              <Icon icon="solar:shield-keyhole-linear" className="mt-0.5 text-base text-warning" />
              <p className="text-xs text-warning">
                Приватный EC-ключ хранится в защищённом хранилище ASAGENT CredentialVault
                (шифрование AES-256-GCM). Через API никогда не передаётся.
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              Чтобы заменить ключ, задайте переменную окружения{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono dark:bg-muted">
                SAFINA_EC_PRIVATE_KEY
              </code>{" "}
              и перезапустите backend.
            </p>
          </div>
        </Card>

        <Card>
          <CardHeader title="Параметры ключа" />
          <div className="space-y-2 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Алгоритм</span>
              <span className="text-xs font-medium text-foreground">ECDSA SECP256k1</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Схема подписи</span>
              <span className="text-xs font-medium text-foreground">ETH-совместимая (sign_msg)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                Заголовки запроса
                <HelpTooltip text={helpContent.keys.headers.text} />
              </span>
              <span className="font-mono text-[10px] text-muted-foreground">x-app-ec-from, x-app-ec-sign-r/s/v</span>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
