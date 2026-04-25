// API base URL: use NEXT_PUBLIC_API_URL if set, otherwise relative URLs
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = typeof window !== "undefined" ? localStorage.getItem("orgon_refresh_token") : null;
  if (!refreshToken) return null;
  
  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem("orgon_access_token", data.access_token);
      if (data.refresh_token) localStorage.setItem("orgon_refresh_token", data.refresh_token);
      return data.access_token;
    }
    return null;
  } catch {
    return null;
  }
}

async function fetchAPI(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("orgon_access_token") : "";
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  let res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
  });

  // Auto-refresh token on 401
  if (res.status === 401 && token && !path.includes("/auth/")) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.Authorization = `Bearer ${newToken}`;
      res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { ...headers, ...options.headers },
      });
    } else {
      // Refresh failed — clear session, redirect to login
      if (typeof window !== "undefined") {
        localStorage.removeItem("orgon_access_token");
        localStorage.removeItem("orgon_refresh_token");
        localStorage.removeItem("orgon_user");
        window.location.href = "/login";
      }
    }
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// Wallets
export const api = {
  // Health
  getHealth: () => fetchAPI("/api/health"),
  getSafinaHealth: () => fetchAPI("/api/health/safina"),

  // Wallets
  getWallets: () => fetchAPI("/api/wallets"),
  getWallet: (name: string) => fetchAPI(`/api/wallets/${name}`),
  getWalletTokens: (name: string) => fetchAPI(`/api/wallets/${name}/tokens`),
  createWallet: (data: { network: string; info: string; slist?: object }) =>
    fetchAPI("/api/wallets", { method: "POST", body: JSON.stringify(data) }),
  syncWallets: () => fetchAPI("/api/wallets/sync", { method: "POST" }),

  // Transactions
  getTransactions: (limit = 50, offset = 0) =>
    fetchAPI(`/api/transactions?limit=${limit}&offset=${offset}`),
  getTransaction: (unid: string) => fetchAPI(`/api/transactions/${unid}`),
  getPendingSignatures: () => fetchAPI("/api/transactions/pending"),
  sendTransaction: (data: {
    token: string;
    to_address: string;
    value: string;
    info?: string;
  }) =>
    fetchAPI("/api/transactions", { method: "POST", body: JSON.stringify(data) }),
  signTransaction: (unid: string) =>
    fetchAPI(`/api/transactions/${unid}/sign`, { method: "POST" }),
  rejectTransaction: (unid: string, reason = "") =>
    fetchAPI(`/api/transactions/${unid}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  syncTransactions: () =>
    fetchAPI("/api/transactions/sync", { method: "POST" }),

  // Networks & Tokens
  getNetworks: () => fetchAPI("/api/networks"),
  getTokens: () => fetchAPI("/api/tokens"),
  getTokenSummary: () => fetchAPI("/api/tokens/summary"),
  getTokensInfo: () => fetchAPI("/api/tokens/info"),

  // Dashboard
  getDashboardOverview: () => fetchAPI("/api/dashboard/overview"),
  getDashboardBalanceHistory: (days = 7) =>
    fetchAPI(`/api/dashboard/balance-history?days=${days}`),

  // Dashboard (Phase 2 - new endpoints)
  getDashboardStats: () => fetchAPI("/api/dashboard/stats"),
  getDashboardRecent: (limit = 20) =>
    fetchAPI(`/api/dashboard/recent?limit=${limit}`),
  getDashboardAlerts: () => fetchAPI("/api/dashboard/alerts"),

  // Transactions (Phase 2 - enhanced)
  /** Validate transaction before sending (pre-flight check) */
  validateTransaction: (data: {
    token: string;
    to_address: string;
    value: string;
    info?: string;
  }) =>
    fetchAPI("/api/transactions/validate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Get transactions with filtering */
  getTransactionsFiltered: (params: {
    limit?: number;
    offset?: number;
    wallet?: string;
    status?: string;
    network?: string;
    from_date?: string;
    to_date?: string;
  }) => {
    const query = new URLSearchParams(
      Object.entries(params)
        .filter(([_, v]) => v !== undefined && v !== "")
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return fetchAPI(`/api/transactions?${query}`);
  },

  // Signatures (Phase 1 - new signature management endpoints)
  /** Get pending signatures (v2 - preferred over deprecated /transactions/pending) */
  getPendingSignaturesV2: () => fetchAPI("/api/signatures/pending"),

  /** Get signature history */
  getSignatureHistory: (limit = 50) =>
    fetchAPI(`/api/signatures/history?limit=${limit}`),

  /** Get signature status and progress (e.g., "2/3 signed") */
  getSignatureStatus: (txUnid: string) =>
    fetchAPI(`/api/signatures/${txUnid}/status`),

  /** Get full transaction details with signatures */
  getSignatureDetails: (txUnid: string) =>
    fetchAPI(`/api/signatures/${txUnid}/details`),

  /**
   * Sign (approve) transaction - v2
   * @deprecated Use signTransactionV2 instead of signTransaction
   */
  signTransactionV2: (txUnid: string) =>
    fetchAPI(`/api/signatures/${txUnid}/sign`, { method: "POST" }),

  /**
   * Reject transaction - v2
   * @deprecated Use rejectTransactionV2 instead of rejectTransaction
   */
  rejectTransactionV2: (txUnid: string, reason = "") =>
    fetchAPI(`/api/signatures/${txUnid}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  /** Get signature statistics */
  getSignatureStats: () => fetchAPI("/api/signatures/stats"),

  // Cache (Phase 1)
  getCacheStats: () => fetchAPI("/api/cache/stats"),
  refreshCache: () => fetchAPI("/api/cache/refresh", { method: "POST" }),

  // Contacts (Address Book)
  /** Get contacts with optional filtering */
  getContacts: (params?: {
    limit?: number;
    offset?: number;
    category?: string;
    search?: string;
    favorites_only?: boolean;
  }) => {
    const query = new URLSearchParams(
      Object.entries(params || {})
        .filter(([_, v]) => v !== undefined && v !== "")
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return fetchAPI(`/api/contacts${query ? `?${query}` : ""}`);
  },

  /** Get single contact by ID */
  getContact: (id: number) => fetchAPI(`/api/contacts/${id}`),

  /** Search contacts by name or address */
  searchContacts: (query: string, limit = 10) =>
    fetchAPI(`/api/contacts/search?q=${encodeURIComponent(query)}&limit=${limit}`),

  /** Get favorite contacts */
  getFavoriteContacts: () => fetchAPI("/api/contacts/favorites"),

  /** Create new contact */
  createContact: (data: {
    name: string;
    address: string;
    network?: string;
    category?: "personal" | "business" | "exchange" | "other";
    notes?: string;
    favorite?: boolean;
  }) =>
    fetchAPI("/api/contacts", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Update existing contact */
  updateContact: (
    id: number,
    data: {
      name?: string;
      address?: string;
      network?: string;
      category?: "personal" | "business" | "exchange" | "other";
      notes?: string;
      favorite?: boolean;
    }
  ) =>
    fetchAPI(`/api/contacts/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /** Delete contact */
  deleteContact: (id: number) =>
    fetchAPI(`/api/contacts/${id}`, { method: "DELETE" }),

  /** Toggle favorite status */
  toggleContactFavorite: (id: number) =>
    fetchAPI(`/api/contacts/${id}/toggle-favorite`, { method: "POST" }),

  // Scheduled Transactions
  /** Get scheduled transactions */
  getScheduledTransactions: (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams(
      Object.entries(params || {})
        .filter(([_, v]) => v !== undefined && v !== "")
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return fetchAPI(`/api/scheduled${query ? `?${query}` : ""}`);
  },

  /** Get single scheduled transaction */
  getScheduledTransaction: (id: number) => fetchAPI(`/api/scheduled/${id}`),

  /** Create scheduled transaction */
  createScheduledTransaction: (data: {
    token: string;
    to_address: string;
    value: string;
    scheduled_at: string;
    info?: string;
    json_info?: any;
    recurrence_rule?: string;
  }) =>
    fetchAPI("/api/scheduled", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Delete/Cancel scheduled transaction */
  deleteScheduledTransaction: (id: number) =>
    fetchAPI(`/api/scheduled/${id}`, { method: "DELETE" }),

  // Analytics
  /** Get balance history */
  getBalanceHistory: (days: number = 30) =>
    fetchAPI(`/api/analytics/balance-history?days=${days}`),

  /** Get transaction volume */
  getTransactionVolume: (network?: number) =>
    fetchAPI(`/api/analytics/transaction-volume${network ? `?network=${network}` : ""}`),

  /** Get token distribution */
  getTokenDistribution: () =>
    fetchAPI("/api/analytics/token-distribution"),

  /** Get analytics signature stats */
  getAnalyticsSignatureStats: () =>
    fetchAPI("/api/analytics/signature-stats"),

  /** Get daily trends */
  getDailyTrends: (from_date?: string, to_date?: string) => {
    const params = new URLSearchParams();
    if (from_date) params.set("from_date", from_date);
    if (to_date) params.set("to_date", to_date);
    return fetchAPI(`/api/analytics/daily-trends${params.toString() ? `?${params}` : ""}`);
  },

  /** Get network activity */
  getNetworkActivity: () =>
    fetchAPI("/api/analytics/network-activity"),

  /** Get wallet summary */
  getWalletSummary: () =>
    fetchAPI("/api/analytics/wallet-summary"),

  /** Get analytics overview (all stats) */
  getAnalyticsOverview: () =>
    fetchAPI("/api/analytics/overview"),

  // Audit Log
  /** Get audit logs */
  getAuditLogs: (params?: {
    limit?: number;
    offset?: number;
    action?: string;
    resource_type?: string;
    from_date?: string;
    to_date?: string;
  }) => {
    const query = new URLSearchParams(
      Object.entries(params || {})
        .filter(([_, v]) => v !== undefined && v !== "")
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return fetchAPI(`/api/audit/logs${query ? `?${query}` : ""}`);
  },

  /** Get resource history */
  getResourceHistory: (resourceType: string, resourceId: string, limit = 50) =>
    fetchAPI(`/api/audit/resource/${resourceType}/${resourceId}?limit=${limit}`),

  /** Get audit stats */
  getAuditStats: () =>
    fetchAPI("/api/audit/stats"),

  /** Search audit logs */
  searchAuditLogs: (query: string, limit = 50) =>
    fetchAPI(`/api/audit/search?q=${encodeURIComponent(query)}&limit=${limit}`),

  /** Create audit log entry */
  createAuditLog: (data: {
    action: string;
    resource_type?: string;
    resource_id?: string;
    details?: any;
  }) =>
    fetchAPI("/api/audit/log", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Authentication
  /** Login with email and password */
  login: (email: string, password: string) =>
    fetchAPI("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  /** Verify 2FA code and complete login */
  verify2FA: (tempToken: string, code: string) =>
    fetchAPI("/api/auth/verify-2fa", {
      method: "POST",
      body: JSON.stringify({ temp_token: tempToken, code }),
    }),

  // Two-Factor Authentication
  /** Get 2FA status */
  getTwoFactorStatus: () =>
    fetchAPI("/api/2fa/status"),

  /** Start 2FA setup (get QR code) */
  setupTwoFactor: () =>
    fetchAPI("/api/2fa/totp/setup", { method: "POST" }),

  /** Enable 2FA with verification code */
  enableTwoFactor: (verificationCode: string) =>
    fetchAPI("/api/2fa/totp/enable", {
      method: "POST",
      body: JSON.stringify({ verification_code: verificationCode }),
    }),

  /** Disable 2FA */
  disableTwoFactor: (code: string) =>
    fetchAPI("/api/2fa/totp/disable", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  /** Regenerate backup codes */
  regenerateBackupCodes: (code: string) =>
    fetchAPI("/api/2fa/backup-codes/regenerate", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  // Profile & User Management
  /** Get current user profile */
  getCurrentUser: () =>
    fetchAPI("/api/users/me"),

  /** Change password */
  changePassword: (currentPassword: string, newPassword: string) =>
    fetchAPI("/api/users/me/password", {
      method: "PUT",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    }),

  /** Get user sessions */
  getUserSessions: () =>
    fetchAPI("/api/users/me/sessions"),

  /** Revoke session */
  revokeSession: (sessionId: number) =>
    fetchAPI(`/api/users/me/sessions/${sessionId}`, {
      method: "DELETE",
    }),

  // Organizations (Multi-Tenancy)
  /** List organizations for current user */
  getOrganizations: (params?: { status?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams(
      Object.entries(params || {})
        .filter(([_, v]) => v !== undefined && v !== "")
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return fetchAPI(`/api/organizations${query ? `?${query}` : ""}`);
  },

  /** Get single organization */
  getOrganization: (id: string) => fetchAPI(`/api/organizations/${id}`),

  /** Create organization */
  createOrganization: (data: {
    name: string;
    slug: string;
    email?: string;
    phone?: string;
    city?: string;
    country?: string;
    license_type?: string;
  }) =>
    fetchAPI("/api/organizations", { method: "POST", body: JSON.stringify(data) }),

  /** Update organization */
  updateOrganization: (id: string, data: Record<string, any>) =>
    fetchAPI(`/api/organizations/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  /** Get organization members */
  getOrganizationMembers: (orgId: string, params?: { limit?: number; offset?: number }) => {
    const query = new URLSearchParams(
      Object.entries(params || {})
        .filter(([_, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return fetchAPI(`/api/organizations/${orgId}/members${query ? `?${query}` : ""}`);
  },

  /** Add member to organization */
  addOrganizationMember: (orgId: string, data: { user_id: number; role?: string }) =>
    fetchAPI(`/api/organizations/${orgId}/members`, { method: "POST", body: JSON.stringify(data) }),

  /** Update member role */
  updateMemberRole: (orgId: string, userId: number, role: string) =>
    fetchAPI(`/api/organizations/${orgId}/members/${userId}`, {
      method: "PUT",
      body: JSON.stringify({ role }),
    }),

  /** Remove member */
  removeMember: (orgId: string, userId: number) =>
    fetchAPI(`/api/organizations/${orgId}/members/${userId}`, { method: "DELETE" }),

  /** Get organization settings */
  getOrganizationSettings: (orgId: string) =>
    fetchAPI(`/api/organizations/${orgId}/settings`),

  /** Update organization settings */
  updateOrganizationSettings: (orgId: string, data: Record<string, any>) =>
    fetchAPI(`/api/organizations/${orgId}/settings`, { method: "PUT", body: JSON.stringify(data) }),

  /** Switch organization context */
  switchOrganization: (orgId: string) =>
    fetchAPI("/api/organizations/tenant/switch", { method: "POST", body: JSON.stringify({ organization_id: orgId }) }),


  // Rates
  getRates: () => fetchAPI("/api/rates"),

  // Wallet actions
  toggleWalletFavorite: (name: string) =>
    fetchAPI(`/api/wallets/${name}/favorite`, { method: "POST" }),
  updateWalletLabel: (name: string, label: string) =>
    fetchAPI(`/api/wallets/${name}/label`, { method: "PUT", body: JSON.stringify({ label }) }),

  // Fee estimation
  estimateFee: (data: { token: string; to_address: string; value: string }) =>
    fetchAPI("/api/transactions/estimate-fee", { method: "POST", body: JSON.stringify(data) }),

  // Address validation
  validateAddress: (data: { address: string; network?: number }) =>
    fetchAPI("/api/addresses/validate", { method: "POST", body: JSON.stringify(data) }),

  /** Generic GET request */
  get: (path: string) => fetchAPI(path),

  /** Generic POST request */
  post: (path: string, data?: any) =>
    fetchAPI(path, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),

  /** Generic PUT request */
  put: (path: string, data?: any) =>
    fetchAPI(path, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    }),

  /** Generic PATCH request */
  patch: (path: string, data?: any) =>
    fetchAPI(path, {
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    }),

  /** Generic DELETE request */
  delete: (path: string, data?: any) =>
    fetchAPI(path, {
      method: "DELETE",
      body: data ? JSON.stringify(data) : undefined,
    }),

  // Fiat
  getFiatRates: (crypto: string, fiat: string) =>
    fetchAPI(`/api/v1/fiat/rates/${crypto}/${fiat}`),
  createOnramp: (data: { amount: string; fiat_currency: string; crypto_currency: string }) =>
    fetchAPI("/api/v1/fiat/onramp", { method: "POST", body: JSON.stringify(data) }),
  createOfframp: (data: { amount: string; fiat_currency: string; crypto_currency: string; bank_account_id: string }) =>
    fetchAPI("/api/v1/fiat/offramp", { method: "POST", body: JSON.stringify(data) }),
  getBankAccounts: () => fetchAPI("/api/v1/fiat/bank-accounts"),
  addBankAccount: (data: { iban: string; bank_name: string; holder_name: string }) =>
    fetchAPI("/api/v1/fiat/bank-accounts", { method: "POST", body: JSON.stringify(data) }),
  getFiatTransactions: () => fetchAPI("/api/v1/fiat/transactions"),
  getFiatTransactionStatus: (txnId: string) => fetchAPI(`/api/v1/fiat/transactions/${txnId}/status`),

  // Partner API
  getPartnerVolume: () => fetchAPI("/api/v1/partner/analytics/volume"),
  getPartnerDistribution: () => fetchAPI("/api/v1/partner/analytics/distribution"),
  getPartnerFees: () => fetchAPI("/api/v1/partner/analytics/fees"),
  exportPartnerAnalytics: () => fetchAPI("/api/v1/partner/analytics/export"),
  getPartnerWallets: () => fetchAPI("/api/v1/partner/wallets"),
  getPartnerWallet: (name: string) => fetchAPI(`/api/v1/partner/wallets/${name}`),
  getPartnerTransactions: () => fetchAPI("/api/v1/partner/transactions"),
  getPartnerTransaction: (unid: string) => fetchAPI(`/api/v1/partner/transactions/${unid}`),
  signPartnerTransaction: (unid: string) =>
    fetchAPI(`/api/v1/partner/transactions/${unid}/sign`, { method: "POST" }),
  rejectPartnerTransaction: (unid: string) =>
    fetchAPI(`/api/v1/partner/transactions/${unid}/reject`, { method: "POST" }),
  getPartnerAddresses: () => fetchAPI("/api/v1/partner/addresses"),
  getPartnerAddress: (id: string) => fetchAPI(`/api/v1/partner/addresses/${id}`),
  getPartnerScheduledTransactions: () => fetchAPI("/api/v1/partner/scheduled-transactions"),
  cancelPartnerScheduledTransaction: (txId: string) =>
    fetchAPI(`/api/v1/partner/scheduled-transactions/${txId}`, { method: "DELETE" }),
  getPartnerNetworks: () => fetchAPI("/api/v1/partner/networks"),
  getPartnerTokensInfo: () => fetchAPI("/api/v1/partner/tokens-info"),
  getPartnerPendingSignatures: () => fetchAPI("/api/v1/partner/signatures/pending"),

  // Webhooks
  getWebhooks: () => fetchAPI("/api/v1/partner/webhooks"),
  getWebhookEvents: () => fetchAPI("/api/v1/partner/webhooks/events"),
  createWebhook: (data: { url: string; events: string[] }) =>
    fetchAPI("/api/v1/partner/webhooks", { method: "POST", body: JSON.stringify(data) }),
  deleteWebhook: (id: string) =>
    fetchAPI(`/api/v1/partner/webhooks/${id}`, { method: "DELETE" }),

  // Batch operations
  batchSend: (data: { transactions: Array<{ to_address: string; value: string; token: string }> }) =>
    fetchAPI("/api/transactions/batch", { method: "POST", body: JSON.stringify(data) }),
  batchSign: (data?: { transaction_ids?: string[] }) =>
    fetchAPI("/api/transactions/batch-sign", { method: "POST", body: data ? JSON.stringify(data) : undefined }),

  // Monitoring
  getMonitoringHealth: () => fetchAPI("/api/monitoring/health"),
  getMonitoringMetrics: () => fetchAPI("/api/monitoring/metrics"),

  // WhiteLabel
  getBranding: () => fetchAPI("/api/v1/whitelabel/branding"),
  updateBranding: (data: { logo_url?: string; primary_color?: string; secondary_color?: string; company_name?: string }) =>
    fetchAPI("/api/v1/whitelabel/branding", { method: "PUT", body: JSON.stringify(data) }),
  getDomains: () => fetchAPI("/api/v1/whitelabel/domains"),
  addDomain: (data: { domain: string }) =>
    fetchAPI("/api/v1/whitelabel/domains", { method: "POST", body: JSON.stringify(data) }),
  verifyDomain: (id: string) =>
    fetchAPI(`/api/v1/whitelabel/domains/${id}/verify`, { method: "POST" }),
  getEmailTemplates: () => fetchAPI("/api/v1/whitelabel/email-templates"),
  updateEmailTemplate: (type: string, data: { subject?: string; body?: string }) =>
    fetchAPI(`/api/v1/whitelabel/email-templates/${type}`, { method: "PUT", body: JSON.stringify(data) }),
};
