"use client";

import { useState, useEffect } from "react";
import { Icon } from "@/lib/icons";

type ReviewTab = "kyc" | "kyb";

interface Submission {
  id: string;
  status: string;
  full_name?: string;
  company_name?: string;
  user_email?: string;
  org_name?: string;
  documents: any[];
  submitted_at: string;
  risk_level: string;
  review_comment?: string;
}

export default function ReviewsPage() {
  const [tab, setTab] = useState<ReviewTab>("kyc");
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [riskLevel, setRiskLevel] = useState("low");

  useEffect(() => {
    fetchSubmissions();
  }, [tab]);

  async function fetchSubmissions() {
    setLoading(true);
    try {
      const endpoint = tab === "kyc" ? "/api/v1/kyc-kyb/kyc/submissions" : "/api/v1/kyc-kyb/kyb/submissions";
      const res = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${localStorage.getItem("orgon_access_token")}` },
      });
      const data = await res.json();
      setSubmissions(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleReview(id: string, decision: "approved" | "rejected") {
    try {
      const endpoint = tab === "kyc"
        ? `/api/v1/kyc-kyb/kyc/${id}/review`
        : `/api/v1/kyc-kyb/kyb/${id}/review`;

      const res = await fetch(endpoint, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("orgon_access_token")}`,
        },
        body: JSON.stringify({ decision, comment, risk_level: riskLevel }),
      });

      if (res.ok) {
        setReviewingId(null);
        setComment("");
        fetchSubmissions();
      }
    } catch (e) {
      console.error(e);
    }
  }

  const statusBadge = (s: string) => {
    const colors: Record<string, string> = {
      pending: "bg-warning/10 text-warning",
      in_review: "bg-primary/10 text-primary",
      approved: "bg-success/10 text-success",
      rejected: "bg-destructive/10 text-destructive",
    };
    return <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[s] || "bg-muted text-muted-foreground"}`}>{s}</span>;
  };

  return (
    <div className="space-y-6 p-2 sm:p-4 md:p-6 lg:p-8">
      <div className="flex items-center gap-3">
        <Icon icon="solar:clipboard-check-bold" className="text-2xl text-primary" />
        <div>
          <h1 className="text-2xl font-bold text-foreground">Проверка заявок</h1>
          <p className="text-sm text-muted-foreground">KYC/KYB верификация — панель администратора</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {[
          { id: "kyc" as ReviewTab, label: "KYC (Физ. лица)", icon: "solar:user-bold" },
          { id: "kyb" as ReviewTab, label: "KYB (Организации)", icon: "solar:buildings-bold" },
        ].map((t) => (
          <button
            key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon icon={t.icon} /> {t.label}
          </button>
        ))}
      </div>

      {/* Submissions List */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Icon icon="svg-spinners:ring-resize" className="text-3xl text-primary" />
        </div>
      ) : submissions.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Icon icon="solar:inbox-bold" className="text-4xl mx-auto mb-2 text-faint" />
          <p>Нет заявок</p>
        </div>
      ) : (
        <div className="space-y-3">
          {submissions.map((s) => (
            <div key={s.id} className="rounded-xl border border-border bg-white p-4 dark:border-border dark:bg-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-foreground">
                    {tab === "kyc" ? s.full_name : s.company_name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {tab === "kyc" ? s.user_email : s.org_name} • {new Date(s.submitted_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {statusBadge(s.status)}
                  {s.status === "pending" && (
                    <button
                      onClick={() => setReviewingId(reviewingId === s.id ? null : s.id)}
                      className="px-3 py-1 text-sm bg-primary text-white rounded-lg hover:bg-primary"
                    >
                      Проверить
                    </button>
                  )}
                </div>
              </div>

              {/* Documents preview */}
              {s.documents && s.documents.length > 0 && (
                <div className="mt-2 flex gap-2 flex-wrap">
                  {(typeof s.documents === 'string' ? JSON.parse(s.documents) : s.documents).map((doc: any, i: number) => (
                    <span key={i} className="px-2 py-1 bg-muted rounded text-xs text-muted-foreground">
                      📄 {doc.type}
                    </span>
                  ))}
                </div>
              )}

              {/* Review panel */}
              {reviewingId === s.id && (
                <div className="mt-4 p-4 bg-muted rounded-lg space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Комментарий</label>
                    <textarea
                      value={comment} onChange={(e) => setComment(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-border bg-card text-sm"
                      rows={2} placeholder="Причина решения..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Уровень риска</label>
                    <select
                      value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)}
                      className="px-3 py-2 rounded-lg border border-border bg-card text-sm"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleReview(s.id, "approved")}
                      className="px-4 py-2 bg-success text-white rounded-lg text-sm hover:bg-success"
                    >
                      ✅ Одобрить
                    </button>
                    <button
                      onClick={() => handleReview(s.id, "rejected")}
                      className="px-4 py-2 bg-destructive text-white rounded-lg text-sm hover:opacity-90"
                    >
                      ❌ Отклонить
                    </button>
                    <button
                      onClick={() => setReviewingId(null)}
                      className="px-4 py-2 bg-slate-200 text-foreground rounded-lg text-sm"
                    >
                      Отмена
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
