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
    approved: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    pending: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    in_review: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    rejected: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    not_submitted: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
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
        <Icon icon="svg-spinners:ring-resize" className="text-3xl text-indigo-500" />
      </div>
    );
  }

  const currentStatus = kycStatus?.status || "not_submitted";
  const canSubmit = currentStatus === "not_submitted" || currentStatus === "rejected";

  return (
    <div className="space-y-6 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-3">
        <Icon icon="solar:user-check-bold" className="text-2xl text-indigo-500" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">KYC Верификация</h1>
          <p className="text-sm text-slate-500">Подтверждение личности по законодательству КР</p>
        </div>
      </div>

      {/* Current Status */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-sm font-medium text-slate-500 mb-2">Текущий статус</h3>
        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${statusColors[currentStatus]}`}>
          {statusLabels[currentStatus]}
        </span>
        {kycStatus?.review_comment && currentStatus === "rejected" && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">
            Причина: {kycStatus.review_comment}
          </p>
        )}
      </div>

      {/* Submission Form */}
      {canSubmit && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <h3 className="font-semibold text-slate-900 dark:text-white">Личные данные</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">ФИО *</label>
                <input
                  type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  placeholder="Иванов Иван Иванович"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Дата рождения</label>
                <input
                  type="date" value={dateOfBirth} onChange={(e) => setDateOfBirth(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Гражданство</label>
                <select
                  value={nationality} onChange={(e) => setNationality(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="KG">Кыргызстан</option>
                  <option value="KZ">Казахстан</option>
                  <option value="RU">Россия</option>
                  <option value="UZ">Узбекистан</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Телефон</label>
                <input
                  type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  placeholder="+996 555 123456"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Адрес</label>
              <textarea
                value={address} onChange={(e) => setAddress(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                rows={2} placeholder="г. Бишкек, ул. ..."
              />
            </div>
          </div>

          {/* Documents */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 space-y-4">
            <h3 className="font-semibold text-slate-900 dark:text-white">Документы</h3>
            <p className="text-sm text-slate-500">Загрузите необходимые документы для верификации</p>

            <div className="space-y-3">
              {DOC_TYPES.map((doc) => {
                const added = documents.find((d) => d.type === doc.value);
                return (
                  <div
                    key={doc.value}
                    className={`flex items-center justify-between p-3 rounded-lg border ${
                      added
                        ? "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20"
                        : "border-slate-200 dark:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon icon={doc.icon} className={added ? "text-emerald-500" : "text-slate-400"} />
                      <span className="text-sm text-slate-700 dark:text-slate-300">{doc.label}</span>
                    </div>
                    {added ? (
                      <button type="button" onClick={() => removeDocument(doc.value)} className="text-red-500 text-sm hover:underline">
                        Удалить
                      </button>
                    ) : (
                      <button
                        type="button" onClick={() => addDocument(doc.value)}
                        className="px-3 py-1 text-sm bg-indigo-500 text-white rounded-lg hover:bg-indigo-600"
                      >
                        Загрузить
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
              {error}
            </div>
          )}
          {success && (
            <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 p-3 text-sm text-emerald-700 dark:text-emerald-400">
              {success}
            </div>
          )}

          <button
            type="submit" disabled={submitting || !fullName || documents.length === 0}
            className="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Отправка..." : "Отправить на верификацию"}
          </button>
        </form>
      )}

      {currentStatus === "approved" && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20 p-6 text-center">
          <Icon icon="solar:verified-check-bold" className="text-4xl text-emerald-500 mx-auto mb-2" />
          <p className="text-emerald-700 dark:text-emerald-300 font-medium">Ваша личность подтверждена</p>
          <p className="text-sm text-emerald-600 dark:text-emerald-400 mt-1">Вы можете совершать транзакции</p>
        </div>
      )}
    </div>
  );
}
