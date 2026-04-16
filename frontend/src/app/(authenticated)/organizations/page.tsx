"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import Link from "next/link";
import clsx from "clsx";

interface Organization {
  id: string;
  name: string;
  display_name?: string;
  slug: string;
  license_type: string;
  status: string;
  address?: string;
  city?: string;
  country?: string;
  email?: string;
  max_wallets?: number;
  max_monthly_volume?: number;
  created_at: string;
}

export default function OrganizationsPage() {
  const t = useTranslations('organizations');
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'active' | 'suspended' | 'closed'>('all');

  useEffect(() => {
    loadOrganizations();
  }, [filter]);

  const loadOrganizations = async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = {};
      if (filter !== "all") params.status = filter;
      const data = await api.getOrganizations(params);
      setOrganizations(data.organizations || data || []);
    } catch (error) {
      console.error('Failed to load organizations:', error);
    } finally {
      setLoading(false);
    }
  };

  const getLicenseBadge = (license: string): "primary" | "success" | "warning" => {
    const variants: Record<string, "primary" | "success" | "warning"> = {
      free: "primary",
      pro: "warning",
      enterprise: "success"
    };
    return variants[license] || "primary";
  };

  const getStatusBadge = (status: string): "primary" | "success" | "warning" => {
    const variants: Record<string, "primary" | "success" | "warning"> = {
      active: "success",
      suspended: "warning",
      closed: "warning"
    };
    return variants[status] || "primary";
  };

  return (
    <>
      <Header title="Organizations" />
      
      <div className="p-2 sm:p-4 md:p-6 lg:p-8 space-y-4">
        {/* Filters */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilter('all')}
              className={clsx(
                "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors",
                filter === 'all'
                  ? "bg-slate-900 text-white dark:bg-white dark:text-slate-950"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
              )}
            >
              All
            </button>
            <button
              onClick={() => setFilter('active')}
              className={clsx(
                "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors",
                filter === 'active'
                  ? "bg-green-500 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
              )}
            >
              Active
            </button>
            <button
              onClick={() => setFilter('suspended')}
              className={clsx(
                "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors",
                filter === 'suspended'
                  ? "bg-yellow-500 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
              )}
            >
              Suspended
            </button>
          </div>
          
          <Link
            href="/organizations/new"
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-slate-950 dark:hover:bg-slate-200 transition-colors"
          >
            <Icon icon="solar:add-circle-linear" />
            New Organization
          </Link>
        </div>

        {/* Organizations Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <div className="p-4 space-y-3 animate-pulse">
                  <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded" />
                  <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-2/3" />
                  <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/2" />
                </div>
              </Card>
            ))}
          </div>
        ) : organizations.length === 0 ? (
          <Card>
            <div className="p-12 text-center">
              <Icon icon="solar:buildings-2-linear" className="mx-auto text-6xl text-slate-300 dark:text-slate-700 mb-4" />
              <p className="text-slate-600 dark:text-slate-400">
                No organizations found
              </p>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {organizations.map((org) => (
              <Link key={org.id} href={`/organizations/${org.id}`}>
                <Card className="h-full hover:border-slate-300 dark:hover:border-slate-700 transition-colors cursor-pointer">
                  <div className="p-4 space-y-3">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-slate-900 dark:text-white truncate">
                          {org.display_name || org.name}
                        </h3>
                        {org.city && org.country && (
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            <Icon icon="solar:map-point-linear" className="inline mr-1" />
                            {org.city}, {org.country}
                          </p>
                        )}
                      </div>
                      <Badge variant={getStatusBadge(org.status)}>
                        {org.status}
                      </Badge>
                    </div>

                    {/* License */}
                    <div className="flex items-center gap-2">
                      <Badge variant={getLicenseBadge(org.license_type)}>
                        {org.license_type}
                      </Badge>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                      <div>
                        <p className="text-xs text-slate-500 dark:text-slate-400">Max Wallets</p>
                        <p className="text-sm font-semibold text-slate-900 dark:text-white">
                          {org.max_wallets || 0}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500 dark:text-slate-400">Max Volume</p>
                        <p className="text-sm font-semibold text-slate-900 dark:text-white">
                          ${(org.max_monthly_volume || 0).toLocaleString()}
                        </p>
                      </div>
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-slate-800">
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {new Date(org.created_at).toLocaleDateString()}
                      </span>
                      <Icon 
                        icon="solar:arrow-right-linear" 
                        className="text-slate-400 dark:text-slate-600"
                      />
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
