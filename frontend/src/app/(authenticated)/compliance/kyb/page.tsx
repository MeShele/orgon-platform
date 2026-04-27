"use client";

import { useState, useEffect } from "react";
import { Icon } from "@/lib/icons";

const DOC_TYPES = [
  { value: "registration_cert", label: "Свидетельство о регистрации", icon: "solar:document-bold" },
  { value: "charter", label: "Устав компании", icon: "solar:notebook-bold" },
  { value: "license", label: "Лицензия (если есть)", icon: "solar:diploma-bold" },
  { value: "beneficiaries", label: "Данные бенефициаров", icon: "solar:users-group-rounded-bold" },
];

export default function KybPage() {
  const [kybStatus, setKybStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [companyName, setCompanyName] = useState("");
  const [regNumber, setRegNumber] = useState("");
  const [taxId, setTaxId] = useState("");
  const [legalAddress, setLegalAddress] = useState("");
  const [country, setCountry] = useState("KG");
  const [documents, setDocuments] = useState<{ type: string; file_url: string; file_name: string }[]>([]);
  const [beneficiaries, setBeneficiaries] = useState<{ name: string; share_percent: number; nationality: string }[]>([
    { name: "", share_percent: 100, nationality: "KG" },
  ]);

  // In production, org_id comes from user's current org context
  const [orgId, setOrgId] = useState("");

  useEffect(() => {
    // Would fetch org_id from context and then status
    setLoading(false);
  }, []);

  function addDocument(type: string) {
    if (documents.find((d) => d.type === type)) return;
    setDocuments([...documents, { type, file_url: `placeholder://${type}`, file_name: `${type}_document` }]);
  }

  function removeDocument(type: string) {
    setDocuments(documents.filter((d) => d.type !== type));
  }

  function updateBeneficiary(index: number, field: string, value: any) {
    const updated = [...beneficiaries];
    (updated[index] as any)[field] = value;
    setBeneficiaries(updated);
  }

  function addBeneficiary() {
    setBeneficiaries([...beneficiaries, { name: "", share_percent: 0, nationality: "KG" }]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSubmitting(true);

    try {
      const res = await fetch("/api/v1/kyc-kyb/kyb/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("orgon_access_token")}`,
        },
        body: JSON.stringify({
          organization_id: orgId,
          company_name: companyName,
          registration_number: regNumber,
          tax_id: taxId,
          legal_address: legalAddress,
          country,
          documents,
          beneficiaries: beneficiaries.filter((b) => b.name),
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Submission failed");
      }

      setSuccess("KYB заявка отправлена! Ожидайте проверки.");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const statusColors: Record<string, string> = {
    approved: "bg-emerald-100 text-success",
    pending: "bg-warning/10 text-warning",
    rejected: "bg-destructive/10 text-destructive",
    not_submitted: "bg-muted text-muted-foreground",
  };

  return (
    <div className="space-y-6 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-3">
        <Icon icon="solar:buildings-bold" className="text-2xl text-primary" />
        <div>
          <h1 className="text-2xl font-bold text-foreground">KYB Верификация</h1>
          <p className="text-sm text-muted-foreground">Верификация организации по законодательству КР</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Company Info */}
        <div className="rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card space-y-4">
          <h3 className="font-semibold text-foreground">Данные компании</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Название компании *</label>
              <input
                type="text" required value={companyName} onChange={(e) => setCompanyName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Рег. номер</label>
              <input
                type="text" value={regNumber} onChange={(e) => setRegNumber(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">ИНН</label>
              <input
                type="text" value={taxId} onChange={(e) => setTaxId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Страна</label>
              <select
                value={country} onChange={(e) => setCountry(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
              >
                <option value="KG">Кыргызстан</option>
                <option value="KZ">Казахстан</option>
                <option value="RU">Россия</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Юридический адрес</label>
            <textarea
              value={legalAddress} onChange={(e) => setLegalAddress(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground"
              rows={2}
            />
          </div>
        </div>

        {/* Documents */}
        <div className="rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card space-y-4">
          <h3 className="font-semibold text-foreground">Документы</h3>
          <div className="space-y-3">
            {DOC_TYPES.map((doc) => {
              const added = documents.find((d) => d.type === doc.value);
              return (
                <div key={doc.value} className={`flex items-center justify-between p-3 rounded-lg border ${
                  added ? "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20" : "border-border"
                }`}>
                  <div className="flex items-center gap-3">
                    <Icon icon={doc.icon} className={added ? "text-success" : "text-muted-foreground"} />
                    <span className="text-sm text-foreground">{doc.label}</span>
                  </div>
                  {added ? (
                    <button type="button" onClick={() => removeDocument(doc.value)} className="text-destructive text-sm">Удалить</button>
                  ) : (
                    <button type="button" onClick={() => addDocument(doc.value)} className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary">Загрузить</button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Beneficiaries */}
        <div className="rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-foreground">Бенефициары</h3>
            <button type="button" onClick={addBeneficiary} className="text-sm text-primary hover:underline">+ Добавить</button>
          </div>
          {beneficiaries.map((b, i) => (
            <div key={i} className="grid grid-cols-3 gap-3">
              <input
                type="text" placeholder="ФИО" value={b.name}
                onChange={(e) => updateBeneficiary(i, "name", e.target.value)}
                className="px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
              />
              <input
                type="number" placeholder="% доли" value={b.share_percent}
                onChange={(e) => updateBeneficiary(i, "share_percent", Number(e.target.value))}
                className="px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
              />
              <select
                value={b.nationality} onChange={(e) => updateBeneficiary(i, "nationality", e.target.value)}
                className="px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
              >
                <option value="KG">KG</option>
                <option value="KZ">KZ</option>
                <option value="RU">RU</option>
              </select>
            </div>
          ))}
        </div>

        {error && <div className="rounded-lg bg-destructive/5 border border-destructive/30 p-3 text-sm text-destructive">{error}</div>}
        {success && <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-sm text-success">{success}</div>}

        <button
          type="submit" disabled={submitting || !companyName}
          className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "Отправка..." : "Отправить на верификацию"}
        </button>
      </form>
    </div>
  );
}
