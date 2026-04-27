"use client";

import { useState, useEffect } from "react";
import { useTranslations } from '@/hooks/useTranslations';
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Icon } from "@/lib/icons";
import ContactModal from "@/components/contacts/ContactModal";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

interface Contact {
  id: number;
  name: string;
  address: string;
  network?: string;
  category?: "personal" | "business" | "exchange" | "other";
  notes?: string;
  favorite: boolean;
  created_at: string;
  updated_at: string;
}

export default function ContactsPage() {
  const t = useTranslations('contacts');
  const tc = useTranslations('common');
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<Contact | null>(null);

  const loadContacts = async () => {
    try {
      setLoading(true);
      const data = await api.getContacts({
        search: search || undefined,
        category: categoryFilter || undefined,
        favorites_only: showFavoritesOnly,
        limit: 100,
      });
      setContacts(data);
    } catch (error) {
      console.error("Failed to load contacts:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContacts();
  }, [search, categoryFilter, showFavoritesOnly]);

  const handleCreate = () => {
    setEditingContact(null);
    setModalOpen(true);
  };

  const handleEdit = (contact: Contact) => {
    setEditingContact(contact);
    setModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm(t('deleteConfirm'))) return;

    try {
      await api.deleteContact(id);
      await loadContacts();
    } catch (error) {
      console.error("Failed to delete contact:", error);
      alert(t('deleteContact'));
    }
  };

  const handleToggleFavorite = async (id: number) => {
    try {
      await api.toggleContactFavorite(id);
      await loadContacts();
    } catch (error) {
      console.error("Failed to toggle favorite:", error);
    }
  };

  const handleModalClose = (success: boolean) => {
    setModalOpen(false);
    setEditingContact(null);
    if (success) {
      loadContacts();
    }
  };

  // Category badge variant mapping
  const getCategoryVariant = (category?: string): "primary" | "success" | "warning" | "danger" | "gray" => {
    switch (category) {
      case "personal": return "primary";
      case "business": return "success";
      case "exchange": return "warning";
      default: return "gray";
    }
  };

  return (
    <>
      <Header title={t('title')} />
      
      <div className={pageLayout.container}>
        {/* Actions & Filters */}
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 flex items-center gap-2">
            <Input
              type="text"
              placeholder={t('searchPlaceholder')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              fullWidth
            />
            <HelpTooltip
              text={helpContent.contacts.search.text}
              example={helpContent.contacts.search.example}
              tips={helpContent.contacts.search.tips}
            />
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-4 py-2 border border-border rounded-lg bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 transition-colors"
            >
              <option value="">{t('categories.all')}</option>
              <option value="personal">{t('categories.personal')}</option>
              <option value="business">{t('categories.business')}</option>
              <option value="exchange">{t('categories.exchange')}</option>
              <option value="other">{t('categories.other')}</option>
            </select>
            <HelpTooltip
              text={helpContent.contacts.categoryFilter.text}
              example={helpContent.contacts.categoryFilter.example}
              tips={helpContent.contacts.categoryFilter.tips}
            />
          </div>

          {/* Favorites Filter */}
          <div className="flex items-center gap-2">
            <Button
              variant={showFavoritesOnly ? "warning" : "ghost"}
              onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
            >
              <Icon icon="solar:star-bold" className="mr-2" />
              {showFavoritesOnly ? t('allContacts') : t('favorites')}
            </Button>
            <HelpTooltip
              text={helpContent.contacts.favoritesFilter.text}
              example={helpContent.contacts.favoritesFilter.example}
              tips={helpContent.contacts.favoritesFilter.tips}
            />
          </div>

          {/* Add Contact Button */}
          <div className="flex items-center gap-2">
            <Button variant="primary" onClick={handleCreate}>
              <Icon icon="solar:add-circle-linear" className="mr-2" />
              {t('addContact')}
            </Button>
            <HelpTooltip
              text={helpContent.contacts.addContact.text}
              example={helpContent.contacts.addContact.example}
              tips={helpContent.contacts.addContact.tips}
            />
          </div>
        </div>

        {/* Contacts List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : contacts.length === 0 ? (
          <Card padding className="text-center py-12">
            <Icon 
              icon="solar:users-group-rounded-linear" 
              className="mx-auto mb-4 text-6xl text-muted-foreground dark:text-muted-foreground"
            />
            <h3 className="text-lg font-medium text-foreground mb-2">
              {search || categoryFilter || showFavoritesOnly
                ? t('noContactsFiltered')
                : t('noContacts')}
            </h3>
            {!search && !categoryFilter && !showFavoritesOnly && (
              <>
                <p className="text-sm text-muted-foreground mb-4">
                  {t('addFirstContact')}
                </p>
                <Button variant="primary" onClick={handleCreate}>
                  <Icon icon="solar:add-circle-linear" className="mr-2" />
                  {t('addContact')}
                </Button>
              </>
            )}
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {contacts.map((contact) => (
              <Card key={contact.id} hover padding={false} className="overflow-hidden">
                {/* Header */}
                <div className="p-4 flex items-start justify-between">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleToggleFavorite(contact.id)}
                        className="hover:scale-110 transition-transform flex-shrink-0"
                        title={contact.favorite ? t('actions.removeFromFavorites') : t('actions.addToFavorites')}
                      >
                        <Icon 
                          icon={contact.favorite ? "solar:star-bold" : "solar:star-linear"} 
                          className={`text-xl ${contact.favorite ? 'text-yellow-500' : 'text-muted-foreground'}`}
                        />
                      </button>
                      <HelpTooltip
                        text={helpContent.contacts.favoriteToggle.text}
                        example={helpContent.contacts.favoriteToggle.example}
                        tips={helpContent.contacts.favoriteToggle.tips}
                      />
                    </div>
                    <h3 className="font-semibold text-lg truncate text-foreground">
                      {contact.name}
                    </h3>
                  </div>
                  
                  {contact.category && (
                    <Badge variant={getCategoryVariant(contact.category)}>
                      {t(`categories.${contact.category}`)}
                    </Badge>
                  )}
                </div>

                {/* Body */}
                <div className="px-4 pb-4 space-y-3">
                  {/* Address */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">
                      {t('fields.address')}
                    </p>
                    <code className="text-sm bg-gray-100 dark:bg-gray-700 text-foreground px-2 py-1 rounded block truncate font-mono">
                      {contact.address}
                    </code>
                  </div>

                  {/* Network */}
                  {contact.network && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">
                        {t('fields.network')}
                      </p>
                      <p className="text-sm font-medium text-foreground">
                        {contact.network}
                      </p>
                    </div>
                  )}

                  {/* Notes */}
                  {contact.notes && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">
                        {t('fields.notes')}
                      </p>
                      <p className="text-sm text-foreground line-clamp-2">
                        {contact.notes}
                      </p>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2 p-4 pt-3 border-t border-border">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleEdit(contact)}
                    className="flex-1"
                  >
                    <Icon icon="solar:pen-linear" className="mr-1" />
                    {tc('edit')}
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleDelete(contact.id)}
                    className="flex-1"
                  >
                    <Icon icon="solar:trash-bin-trash-linear" className="mr-1" />
                    {tc('delete')}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Modal */}
        {modalOpen && (
          <ContactModal
            contact={editingContact}
            onClose={handleModalClose}
          />
        )}
      </div>
    </>
  );
}
