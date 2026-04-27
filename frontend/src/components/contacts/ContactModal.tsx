"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { AnimatedModal } from "@/components/aceternity/animated-modal";
import { AnimatedInput } from "@/components/aceternity/animated-input";
import { Icon } from "@/lib/icons";
import { MovingBorderButton } from "@/components/aceternity/moving-border";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

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
    if (contact) {
      setFormData(contact);
    }
  }, [contact]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (contact?.id) {
        // Update existing contact
        await api.updateContact(contact.id, formData);
      } else {
        // Create new contact
        await api.createContact(formData);
      }
      onClose(true);
    } catch (err: any) {
      setError(err.message || "Failed to save contact");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatedModal
      isOpen={true}
      onClose={() => onClose(false)}
      title={contact ? "Edit Contact" : "Add Contact"}
      size="md"
      footer={
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => onClose(false)}
            disabled={loading}
            className="flex-1 px-4 py-2 border border-border rounded-xl hover:bg-muted font-medium transition-colors disabled:opacity-50 text-white"
          >
            Cancel
          </button>
          <MovingBorderButton
            type="submit"
            disabled={loading}
            className="flex-1"
            onClick={handleSubmit}
            duration={3000}
          >
            <span className="flex items-center justify-center gap-2">
              {loading && <Icon icon="solar:refresh-linear" className="animate-spin" />}
              {loading ? "Saving..." : contact ? "Update" : "Create"}
            </span>
          </MovingBorderButton>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Name */}
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <AnimatedInput
              label="Name"
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Alice Wallet"
              icon={<Icon icon="solar:user-linear" />}
            />
          </div>
          <div className="pt-6">
            <HelpTooltip
              text={helpContent.contacts.nameField.text}
              example={helpContent.contacts.nameField.example}
              tips={helpContent.contacts.nameField.tips}
            />
          </div>
        </div>

        {/* Address */}
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <AnimatedInput
              label="Address"
              type="text"
              required
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="0x742d35Cc..."
              className="font-mono text-xs"
              icon={<Icon icon="solar:wallet-linear" />}
            />
          </div>
          <div className="pt-6">
            <HelpTooltip
              text={helpContent.contacts.addressField.text}
              example={helpContent.contacts.addressField.example}
              tips={helpContent.contacts.addressField.tips}
            />
          </div>
        </div>

        {/* Network */}
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <AnimatedInput
              label="Network (optional)"
              type="text"
              value={formData.network || ""}
              onChange={(e) => setFormData({ ...formData, network: e.target.value })}
              placeholder="ethereum, polygon, etc."
              icon={<Icon icon="solar:layers-linear" />}
            />
          </div>
          <div className="pt-6">
            <HelpTooltip
              text={helpContent.contacts.networkField.text}
              example={helpContent.contacts.networkField.example}
              tips={helpContent.contacts.networkField.tips}
            />
          </div>
        </div>

        {/* Category */}
        <div className="flex items-start gap-2">
          <div className="relative flex-1">
            <select
              value={formData.category || ""}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  category: e.target.value as
                    | "personal"
                    | "business"
                    | "exchange"
                    | "other"
                    | undefined,
                })
              }
              className="peer w-full rounded-xl border border-border bg-card/40 px-4 pb-2 pt-6 text-sm text-white transition-all duration-300 focus:outline-none focus:ring-2 focus:border-blue-500 focus:ring-primary/30/20 appearance-none"
            >
              <option value="" className="bg-muted">
                Select category
              </option>
              <option value="personal" className="bg-muted">
                Personal
              </option>
              <option value="business" className="bg-muted">
                Business
              </option>
              <option value="exchange" className="bg-muted">
                Exchange
              </option>
              <option value="other" className="bg-muted">
                Other
              </option>
            </select>
            <label className="absolute left-4 top-2 text-xs text-muted-foreground font-medium">
              Category (optional)
            </label>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
              <Icon icon="solar:alt-arrow-down-linear" />
            </div>
          </div>
          <div className="pt-6">
            <HelpTooltip
              text={helpContent.contacts.categoryField.text}
              example={helpContent.contacts.categoryField.example}
              tips={helpContent.contacts.categoryField.tips}
            />
          </div>
        </div>

        {/* Notes */}
        <div className="flex items-start gap-2">
          <div className="relative flex-1">
            <textarea
              value={formData.notes || ""}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
              placeholder="Friend from university..."
              className="peer w-full rounded-xl border border-border bg-card/40 px-4 pb-2 pt-6 text-sm text-white transition-all duration-300 focus:outline-none focus:ring-2 focus:border-blue-500 focus:ring-primary/30/20 resize-none placeholder-transparent"
            />
            <label className="absolute left-4 top-2 text-xs text-muted-foreground font-medium">
              Notes (optional)
            </label>
          </div>
          <div className="pt-6">
            <HelpTooltip
              text={helpContent.contacts.notesField.text}
              example={helpContent.contacts.notesField.example}
              tips={helpContent.contacts.notesField.tips}
            />
          </div>
        </div>

        {/* Favorite */}
        <div className="flex items-start gap-2">
          <label className="flex-1 flex items-center gap-3 p-3 rounded-xl border border-border bg-card/20 hover:bg-card/40 transition-colors cursor-pointer group">
            <input
              type="checkbox"
              checked={formData.favorite}
              onChange={(e) =>
                setFormData({ ...formData, favorite: e.target.checked })
              }
              className="w-5 h-5 text-yellow-500 border-slate-600 rounded focus:ring-yellow-500 focus:ring-offset-slate-900 bg-muted"
            />
            <div className="flex items-center gap-2">
              <Icon
                icon={
                  formData.favorite
                    ? "solar:star-bold"
                    : "solar:star-linear"
                }
                className={`text-lg ${
                  formData.favorite ? "text-yellow-500" : "text-muted-foreground group-hover:text-yellow-500"
                } transition-colors`}
              />
              <span className="text-sm font-medium text-white">
                Mark as favorite
              </span>
            </div>
          </label>
          <div className="pt-3">
            <HelpTooltip
              text={helpContent.contacts.favoriteCheckbox.text}
              example={helpContent.contacts.favoriteCheckbox.example}
              tips={helpContent.contacts.favoriteCheckbox.tips}
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-start gap-2">
            <Icon icon="solar:danger-circle-linear" className="mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </form>
    </AnimatedModal>
  );
}
