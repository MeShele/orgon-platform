"use client";

import { useState } from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { format, addDays, addWeeks, addMonths } from "date-fns";
import CronBuilder from "./CronBuilder";

interface ScheduleModalProps {
  transaction: {
    token: string;
    to_address: string;
    value: string;
    info?: string;
  };
  onClose: (scheduled?: boolean) => void;
  onSchedule: (data: {
    scheduled_at: string;
    recurrence_rule?: string;
  }) => Promise<void>;
}

export default function ScheduleModal({
  transaction,
  onClose,
  onSchedule,
}: ScheduleModalProps) {
  const [isRecurring, setIsRecurring] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date>(
    addDays(new Date(), 1) // Default: tomorrow
  );
  const [cronExpression, setCronExpression] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data: any = {
        scheduled_at: selectedDate.toISOString(),
      };

      if (isRecurring && cronExpression) {
        data.recurrence_rule = cronExpression;
      }

      await onSchedule(data);
      onClose(true);
    } catch (err: any) {
      setError(err.message || "Failed to schedule transaction");
    } finally {
      setLoading(false);
    }
  };

  // Quick presets
  const quickPresets = [
    { label: "Tomorrow", date: addDays(new Date(), 1) },
    { label: "Next Week", date: addWeeks(new Date(), 1) },
    { label: "Next Month", date: addMonths(new Date(), 1) },
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <h2 className="text-2xl font-bold mb-2">Schedule Transaction</h2>
          <p className="text-sm text-muted-foreground">
            Send {transaction.value} to {transaction.to_address.slice(0, 10)}...
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Type Toggle */}
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setIsRecurring(false)}
              className={`flex-1 px-4 py-3 rounded-lg font-medium transition-all ${
                !isRecurring
                  ? "bg-blue-600 text-white shadow-md"
                  : "bg-gray-100 text-foreground hover:bg-gray-200"
              }`}
            >
              📅 One-Time
            </button>
            <button
              type="button"
              onClick={() => setIsRecurring(true)}
              className={`flex-1 px-4 py-3 rounded-lg font-medium transition-all ${
                isRecurring
                  ? "bg-blue-600 text-white shadow-md"
                  : "bg-gray-100 text-foreground hover:bg-gray-200"
              }`}
            >
              🔄 Recurring
            </button>
          </div>

          {/* Date & Time Picker */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              {isRecurring ? "Start Date & Time" : "Execution Date & Time"}
            </label>

            <div className="space-y-3">
              {/* DatePicker */}
              <DatePicker
                selected={selectedDate}
                onChange={(date: Date | null) => date && setSelectedDate(date)}
                showTimeSelect
                timeFormat="HH:mm"
                timeIntervals={15}
                dateFormat="MMMM d, yyyy h:mm aa"
                minDate={new Date()}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
                calendarClassName="shadow-lg"
              />

              {/* Quick Presets */}
              <div className="flex gap-2">
                {quickPresets.map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => setSelectedDate(preset.date)}
                    className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              {/* Selected Date Display */}
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Scheduled for:</strong>{" "}
                  {format(selectedDate, "EEEE, MMMM d, yyyy 'at' h:mm a")}
                </p>
              </div>
            </div>
          </div>

          {/* Recurring Settings */}
          {isRecurring && (
            <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-lg">🔄</span>
                <h3 className="font-semibold">Recurrence Settings</h3>
              </div>

              <CronBuilder
                value={cronExpression}
                onChange={setCronExpression}
                startDate={selectedDate}
              />
            </div>
          )}

          {/* Transaction Details Summary */}
          <div className="p-4 bg-gray-50 rounded-lg space-y-2">
            <h3 className="font-semibold mb-2">Transaction Details</h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Amount:</span>
                <span className="font-medium">{transaction.value}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Token:</span>
                <span className="font-medium">{transaction.token}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">To:</span>
                <code className="text-xs bg-white px-2 py-1 rounded">
                  {transaction.to_address.slice(0, 15)}...
                </code>
              </div>
              {transaction.info && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Note:</span>
                  <span className="font-medium">{transaction.info}</span>
                </div>
              )}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={() => onClose(false)}
              disabled={loading}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-muted font-medium transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || (isRecurring && !cronExpression)}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading
                ? "Scheduling..."
                : isRecurring
                ? "Schedule Recurring Payment"
                : "Schedule Payment"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
