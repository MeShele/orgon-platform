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
                  ? "bg-foreground text-background"
                  : "bg-muted text-muted-foreground hover:bg-muted dark:hover:bg-card"
              )}
            >
              All
            </button>
            <button
              onClick={() => setFilter('active')}
              className={clsx(
                "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors",
                filter === 'active'
                  ? "bg-success text-success-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted dark:hover:bg-card"
              )}
            >
              Active
            </button>
            <button
              onClick={() => setFilter('suspended')}
              className={clsx(
                "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors",
                filter === 'suspended'
                  ? "bg-warning text-warning-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted dark:hover:bg-card"
              )}
            >
              Suspended
            </button>
          </div>
          
          <Link
            href="/organizations/new"
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:opacity-90 dark:bg-white dark:text-foreground dark:hover:bg-muted transition-colors"
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
                  <div className="h-6 bg-muted dark:bg-muted rounded" />
                  <div className="h-4 bg-muted dark:bg-muted rounded w-2/3" />
                  <div className="h-4 bg-muted dark:bg-muted rounded w-1/2" />
                </div>
              </Card>
            ))}
          </div>
        ) : organizations.length === 0 ? (
          <Card>
            <div className="p-12 text-center">
              <Icon icon="solar:buildings-2-linear" className="mx-auto text-6xl text-faint mb-4" />
              <p className="text-muted-foreground">
                No organizations found
              </p>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {organizations.map((org) => (
              <Link key={org.id} href={`/organizations/${org.id}`}>
                <Card className="h-full hover:border-border dark:hover:border-border transition-colors cursor-pointer">
                  <div className="p-4 space-y-3">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-base font-semibold text-foreground truncate">
                          {org.display_name || org.name}
                        </h3>
                        {org.city && org.country && (
                          <p className="text-xs text-muted-foreground mt-1">
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
                    <div className="grid grid-cols-2 gap-3 pt-3 border-t border-border">
                      <div>
                        <p className="text-xs text-muted-foreground">Max Wallets</p>
                        <p className="text-sm font-semibold text-foreground">
                          {org.max_wallets || 0}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Max Volume</p>
                        <p className="text-sm font-semibold text-foreground">
                          ${(org.max_monthly_volume || 0).toLocaleString()}
                        </p>
                      </div>
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-3 border-t border-border">
                      <span className="text-xs text-muted-foreground">
                        {new Date(org.created_at).toLocaleDateString()}
                      </span>
                      <Icon 
                        icon="solar:arrow-right-linear" 
                        className="text-muted-foreground dark:text-muted-foreground"
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
