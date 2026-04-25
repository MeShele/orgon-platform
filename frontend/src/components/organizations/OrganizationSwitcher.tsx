"use client";

import { useState, useEffect } from "react";
import { Icon } from "@/lib/icons";
import { useTranslations } from "@/hooks/useTranslations";
import { api } from "@/lib/api";
import clsx from "clsx";

interface Organization {
  id: string;
  name: string;
  display_name?: string;
  license_type: string;
  status: string;
}

export function OrganizationSwitcher() {
  const t = useTranslations('organizations');
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [currentOrg, setCurrentOrg] = useState<Organization | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOrganizations();
  }, []);

  const loadOrganizations = async () => {
    try {
      setLoading(true);
      const data = await api.getOrganizations();
      const orgs = Array.isArray(data) ? data : [];
      setOrganizations(orgs);

      if (orgs.length > 0 && !currentOrg) {
        setCurrentOrg(orgs[0]);
      }
    } catch (error) {
      console.error('Failed to load organizations:', error);
    } finally {
      setLoading(false);
    }
  };

  const switchOrganization = async (org: Organization) => {
    try {
      try { await api.switchOrganization(org.id); } catch (err) { console.error('Switch failed:', err); }
      // await api.post('/api/organizations/tenant/switch', { organization_id: org.id });
      
      setCurrentOrg(org);
      setIsOpen(false);
      
      // Reload page to refresh data for new organization
      // window.location.reload();
    } catch (error) {
      console.error('Failed to switch organization:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-slate-500 dark:text-slate-400">
        <Icon icon="solar:buildings-2-linear" className="text-sm animate-pulse" />
        <span className="hidden sm:inline">Loading...</span>
      </div>
    );
  }

  if (organizations.length === 0) {
    return null;
  }

  // Single organization - no need for switcher
  if (organizations.length === 1) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 px-3 py-1.5">
        <Icon icon="solar:buildings-2-linear" className="text-sm text-slate-600 dark:text-slate-400" />
        <span className="text-xs font-medium text-slate-900 dark:text-white hidden sm:inline">
          {organizations[0].display_name || organizations[0].name}
        </span>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          "flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
          isOpen
            ? "border-slate-900 bg-slate-100 dark:border-white dark:bg-slate-800"
            : "border-slate-200 bg-white hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900/50 dark:hover:bg-slate-800"
        )}
      >
        <Icon icon="solar:buildings-2-linear" className="text-sm" />
        <span className="hidden sm:inline max-w-[120px] truncate">
          {currentOrg?.display_name || currentOrg?.name || 'Select Organization'}
        </span>
        <Icon 
          icon={isOpen ? "solar:alt-arrow-up-linear" : "solar:alt-arrow-down-linear"} 
          className="text-xs"
        />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute left-0 top-full mt-2 w-64 rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900 z-50">
            <div className="p-2">
              <div className="px-3 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Organizations
              </div>
              
              <div className="space-y-1">
                {organizations.map((org) => (
                  <button
                    key={org.id}
                    onClick={() => switchOrganization(org)}
                    className={clsx(
                      "w-full flex items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors",
                      currentOrg?.id === org.id
                        ? "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-white"
                        : "text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/50"
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">
                        {org.display_name || org.name}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400 capitalize">
                        {org.license_type}
                      </div>
                    </div>
                    
                    {currentOrg?.id === org.id && (
                      <Icon 
                        icon="solar:check-circle-bold" 
                        className="text-green-500 flex-shrink-0" 
                      />
                    )}
                  </button>
                ))}
              </div>
              
              <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                <a
                  href="/organizations"
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-800/50 transition-colors"
                  onClick={() => setIsOpen(false)}
                >
                  <Icon icon="solar:settings-linear" className="text-base" />
                  Manage Organizations
                </a>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
