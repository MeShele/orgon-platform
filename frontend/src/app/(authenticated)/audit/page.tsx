"use client";

import { useState, useEffect } from "react";
import { format } from "date-fns";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { useTranslations } from '@/hooks/useTranslations';
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import AuditLogDetailModal from "@/components/audit/AuditLogDetailModal";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

interface AuditLog {
  id: number;
  user_id?: number;
  action: string;
  resource_type?: string;
  resource_id?: string;
  details?: any;
  ip_address?: string;
  user_agent?: string;
  created_at?: string;
  timestamp?: string;
}

interface AuditStats {
  total: number;
  recent_24h: number;
  by_action: Record<string, number>;
  by_resource: Record<string, number>;
}

export default function AuditPage() {
  const t = useTranslations('audit');
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [actionFilter, setActionFilter] = useState<string>("");
  const [resourceFilter, setResourceFilter] = useState<string>("");
  
  // Date filters
  const [fromDate, setFromDate] = useState<Date | null>(null);
  const [toDate, setToDate] = useState<Date | null>(null);
  
  // Pagination
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [totalLogs, setTotalLogs] = useState(0);
  
  // Detail modal
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      
      const params: any = {
        limit,
        offset,
      };
      
      if (actionFilter) params.action = actionFilter;
      if (resourceFilter) params.resource_type = resourceFilter;
      if (fromDate) params.from_date = format(fromDate, 'yyyy-MM-dd');
      if (toDate) params.to_date = format(toDate, 'yyyy-MM-dd');
      
      const [statsData, logsData] = await Promise.all([
        api.getAuditStats(),
        api.getAuditLogs(params)
      ]);
      
      setStats(statsData);
      setLogs(logsData.logs || []);
      setTotalLogs(logsData.total || logsData.logs?.length || 0);
    } catch (error) {
      console.error("Failed to load audit logs:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadAuditLogs();
      return;
    }

    try {
      setLoading(true);
      const results = await api.searchAuditLogs(searchQuery);
      setLogs(results.results || []);
      setTotalLogs(results.results?.length || 0);
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (exportFormat: 'csv' | 'json') => {
    const dataToExport = logs.map(log => ({
      id: log.id,
      timestamp: log.timestamp || log.created_at || "",
      action: log.action,
      resource_type: log.resource_type || '',
      resource_id: log.resource_id || '',
      user_id: log.user_id || '',
      ip_address: log.ip_address || '',
      details: JSON.stringify(log.details || {}),
    }));

    const timestamp = format(new Date(), 'yyyy-MM-dd');

    if (exportFormat === 'json') {
      const blob = new Blob([JSON.stringify(dataToExport, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${timestamp}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      // CSV export
      const headers = ['ID', 'Timestamp', 'Action', 'Resource Type', 'Resource ID', 'User ID', 'IP Address', 'Details'];
      const csvRows = [
        headers.join(','),
        ...dataToExport.map(row => [
          row.id,
          row.timestamp,
          row.action,
          row.resource_type,
          row.resource_id,
          row.user_id,
          row.ip_address,
          `"${row.details.replace(/"/g, '""')}"` // Escape quotes
        ].join(','))
      ];
      
      const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${timestamp}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleClearFilters = () => {
    setActionFilter("");
    setResourceFilter("");
    setSearchQuery("");
    setFromDate(null);
    setToDate(null);
    setOffset(0);
  };

  const handlePageChange = (newOffset: number) => {
    setOffset(newOffset);
  };

  const handleViewDetail = (log: AuditLog) => {
    setSelectedLog(log);
    setShowDetailModal(true);
  };

  useEffect(() => {
    loadAuditLogs();
  }, [actionFilter, resourceFilter, fromDate, toDate, limit, offset]);

  const getActionVariant = (action: string): "primary" | "success" | "warning" | "danger" | "gray" => {
    switch (action) {
      case "create": return "success";
      case "update": return "primary";
      case "delete": return "danger";
      case "sign": return "warning";
      case "reject": return "danger";
      default: return "gray";
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case "create": return "solar:add-circle-linear";
      case "update": return "solar:pen-linear";
      case "delete": return "solar:trash-bin-trash-linear";
      case "sign": return "solar:document-add-linear";
      case "reject": return "solar:close-circle-linear";
      case "view": return "solar:eye-linear";
      default: return "solar:file-text-linear";
    }
  };

  const totalPages = Math.ceil(totalLogs / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <>
      <Header title={t('title')} />
      <div className={pageLayout.container}>
        <div className="flex items-center gap-2">
          <HelpTooltip
            text="Audit log — append-only журнал всех действий пользователей и системы."
            tips={[
              "Записи никогда не редактируются и не удаляются (immutability trigger на DB-уровне).",
              "Источники: ручные действия (login, sign tx, claim alert), system events (KMS keys, webhooks).",
              "Для compliance audit регулятор может запросить выгрузку — Export CSV в правом верхнем углу.",
              "AML actions (claim/resolve/release-hold/SAR submit) — отдельные `aml.*` action-типы.",
              "B2B partner audit — отдельная таблица audit_log_b2b (см. /partner).",
            ]}
          />
          <span className="text-xs text-muted-foreground">Что это и retention policy</span>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            <Card padding hover>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">
                    {t('stats.totalEvents')}
                  </p>
                  <p className="text-2xl sm:text-3xl font-bold text-foreground">
                    {stats.total}
                  </p>
                </div>
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
                  <Icon icon="solar:chart-linear" className="text-2xl text-primary" />
                </div>
              </div>
            </Card>

            <Card padding hover>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">
                    {t('stats.last24h')}
                  </p>
                  <p className="text-2xl sm:text-3xl font-bold text-foreground">
                    {stats.recent_24h}
                  </p>
                </div>
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-success/10 rounded-full flex items-center justify-center flex-shrink-0">
                  <Icon icon="solar:clock-circle-linear" className="text-2xl text-success" />
                </div>
              </div>
            </Card>

            <Card padding hover className="sm:col-span-2 lg:col-span-1">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">
                    {t('stats.actionTypes')}
                  </p>
                  <p className="text-2xl sm:text-3xl font-bold text-foreground">
                    {Object.keys(stats.by_action).length}
                  </p>
                </div>
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-muted rounded-full flex items-center justify-center flex-shrink-0">
                  <Icon icon="solar:target-linear" className="text-2xl text-foreground" />
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card padding>
          <div className="space-y-4">
            {/* Search */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1 flex items-center gap-2">
                <Input
                  type="text"
                  placeholder={t('searchPlaceholder')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  fullWidth
                />
                <HelpTooltip
                  text={helpContent.audit.search.text}
                  example={helpContent.audit.search.example}
                  tips={helpContent.audit.search.tips}
                />
              </div>
              <Button 
                variant="primary" 
                onClick={handleSearch}
                className="sm:w-auto"
              >
                <Icon icon="solar:magnifer-linear" className="mr-2" />
                {t('searchButton')}
              </Button>
            </div>

            {/* Filters Row 1 */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1 flex items-center gap-2">
                <select
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  className="flex-1 px-4 py-2 border border-border rounded-lg bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 transition-colors"
                >
                  <option value="">{t('filters.allActions')}</option>
                  <option value="create">{t('actions.create')}</option>
                  <option value="update">{t('actions.update')}</option>
                  <option value="delete">{t('actions.delete')}</option>
                  <option value="sign">{t('actions.sign')}</option>
                  <option value="reject">{t('actions.reject')}</option>
                  <option value="view">{t('actions.view')}</option>
                </select>
                <HelpTooltip
                  text={helpContent.audit.actionFilter.text}
                  example={helpContent.audit.actionFilter.example}
                  tips={helpContent.audit.actionFilter.tips}
                />
              </div>

              <div className="flex-1 flex items-center gap-2">
                <select
                  value={resourceFilter}
                  onChange={(e) => setResourceFilter(e.target.value)}
                  className="flex-1 px-4 py-2 border border-border rounded-lg bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 transition-colors"
                >
                  <option value="">{t('filters.allResources')}</option>
                  <option value="transaction">{t('filters.resources.transaction')}</option>
                  <option value="wallet">{t('filters.resources.wallet')}</option>
                  <option value="signature">{t('filters.resources.signature')}</option>
                  <option value="contact">{t('filters.resources.contact')}</option>
                  <option value="user">{t('filters.resources.user')}</option>
                </select>
                <HelpTooltip
                  text={helpContent.audit.resourceFilter.text}
                  example={helpContent.audit.resourceFilter.example}
                  tips={helpContent.audit.resourceFilter.tips}
                />
              </div>
            </div>

            {/* Filters Row 2: Date Range */}
            <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
              <div className="flex-1 flex flex-col sm:flex-row gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <label className="block text-sm text-muted-foreground">
                      {t('filters.fromDate')}
                    </label>
                    <HelpTooltip
                      text={helpContent.audit.dateFrom.text}
                      example={helpContent.audit.dateFrom.example}
                      tips={helpContent.audit.dateFrom.tips}
                    />
                  </div>
                  <DatePicker
                    selected={fromDate}
                    onChange={(date: Date | null) => setFromDate(date)}
                    dateFormat="yyyy-MM-dd"
                    placeholderText={t('filters.selectFromDate')}
                    className="w-full px-4 py-2 border border-border rounded-lg bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                    isClearable
                  />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <label className="block text-sm text-muted-foreground">
                      {t('filters.toDate')}
                    </label>
                    <HelpTooltip
                      text={helpContent.audit.dateTo.text}
                      example={helpContent.audit.dateTo.example}
                      tips={helpContent.audit.dateTo.tips}
                    />
                  </div>
                  <DatePicker
                    selected={toDate}
                    onChange={(date: Date | null) => setToDate(date)}
                    dateFormat="yyyy-MM-dd"
                    placeholderText={t('filters.selectToDate')}
                    className="w-full px-4 py-2 border border-border rounded-lg bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                    isClearable
                    minDate={fromDate || undefined}
                  />
                </div>
              </div>

              <Button 
                variant="ghost" 
                onClick={handleClearFilters}
                className="sm:w-auto sm:mt-6"
              >
                <Icon icon="solar:refresh-linear" className="mr-2" />
                {t('clearFilters')}
              </Button>
            </div>

            {/* Export Buttons */}
            <div className="flex flex-wrap gap-3 pt-2 border-t border-border">
              <div className="flex items-center gap-2">
                <Button 
                  variant="ghost" 
                  onClick={() => handleExport('csv')}
                  size="sm"
                  disabled={logs.length === 0}
                >
                  <Icon icon="solar:file-download-linear" className="mr-2" />
                  Экспорт в CSV
                </Button>
                <HelpTooltip
                  text={helpContent.audit.exportCsv.text}
                  example={helpContent.audit.exportCsv.example}
                  tips={helpContent.audit.exportCsv.tips}
                />
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  variant="ghost" 
                  onClick={() => handleExport('json')}
                  size="sm"
                  disabled={logs.length === 0}
                >
                  <Icon icon="solar:code-file-linear" className="mr-2" />
                  Экспорт в JSON
                </Button>
                <HelpTooltip
                  text={helpContent.audit.exportJson.text}
                  example={helpContent.audit.exportJson.example}
                  tips={helpContent.audit.exportJson.tips}
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Logs List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : logs.length === 0 ? (
          <Card padding className="py-14">
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                <Icon icon="solar:history-linear" className="text-3xl text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium text-foreground mb-1">
                {t('noLogs')}
              </h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Каждое действие пользователя — логин, создание кошелька, подпись, экспорт — пишется сюда. Таблица append-only, защищена БД-триггером.
              </p>
            </div>
          </Card>
        ) : (
          <>
            <div className="space-y-3">
              {logs.map((log) => (
                <Card 
                  key={log.id} 
                  hover 
                  padding={false} 
                  className="overflow-hidden cursor-pointer"
                  onClick={() => handleViewDetail(log)}
                >
                  <div className="p-4 sm:p-6">
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex-shrink-0">
                          <Icon 
                            icon={getActionIcon(log.action)} 
                            className="text-2xl text-muted-foreground"
                          />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={getActionVariant(log.action)}>
                              {t(`actions.${log.action}`)}
                            </Badge>
                            {log.resource_type && (
                              <Badge variant="gray">
                                {t(`filters.resources.${log.resource_type}`)}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="text-xs text-muted-foreground flex-shrink-0">
                        {(() => { try { const d = new Date(log.timestamp || log.created_at || ""); return isNaN(d.getTime()) ? "—" : format(d, "MMM d, HH:mm:ss"); } catch { return "—"; } })()}
                      </div>
                    </div>

                    {/* Details Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 text-sm">
                      {log.resource_id && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">
                            {t('fields.resourceId')}
                          </p>
                          <code className="text-xs bg-muted dark:bg-muted text-foreground px-2 py-1 rounded block truncate font-mono">
                            {log.resource_id}
                          </code>
                        </div>
                      )}

                      {log.user_id && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">
                            {t('fields.userId')}
                          </p>
                          <p className="text-sm text-foreground truncate">
                            {log.user_id}
                          </p>
                        </div>
                      )}

                      {log.ip_address && (
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">
                            {t('fields.ipAddress')}
                          </p>
                          <code className="text-xs bg-muted dark:bg-muted text-foreground px-2 py-1 rounded block truncate font-mono">
                            {log.ip_address}
                          </code>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Pagination */}
            {totalLogs > limit && (
              <Card padding>
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="text-sm text-muted-foreground">
                    Показано {offset + 1}–{Math.min(offset + limit, totalLogs)} из {totalLogs}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handlePageChange(0)}
                      disabled={offset === 0}
                    >
                      <Icon icon="solar:double-alt-arrow-left-linear" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handlePageChange(Math.max(0, offset - limit))}
                      disabled={offset === 0}
                    >
                      <Icon icon="solar:alt-arrow-left-linear" />
                    </Button>
                    
                    <span className="px-4 py-2 text-sm text-foreground">
                      Страница {currentPage} из {totalPages}
                    </span>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handlePageChange(offset + limit)}
                      disabled={offset + limit >= totalLogs}
                    >
                      <Icon icon="solar:alt-arrow-right-linear" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handlePageChange((totalPages - 1) * limit)}
                      disabled={offset + limit >= totalLogs}
                    >
                      <Icon icon="solar:double-alt-arrow-right-linear" />
                    </Button>
                  </div>

                  <select
                    value={limit}
                    onChange={(e) => {
                      setLimit(Number(e.target.value));
                      setOffset(0);
                    }}
                    className="px-3 py-1 text-sm border border-border rounded-lg bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                  >
                    <option value="25">25 на странице</option>
                    <option value="50">50 на странице</option>
                    <option value="100">100 на странице</option>
                  </select>
                </div>
              </Card>
            )}
          </>
        )}
      </div>

      {/* Detail Modal */}
      {showDetailModal && selectedLog && (
        <AuditLogDetailModal
          log={selectedLog}
          onClose={() => {
            setShowDetailModal(false);
            setSelectedLog(null);
          }}
        />
      )}
    </>
  );
}
