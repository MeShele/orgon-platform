"use client";

// Wraps the Sumsub WebSDK iframe with React lifecycle.
//
// Pattern (per ADR-8 in docs/stories/2-4-sumsub-kyc-architecture.md):
// 1. On mount, inject Sumsub's `<script>` tag if it's not already on the page.
// 2. Wait for `window.snsWebSdk` to become available.
// 3. Mint a fresh access-token from our backend, hand it to snsWebSdk.init().
// 4. Mount iframe in a container <div>.
// 5. On `idCheck.onApplicantSubmitted` event, fire `onComplete()` so the
//    parent can re-fetch status.
//
// The component shows a small loading skeleton while the SDK boots so
// the page doesn't look frozen for the 200-400ms it takes the script
// to download + initialise.

import { useEffect, useRef, useState } from "react";
import { fetchSumsubAccessToken } from "@/lib/sumsubKyc";
import { Icon } from "@/lib/icons";

const SDK_SRC = "https://static.sumsub.com/idensic/static/sns-websdk-builder.js";
const CONTAINER_ID = "orgon-sumsub-websdk";

interface AccessTokenLike {
  access_token: string;
}

interface Props {
  /** Called when user submits all docs and Sumsub queues review. */
  onComplete?: () => void;
  /** Lang for Sumsub's iframe internals. RU/EN/KY map to ru/en/en. */
  lang?: "ru" | "en" | "ky";
  /**
   * Async producer of a fresh access token. Defaults to the KYC
   * fetcher (`fetchSumsubAccessToken`). KYB callers pass a closure
   * that captures `organization_id` and calls `fetchSumsubKybAccessToken`.
   */
  tokenFetcher?: () => Promise<AccessTokenLike>;
}

function ensureSdkScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.snsWebSdk) return Promise.resolve();
  // Re-use an existing tag if some other component already loaded it.
  const existing = document.querySelector(`script[src="${SDK_SRC}"]`);
  if (existing) {
    return new Promise((resolve) => {
      existing.addEventListener("load", () => resolve());
    });
  }
  return new Promise((resolve, reject) => {
    const tag = document.createElement("script");
    tag.src = SDK_SRC;
    tag.async = true;
    tag.onload = () => resolve();
    tag.onerror = () => reject(new Error(`Failed to load ${SDK_SRC}`));
    document.head.appendChild(tag);
  });
}

export function SumsubWebSdkContainer({
  onComplete,
  lang = "ru",
  tokenFetcher,
}: Props) {
  const [error, setError] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const launched = useRef(false);

  useEffect(() => {
    if (launched.current) return;
    launched.current = true;

    const fetchToken: () => Promise<AccessTokenLike> =
      tokenFetcher ?? fetchSumsubAccessToken;

    let cancelled = false;
    (async () => {
      try {
        const tokenResp = await fetchToken();
        await ensureSdkScript();
        if (cancelled) return;
        if (!window.snsWebSdk) {
          throw new Error("snsWebSdk not available after script load");
        }
        // Sumsub asks for a token-refresh callback so it can renew when
        // the original short-lived token nears expiry while user is still
        // in the iframe.
        const refresh = async () => {
          const fresh = await fetchToken();
          return fresh.access_token;
        };
        // Map our 'ky' to Sumsub's nearest-supported 'en'.
        const sumsubLang = lang === "ky" ? "en" : lang;
        window.snsWebSdk
          .init(tokenResp.access_token, refresh)
          .withConf({ lang: sumsubLang, theme: "light" })
          .withOptions({ addViewportTag: false, adaptIframeHeight: true })
          .on("idCheck.onApplicantSubmitted", () => {
            // Fire on full submission. Parent re-fetches status.
            onComplete?.();
          })
          .build()
          .launch(`#${CONTAINER_ID}`);
        setBooting(false);
      } catch (e) {
        if (cancelled) return;
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
        setBooting(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [lang, onComplete, tokenFetcher]);

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-6">
        <div className="flex items-start gap-3">
          <Icon icon="solar:danger-circle-bold" className="text-destructive text-xl shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">Не удалось запустить верификацию</p>
            <p className="text-xs text-muted-foreground">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {booting && (
        <div className="flex items-center justify-center py-16">
          <Icon icon="svg-spinners:ring-resize" className="text-3xl text-primary" />
          <span className="ml-3 text-sm text-muted-foreground">Загружаем модуль верификации…</span>
        </div>
      )}
      {/* Sumsub mounts iframe here. Hidden until booted. */}
      <div id={CONTAINER_ID} style={{ minHeight: booting ? 0 : 600 }} />
    </div>
  );
}
