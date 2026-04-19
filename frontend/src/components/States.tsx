import { useEffect, useState } from "react";

export function LoadingHint({ text = "Обновление" }: { text?: string }) {
  const [dots, setDots] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setDots((d) => (d + 1) % 4), 400);
    return () => clearInterval(id);
  }, []);
  return (
    <span className="inline-flex items-center gap-1 text-xs text-slate-500">
      <span className="h-2 w-2 animate-pulse rounded-full bg-primary-500" />
      {text}
      {".".repeat(dots)}
    </span>
  );
}

interface ErrorBoxProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorBox({ message, onRetry, className }: ErrorBoxProps) {
  return (
    <div
      className={`rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 ${className ?? ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold">Не удалось выполнить запрос</div>
          <div className="mt-0.5 break-words text-red-600/90">{message}</div>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="shrink-0 rounded-full border border-red-200 bg-white px-2.5 py-0.5 text-[11px] font-medium text-red-700 hover:bg-red-100"
          >
            Повторить
          </button>
        )}
      </div>
    </div>
  );
}
