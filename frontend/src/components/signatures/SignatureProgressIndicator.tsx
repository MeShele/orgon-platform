"use client";

interface Props {
  signed: string[];
  waiting: string[];
  totalRequired: number;
  isComplete: boolean;
}

export function SignatureProgressIndicator({
  signed,
  waiting,
  totalRequired,
  isComplete,
}: Props) {
  const progress = `${signed.length}/${totalRequired}`;
  const percentage = (signed.length / totalRequired) * 100;

  const truncateAddress = (addr: string) => {
    if (addr.length <= 12) return addr;
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`;
  };

  return (
    <div className="space-y-2">
      {/* Progress Text */}
      <div className="flex items-center gap-2">
        <span
          className={`text-sm font-medium ${
            isComplete
              ? "text-success"
              : "text-foreground"
          }`}
        >
          {progress}
        </span>
        {isComplete && <span className="text-green-600">✓</span>}
      </div>

      {/* Progress Bar */}
      <div className="h-2 w-32 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className={`h-full transition-all duration-300 ${
            isComplete ? "bg-green-600" : "bg-blue-600"
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Details (tooltip-like) */}
      {(signed.length > 0 || waiting.length > 0) && (
        <div className="text-xs text-muted-foreground">
          {signed.length > 0 && (
            <div className="mb-1">
              <span className="font-medium">Signed:</span>
              {signed.slice(0, 2).map((addr, i) => (
                <span key={i} className="ml-1">
                  {truncateAddress(addr)}
                  {i < signed.slice(0, 2).length - 1 ? "," : ""}
                </span>
              ))}
              {signed.length > 2 && ` +${signed.length - 2} more`}
            </div>
          )}
          {waiting.length > 0 && (
            <div>
              <span className="font-medium">Waiting:</span>
              {waiting.slice(0, 2).map((addr, i) => (
                <span key={i} className="ml-1">
                  {truncateAddress(addr)}
                  {i < waiting.slice(0, 2).length - 1 ? "," : ""}
                </span>
              ))}
              {waiting.length > 2 && ` +${waiting.length - 2} more`}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
