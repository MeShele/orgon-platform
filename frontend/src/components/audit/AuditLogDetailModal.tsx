"use client";

import { format } from "date-fns";
import { Icon } from "@/lib/icons";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

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
}

interface AuditLogDetailModalProps {
  log: AuditLog;
  onClose: () => void;
}

export default function AuditLogDetailModal({ log, onClose }: AuditLogDetailModalProps) {
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

  const formatJSON = (data: any) => {
    try {
      return JSON.stringify(data, null, 2);
    } catch (e) {
      return String(data);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                <Icon 
                  icon={getActionIcon(log.action)} 
                  className="text-2xl text-blue-600 dark:text-blue-400"
                />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
                  Audit Log Details
                </h2>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={getActionVariant(log.action)}>
                    {log.action.toUpperCase()}
                  </Badge>
                  {log.resource_type && (
                    <Badge variant="gray">
                      {log.resource_type}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <Icon icon="solar:close-circle-linear" className="text-2xl text-gray-500 dark:text-gray-400" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Metadata Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400 block mb-1">
                Event ID
              </label>
              <code className="text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 rounded-lg block font-mono">
                {log.id}
              </code>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400 block mb-1">
                Timestamp
              </label>
              <div className="text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 rounded-lg">
                {log.created_at ? format(new Date(log.created_at), "MMM d, yyyy HH:mm:ss") : "—"}
              </div>
            </div>

            {log.user_id && (
              <div>
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400 block mb-1">
                  User ID
                </label>
                <code className="text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 rounded-lg block font-mono">
                  {log.user_id}
                </code>
              </div>
            )}

            {log.resource_id && (
              <div>
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400 block mb-1">
                  Resource ID
                </label>
                <code className="text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 rounded-lg block font-mono break-all">
                  {log.resource_id}
                </code>
              </div>
            )}

            {log.ip_address && (
              <div>
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400 block mb-1">
                  IP Address
                </label>
                <code className="text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 rounded-lg block font-mono">
                  {log.ip_address}
                </code>
              </div>
            )}
          </div>

          {/* User Agent */}
          {log.user_agent && (
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400 block mb-2">
                User Agent
              </label>
              <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-3">
                <code className="text-xs text-gray-900 dark:text-gray-100 font-mono break-all">
                  {log.user_agent}
                </code>
              </div>
            </div>
          )}

          {/* Details */}
          {log.details && Object.keys(log.details).length > 0 && (
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400 block mb-2">
                Additional Details
              </label>
              <div className="bg-gray-900 dark:bg-gray-950 rounded-lg p-4 overflow-x-auto">
                <pre className="text-xs text-green-400 font-mono">
                  {formatJSON(log.details)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <Button variant="primary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
