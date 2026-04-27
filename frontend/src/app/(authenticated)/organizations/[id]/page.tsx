"use client"

import { api } from "@/lib/api";;

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/lib/icons";
import { AddMemberModal } from "@/components/organizations/AddMemberModal";
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
  phone?: string;
  max_wallets?: number;
  max_monthly_volume?: number;
  kyc_required?: boolean;
  created_at: string;
}

interface Member {
  id: string;
  user_id: number;
  email: string;
  username?: string;
  role: 'admin' | 'operator' | 'viewer';
  joined_at: string;
}

type Tab = 'overview' | 'members' | 'settings';

export default function OrganizationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const orgId = params.id as string;
  
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);

  useEffect(() => {
    loadOrganization();
    if (activeTab === 'members') {
      loadMembers();
    }
  }, [orgId, activeTab]);

  const loadOrganization = async () => {
    try {
      setLoading(true);
      const data = await api.getOrganization(orgId);
      setOrganization(data as Organization);
    } catch (error) {
      console.error('Failed to load organization:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMembers = async () => {
    try {
      const data = await api.getOrganizationMembers(orgId);
      const membersList = Array.isArray(data) ? data : (data as any)?.items || [];
      setMembers(membersList as Member[]);
    } catch (error) {
      console.error('Failed to load members:', error);
    }
  };

  const getRoleBadge = (role: string): "primary" | "success" | "warning" => {
    const variants: Record<string, "primary" | "success" | "warning"> = {
      admin: "warning",
      operator: "primary",
      viewer: "success"
    };
    return variants[role] || "primary";
  };

  if (loading) {
    return (
      <>
        <Header title="Organization" />
        <div className="p-8">
          <Card>
            <div className="p-8 animate-pulse space-y-4">
              <div className="h-8 bg-muted dark:bg-muted rounded w-1/3" />
              <div className="h-4 bg-muted dark:bg-muted rounded w-1/2" />
              <div className="h-4 bg-muted dark:bg-muted rounded w-2/3" />
            </div>
          </Card>
        </div>
      </>
    );
  }

  if (!organization) {
    return (
      <>
        <Header title="Organization Not Found" />
        <div className="p-8">
          <Card>
            <div className="p-12 text-center">
              <p className="text-muted-foreground">
                Organization not found
              </p>
              <button
                onClick={() => router.push('/organizations')}
                className="mt-4 px-4 py-2 text-sm rounded-lg bg-foreground text-background"
              >
                Back to Organizations
              </button>
            </div>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <Header title={organization.display_name || organization.name} />
      
      <div className="p-2 sm:p-4 md:p-6 lg:p-8 space-y-4">
        {/* Header Card */}
        <Card>
          <div className="p-6 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-foreground">
                  {organization.display_name || organization.name}
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {organization.slug}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={organization.status === 'active' ? 'success' : 'warning'}>
                  {organization.status}
                </Badge>
                <Badge variant="primary">
                  {organization.license_type}
                </Badge>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border">
              <div>
                <p className="text-xs text-muted-foreground">Max Wallets</p>
                <p className="text-lg font-semibold text-foreground">
                  {organization.max_wallets}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Max Volume</p>
                <p className="text-lg font-semibold text-foreground">
                  ${organization.max_monthly_volume?.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">KYC Required</p>
                <p className="text-lg font-semibold text-foreground">
                  {organization.kyc_required ? 'Yes' : 'No'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Created</p>
                <p className="text-lg font-semibold text-foreground">
                  {new Date(organization.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        </Card>

        {/* Tabs */}
        <div className="flex items-center gap-2 border-b border-border">
          <button
            onClick={() => setActiveTab('overview')}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              activeTab === 'overview'
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground dark:text-muted-foreground dark:hover:text-primary-foreground"
            )}
          >
            <Icon icon="solar:document-text-linear" className="inline mr-2" />
            Overview
          </button>
          <button
            onClick={() => setActiveTab('members')}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              activeTab === 'members'
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground dark:text-muted-foreground dark:hover:text-primary-foreground"
            )}
          >
            <Icon icon="solar:users-group-rounded-linear" className="inline mr-2" />
            Members ({members.length})
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              activeTab === 'settings'
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground dark:text-muted-foreground dark:hover:text-primary-foreground"
            )}
          >
            <Icon icon="solar:settings-linear" className="inline mr-2" />
            Settings
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <Card>
            <CardHeader title="Organization Details" />
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    Email
                  </p>
                  <p className="text-sm text-foreground">
                    {organization.email || 'Not set'}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    Phone
                  </p>
                  <p className="text-sm text-foreground">
                    {organization.phone || 'Not set'}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    Address
                  </p>
                  <p className="text-sm text-foreground">
                    {organization.address || 'Not set'}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    Location
                  </p>
                  <p className="text-sm text-foreground">
                    {organization.city}, {organization.country}
                  </p>
                </div>
              </div>
            </div>
          </Card>
        )}

        {activeTab === 'members' && (
          <Card>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">
                  Members
                </h3>
                <button 
                  onClick={() => setShowAddMemberModal(true)}
                  className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:opacity-90 dark:bg-white dark:text-foreground dark:hover:bg-muted"
                >
                  <Icon icon="solar:add-circle-linear" className="inline mr-2" />
                  Add Member
                </button>
              </div>

              <div className="space-y-2">
                {members.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-muted dark:hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-semibold">
                        {member.email.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {member.username || member.email}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {member.email}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <Badge variant={getRoleBadge(member.role)}>
                        {member.role}
                      </Badge>
                      <button className="text-muted-foreground hover:text-muted-foreground dark:hover:text-faint">
                        <Icon icon="solar:menu-dots-linear" className="text-lg" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}

        {activeTab === 'settings' && (
          <Card>
            <CardHeader title="Organization Settings" />
            <div className="p-6">
              <p className="text-sm text-muted-foreground">
                Settings panel coming soon...
              </p>
            </div>
          </Card>
        )}
      </div>

      {/* Add Member Modal */}
      <AddMemberModal
        organizationId={orgId}
        isOpen={showAddMemberModal}
        onClose={() => setShowAddMemberModal(false)}
        onSuccess={() => loadMembers()}
      />
    </>
  );
}
