"use client";

import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

export default function KeysPage() {
  return (
    <>
      <Header title="Key Management" />
      <div className="space-y-4 p-2 sm:p-4 md:p-6 lg:p-8 max-w-2xl">
        <Card>
          <CardHeader
            title="EC Signing Key"
            subtitle="SECP256k1 private key used for Safina API authentication"
            action={<HelpTooltip text={helpContent.keys.ecKey.text} diagram={helpContent.keys.ecKey.diagram} />}
          />
          <div className="space-y-3 p-4">
            <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-500/20 dark:bg-amber-500/10">
              <Icon icon="solar:shield-keyhole-linear" className="mt-0.5 text-base text-amber-600 dark:text-amber-400" />
              <p className="text-xs text-amber-800 dark:text-amber-300">
                The EC private key is stored securely in the ASAGENT CredentialVault
                (AES-256-GCM encrypted). It is never exposed through the API.
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              To update the key, set the{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono dark:bg-muted">
                SAFINA_EC_PRIVATE_KEY
              </code>{" "}
              environment variable and restart the backend.
            </p>
          </div>
        </Card>

        <Card>
          <CardHeader title="Key Details" />
          <div className="space-y-2 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Algorithm</span>
              <span className="text-xs font-medium text-foreground">ECDSA SECP256k1</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Signature</span>
              <span className="text-xs font-medium text-foreground">ETH-compatible (sign_msg)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                Headers
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
