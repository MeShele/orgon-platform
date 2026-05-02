"use client"

import { api } from "@/lib/api";;

import { useState } from "react";
import { Icon } from "@/lib/icons";
import clsx from "clsx";

interface AddMemberModalProps {
  organizationId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

type UserRole = "admin" | "operator" | "viewer";

export function AddMemberModal({ organizationId, isOpen, onClose, onSuccess }: AddMemberModalProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("viewer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.addOrganizationMember(organizationId, { user_id: 0, role } as any);
      
      
      onSuccess();
      onClose();
      
      // Reset form
      setEmail("");
      setRole("viewer");
    } catch (err: any) {
      setError(err.message || "Failed to add member");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-md rounded-xl border border-border bg-white shadow-2xl dark:border-border dark:bg-card">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border p-6 dark:border-border">
          <div>
            <h3 className="text-lg font-semibold text-foreground">
              Add Member
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Invite a user to this organization
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-muted-foreground dark:hover:bg-muted dark:hover:text-faint"
          >
            <Icon icon="solar:close-circle-linear" className="text-xl" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Email Address *
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
              placeholder="user@example.com"
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground mt-1">
              User will receive an invitation email
            </p>
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Role *
            </label>
            <div className="space-y-2">
              {[
                { value: "admin", label: "Admin", desc: "Full access to organization settings and members" },
                { value: "operator", label: "Operator", desc: "Can manage wallets and transactions" },
                { value: "viewer", label: "Viewer", desc: "Read-only access to organization data" }
              ].map((roleOption) => (
                <label
                  key={roleOption.value}
                  className={clsx(
                    "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                    role === roleOption.value
                      ? "border-slate-900 bg-muted dark:border-white dark:bg-muted"
                      : "border-border hover:bg-muted dark:border-border dark:hover:bg-muted/50"
                  )}
                >
                  <input
                    type="radio"
                    name="role"
                    value={roleOption.value}
                    checked={role === roleOption.value}
                    onChange={(e) => setRole(e.target.value as UserRole)}
                    className="mt-0.5 w-4 h-4 text-foreground"
                    disabled={loading}
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">
                      {roleOption.label}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {roleOption.desc}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-3 dark:bg-red-950/20 dark:border-red-900">
              <div className="flex items-start gap-2">
                <Icon icon="solar:danger-circle-bold" className="text-destructive text-base flex-shrink-0 mt-0.5" />
                <p className="text-xs text-red-700 dark:text-red-300">
                  {error}
                </p>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-300 text-foreground hover:bg-muted dark:border-border dark:text-faint dark:hover:bg-muted transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Icon icon="solar:refresh-linear" className="inline animate-spin mr-2" />
                  Adding...
                </>
              ) : (
                "Add Member"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
