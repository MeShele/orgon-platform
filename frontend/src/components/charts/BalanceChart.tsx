"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardHeader } from "@/components/common/Card";
import { api } from "@/lib/api";

export function BalanceChart({ days = 7 }: { days?: number }) {
  const [data, setData] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    api
      .getDashboardBalanceHistory(days)
      .then(setData)
      .catch(() => {});
  }, [days]);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader title="Balance History" subtitle={`Last ${days} days`} />
        <div className="flex h-48 items-center justify-center text-sm text-gray-400">
          No balance history yet. Data will appear after the first sync cycle.
        </div>
      </Card>
    );
  }

  // Group by date
  const grouped: Record<string, Record<string, number>> = {};
  for (const entry of data) {
    const date = String(entry.recorded_at).split("T")[0];
    if (!grouped[date]) grouped[date] = {};
    const token = String(entry.token);
    grouped[date][token] =
      (grouped[date][token] || 0) + parseFloat(String(entry.total_value));
  }

  const chartData = Object.entries(grouped).map(([date, tokens]) => ({
    date,
    ...tokens,
  }));

  const tokenNames = [
    ...new Set(data.map((d) => String(d.token))),
  ];

  const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

  return (
    <Card>
      <CardHeader title="Balance History" subtitle={`Last ${days} days`} />
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" fontSize={12} tick={{ fill: "#9CA3AF" }} />
            <YAxis fontSize={12} tick={{ fill: "#9CA3AF" }} />
            <Tooltip />
            <Legend />
            {tokenNames.map((token, i) => (
              <Line
                key={token}
                type="monotone"
                dataKey={token}
                stroke={colors[i % colors.length]}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
