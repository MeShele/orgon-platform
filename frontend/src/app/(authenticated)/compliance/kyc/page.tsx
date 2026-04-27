"use client";

import { useState, useEffect } from "react";
import { Icon } from "@/lib/icons";

interface KycStatus {
  status: string;
  id?: string;
  risk_level?: string;
  review_comment?: string;
  submitted_at?: string;
  reviewed_at?: string;
}

const DOC_TYPES = [
  { value: "passport", label: "Паспорт / ID Card", icon: "solar:card-bold" },
  { value: "selfie", label: "Селфи с документом", icon: "solar:camera-bold" },
  { value: "proof_of_address", label: "Подтверждение адреса", icon: "solar:home-bold" },
];

export default function KycPage() {
  const [kycStatus, setKycStatus] = useState<KycStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [fullName, setFullName] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [nationality, setNationality] = useState("KG");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [documents, setDocuments] = useState<{ type: string; file_url: string; file_name: string }[]>([]);

  useEffect(() => {
    fetchStatus();
  }, []);

  async function fetchStatus() {
    try {
      const res = await fetch("/api/v1/kyc-kyb/kyc/status", {
        headers: { Authorization: `Bearer ${localStorage.getItem("orgon_access_token")}` },
      });
      const data = await res.json();
      setKycStatus(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function addDocument(type: string) {
    if (documents.find((d) => d.type === type)) return;
    // In production, this would trigger file upload. For now, placeholder.
    setDocuments([...documents, { type, file_url: `placeholder://${type}`, file_name: `${type}_document` }]);
  }

  function removeDocument(type: string) {
    setDocuments(documents.filter((d) => d.type !== type));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSubmitting(true);

    try {
      const res = await fetch("/api/v1/kyc-kyb/kyc/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("orgon_access_token")}`,
        },
        body: JSON.stringify({
          full_name: fullName,
          date_of_birth: dateOfBirth || null,
          nationality,
          address,
          phone,
          documents,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Submission failed");
      }

      setSuccess("KYC заявка отправлена! Ожидайте проверки.");
      fetchStatus();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const statusColors: Record<string, string> = {
    approved: "bg-success/10 text-success",
    pending: "bg-warning/10 text-warning",
    in_review: "bg-primary/10 text-primary",
    rejected: "bg-destructive/10 text-destructive",
    not_submitted: "bg-muted text-muted-foreground",
  };

  const statusLabels: Record<string, string> = {
    approved: "✅ Верифицирован",
    pending: "⏳ На рассмотрении",
    in_review: "🔍 Проверяется",
    rejected: "❌ Отклонено",
    not_submitted: "Не подано",
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Icon icon="svg-spinners:ring-resize" className="text-3xl text-primary" />
      </div>
    );
  }

  const currentStatus = kycStatus?.status || "not_submitted";
  const canSubmit = currentStatus === "not_submitted" || currentStatus === "rejected";

  return (
    <div className="space-y-6 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-3">
        <Icon icon="solar:user-check-bold" className="text-2xl text-primary" />
        <div>
          <h1 className="text-2xl font-bold text-foreground">KYC Верификация</h1>
          <p className="text-sm text-muted-foreground">Подтверждение личности по законодательству КР</p>
        </div>
      </div>

      {/* Current Status */}
      <div className="rounded-xl border border-border bg-card p-5 dark:border-border dark:bg-card">
        <h3 className="text-sm font-medium text-muted-foreground mb-2">Текущий статус</h3>
        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${statusColors[currentStatus]}`}>
          {statusLabels[currentStatus]}
        </span>
        {kycStatus?.review_comment && currentStatus === "rejected" && (
          <p className="mt-2 text-sm text-destructive">
            Причина: {kycStatus.review_comment}
          </p>
        )}
      </div>

      {/* Submission Form */}
      {canSubmit && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card space-y-4">
            <h3 className="font-semibold text-foreground">Личные данные</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">ФИО *</label>
                <input
                  type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
                  placeholder="Иванов Иван Иванович"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Дата рождения</label>
                <input
                  type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Гражданство</label>
                <select
                  value={nationality} onChange={(e) => setNationality(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
                >
                  <option value="KG">Кыргызстан</option>
                  <option value="KZ">Казахстан</option>
                  <option value="RU">Россия</option>
                  <option value="UZ">Узбекистан</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Телефон</label>
                <input
                  type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
                  placeholder="+996 555 123456"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Адрес</label>
              <textarea
                value={address} onChange={(e) => setAddress(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
                rows={2} placeholder="г. Бишкек, ул. ..."
              />
            </div>
          </div>

          {/* Documents */}
          <div className="rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card space-y-4">
            <h3 className="font-semibold text-foreground">Документы</h3>
            <p className="text-sm text-muted-foreground">Отметьте, какие документы вы готовы предоставить для верификации</p>

            <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3 text-[13px]">
              <Icon icon="solar:info-circle-bold" className="text-warning mt-0.5 shrink-0" />
              <div className="text-foreground">
                Прямая загрузка файлов через интерфейс — в разработке. Сейчас отметьте список,
                а сами копии отправьте на{" "}
                <a className="text-primary underline-offset-4 hover:underline" href="mailto:compliance@orgon.asystem.kg">compliance@orgon.asystem.kg</a>{" "}
                с темой «KYC submission · ваше ФИО». Compliance-команда привяжет их к вашей заявке.
              </div>
            </div>

            <div className="space-y-3">
              {DOC_TYPES.map((doc) => {
                const added = documents.find((d) => d.type === doc.value);
                return (
                  <div
                    key={doc.value}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      added ? "border-success/40 bg-success/5" : "border-border"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon icon={doc.icon} className={added ? "text-success" : "text-muted-foreground"} />
                      <span className="text-sm text-foreground">{doc.label}</span>
                    </div>
                    {added ? (
                      <button type="button" onClick={() => removeDocument(doc.value)} className="text-destructive text-sm hover:underline">
                        Снять отметку
                      </button>
                    ) : (
                      <button
                        type="button" onClick={() => addDocument(doc.value)}
                        className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity"
                      >
                        Отметить как готовый
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-destructive/10 border border-red-200 dark:border-red-800 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          {success && (
            <div className="rounded-lg bg-success/10 border border-emerald-200 dark:border-emerald-800 p-3 text-sm text-success">
              {success}
            </div>
          )}

          <button
            type="submit" disabled={submitting || !fullName || documents.length === 0}
            className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Отправка..." : "Отправить на верификацию"}
          </button>
        </form>
      )}

      {currentStatus === "approved" && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20 p-6 text-center">
          <Icon icon="solar:verified-check-bold" className="text-4xl text-success mx-auto mb-2" />
          <p className="text-success dark:text-emerald-300 font-medium">Ваша личность подтверждена</p>
          <p className="text-sm text-success mt-1">Вы можете совершать транзакции</p>
        </div>
      )}
    </div>
  );
}
