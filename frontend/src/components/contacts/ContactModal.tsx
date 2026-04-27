"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { cn } from "@/lib/utils";

interface Contact {
  id?: number;
  name: string;
  address: string;
  network?: string;
  category?: "personal" | "business" | "exchange" | "other";
  notes?: string;
  favorite: boolean;
}

interface ContactModalProps {
  contact?: Contact | null;
  onClose: (success: boolean) => void;
}

const CATEGORIES: { value: NonNullable<Contact["category"]>; label: string }[] = [
  { value: "personal", label: "Personal" },
  { value: "business", label: "Business" },
  { value: "exchange", label: "Exchange" },
  { value: "other",    label: "Other" },
];

export default function ContactModal({ contact, onClose }: ContactModalProps) {
  const [formData, setFormData] = useState<Contact>({
    name: "",
    address: "",
    network: "",
    category: undefined,
    notes: "",
    favorite: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (contact) setFormData(contact);
  }, [contact]);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (contact?.id) {
        await api.updateContact(contact.id, formData);
      } else {
        await api.createContact(formData);
      }
      onClose(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save contact");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose(false)}>
      <DialogContent size="md">
        <DialogHeader>
          <DialogTitle>{contact ? "Edit contact" : "Add contact"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="px-5 py-5 space-y-4">
          {/* Name */}
          <FieldRow help={helpContent.contacts.nameField}>
            <Input
              label="Name"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Alice Wallet"
            />
          </FieldRow>

          {/* Address */}
          <FieldRow help={helpContent.contacts.addressField}>
            <Input
              label="Address"
              required
              mono
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="0x742d35Cc..."
            />
          </FieldRow>

          {/* Network */}
          <FieldRow help={helpContent.contacts.networkField}>
            <Input
              label="Network (optional)"
              value={formData.network || ""}
              onChange={(e) => setFormData({ ...formData, network: e.target.value })}
              placeholder="ethereum, polygon, …"
            />
          </FieldRow>

          {/* Category */}
          <FieldRow help={helpContent.contacts.categoryField}>
            <div className="w-full">
              <label className="block mb-1.5 font-mono text-[11px] tracking-[0.12em] uppercase text-faint">Category (optional)</label>
              <div className="relative">
                <select
                  value={formData.category || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      category: (e.target.value || undefined) as Contact["category"],
                    })
                  }
                  className={cn(
                    "block w-full h-10 px-3 pr-9 appearance-none",
                    "bg-card text-foreground border border-border",
                    "transition-colors duration-150",
                    "focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20",
                  )}
                >
                  <option value="">Select category</option>
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
                <Icon
                  icon="solar:alt-arrow-down-linear"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
                />
              </div>
            </div>
          </FieldRow>

          {/* Notes */}
          <FieldRow help={helpContent.contacts.notesField}>
            <div className="w-full">
              <label className="block mb-1.5 font-mono text-[11px] tracking-[0.12em] uppercase text-faint">Notes (optional)</label>
              <textarea
                value={formData.notes || ""}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={3}
                placeholder="Friend from university..."
                className={cn(
                  "block w-full px-3 py-2",
                  "bg-card text-foreground placeholder:text-faint",
                  "border border-border resize-none",
                  "transition-colors duration-150",
                  "focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20",
                )}
              />
            </div>
          </FieldRow>

          {/* Favorite */}
          <FieldRow help={helpContent.contacts.favoriteCheckbox} compact>
            <label className="flex items-center gap-3 px-3 py-2 border border-border bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors">
              <input
                type="checkbox"
                checked={formData.favorite}
                onChange={(e) => setFormData({ ...formData, favorite: e.target.checked })}
                className="w-4 h-4 accent-primary"
              />
              <Icon
                icon={formData.favorite ? "solar:star-bold" : "solar:star-linear"}
                className={cn(
                  "text-base transition-colors",
                  formData.favorite ? "text-warning" : "text-muted-foreground",
                )}
              />
              <span className="text-[13px] text-foreground">Mark as favorite</span>
            </label>
          </FieldRow>

          {error && (
            <div className="flex items-start gap-2 px-3 py-2 border border-destructive/40 bg-destructive/10 text-destructive text-[13px]">
              <Icon icon="solar:danger-circle-linear" className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => onClose(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => handleSubmit()}
            loading={loading}
          >
            {contact ? "Update" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function FieldRow({
  children,
  help,
  compact = false,
}: {
  children: React.ReactNode;
  help: { text: string; example?: string; tips?: readonly string[] };
  compact?: boolean;
}) {
  return (
    <div className="flex items-start gap-2">
      <div className="flex-1">{children}</div>
      <div className={compact ? "pt-2" : "pt-7"}>
        <HelpTooltip text={help.text} example={help.example} tips={help.tips ? [...help.tips] : undefined} />
      </div>
    </div>
  );
}
