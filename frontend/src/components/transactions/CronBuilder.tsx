"use client";

import { useState, useEffect } from "react";
import { format, addMinutes } from "date-fns";

interface CronBuilderProps {
  value: string;
  onChange: (cronExpression: string) => void;
  startDate: Date;
}

export default function CronBuilder({
  value,
  onChange,
  startDate,
}: CronBuilderProps) {
  const [preset, setPreset] = useState<string>("custom");
  const [customCron, setCustomCron] = useState<string>(value || "");

  // Cron presets
  const presets = [
    { id: "daily", label: "Daily", cron: "0 10 * * *", desc: "Every day at 10:00 AM" },
    { id: "weekly", label: "Weekly", cron: "0 10 * * MON", desc: "Every Monday at 10:00 AM" },
    { id: "biweekly", label: "Bi-Weekly", cron: "0 10 */14 * *", desc: "Every 2 weeks at 10:00 AM" },
    { id: "monthly", label: "Monthly", cron: "0 10 1 * *", desc: "1st of month at 10:00 AM" },
    { id: "quarterly", label: "Quarterly", cron: "0 10 1 */3 *", desc: "Every 3 months at 10:00 AM" },
    { id: "yearly", label: "Yearly", cron: "0 10 1 1 *", desc: "Jan 1st at 10:00 AM" },
  ];

  // Update cron when preset changes
  useEffect(() => {
    if (preset !== "custom") {
      const selectedPreset = presets.find((p) => p.id === preset);
      if (selectedPreset) {
        // Adjust cron to use startDate's time
        const hour = startDate.getHours();
        const minute = startDate.getMinutes();
        const parts = selectedPreset.cron.split(" ");
        parts[0] = minute.toString();
        parts[1] = hour.toString();
        const adjustedCron = parts.join(" ");
        onChange(adjustedCron);
        setCustomCron(adjustedCron);
      }
    }
  }, [preset, startDate]);

  const handlePresetChange = (presetId: string) => {
    setPreset(presetId);
  };

  const handleCustomChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newCron = e.target.value;
    setCustomCron(newCron);
    onChange(newCron);
  };

  // Preview next executions (simplified)
  const getNextExecutions = (cron: string): string[] => {
    if (!cron || cron.split(" ").length !== 5) return [];

    try {
      const parts = cron.split(" ");
      const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;

      // Generate 3 sample execution times (simplified)
      const executions: Date[] = [];
      let current = new Date(startDate);

      // Simple logic for common patterns
      if (dayOfWeek !== "*") {
        // Weekly pattern
        for (let i = 0; i < 3; i++) {
          const next = new Date(current);
          next.setDate(next.getDate() + 7 * i);
          next.setHours(parseInt(hour) || 10);
          next.setMinutes(parseInt(minute) || 0);
          executions.push(next);
        }
      } else if (dayOfMonth === "1") {
        // Monthly pattern
        for (let i = 0; i < 3; i++) {
          const next = new Date(current);
          next.setMonth(next.getMonth() + i);
          next.setDate(1);
          next.setHours(parseInt(hour) || 10);
          next.setMinutes(parseInt(minute) || 0);
          executions.push(next);
        }
      } else {
        // Daily pattern
        for (let i = 0; i < 3; i++) {
          const next = new Date(current);
          next.setDate(next.getDate() + i);
          next.setHours(parseInt(hour) || 10);
          next.setMinutes(parseInt(minute) || 0);
          executions.push(next);
        }
      }

      return executions.map((d) =>
        format(d, "MMM d, yyyy 'at' h:mm a")
      );
    } catch {
      return [];
    }
  };

  const nextExecutions = getNextExecutions(customCron || value);

  return (
    <div className="space-y-4">
      {/* Preset Buttons */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {presets.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => handlePresetChange(p.id)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
              preset === p.id
                ? "bg-blue-600 text-white shadow-md"
                : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Selected Preset Description */}
      {preset !== "custom" && (
        <div className="p-3 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>
              {presets.find((p) => p.id === preset)?.label}:
            </strong>{" "}
            {presets.find((p) => p.id === preset)?.desc}
          </p>
        </div>
      )}

      {/* Custom Cron Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Custom Cron Expression (Optional)
        </label>
        <input
          type="text"
          value={customCron}
          onChange={handleCustomChange}
          onFocus={() => setPreset("custom")}
          placeholder="0 10 * * MON (Every Monday at 10:00 AM)"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
        />
        <p className="mt-1 text-xs text-gray-500">
          Format: minute hour day-of-month month day-of-week
        </p>
      </div>

      {/* Preview Next Executions */}
      {nextExecutions.length > 0 && (
        <div className="p-3 bg-green-50 rounded-lg">
          <p className="text-sm font-medium text-green-800 mb-2">
            📅 Next 3 Executions:
          </p>
          <ul className="space-y-1 text-sm text-green-700">
            {nextExecutions.map((exec, i) => (
              <li key={i}>
                {i + 1}. {exec}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Cron Help */}
      <details className="text-sm">
        <summary className="cursor-pointer text-gray-600 hover:text-gray-900 font-medium">
          📖 Cron Expression Guide
        </summary>
        <div className="mt-2 p-3 bg-gray-50 rounded-lg space-y-2 text-xs text-gray-700">
          <p>
            <strong>Format:</strong> minute hour day-of-month month day-of-week
          </p>
          <p>
            <strong>Examples:</strong>
          </p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>
              <code className="bg-white px-1 rounded">0 10 * * *</code> - Every day at 10:00 AM
            </li>
            <li>
              <code className="bg-white px-1 rounded">0 10 * * MON</code> - Every Monday at 10:00 AM
            </li>
            <li>
              <code className="bg-white px-1 rounded">0 10 1 * *</code> - 1st of every month at 10:00 AM
            </li>
            <li>
              <code className="bg-white px-1 rounded">0 10 15 * *</code> - 15th of every month at 10:00 AM
            </li>
            <li>
              <code className="bg-white px-1 rounded">0 10 1 1 *</code> - Jan 1st at 10:00 AM (yearly)
            </li>
          </ul>
          <p>
            <strong>Wildcards:</strong>
          </p>
          <ul className="list-disc list-inside ml-2">
            <li>
              <code className="bg-white px-1 rounded">*</code> - Every value
            </li>
            <li>
              <code className="bg-white px-1 rounded">*/n</code> - Every n-th value
            </li>
          </ul>
        </div>
      </details>
    </div>
  );
}
