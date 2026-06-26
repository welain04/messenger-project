interface UnreadBadgeProps {
  count: number;
  className?: string;
  size?: "sm" | "md";
}

export const UnreadBadge = ({ count, className = "", size = "md" }: UnreadBadgeProps) => {
  if (count <= 0) return null;

  const label = count > 99 ? "99+" : String(count);
  const sizeClasses =
    size === "sm"
      ? "h-4 min-w-[16px] px-0.5 text-[9px] ring-2 ring-white"
      : "h-5 min-w-[20px] px-1 text-[10px] ring-2 ring-white";

  return (
    <span
      data-testid="unread-badge"
      className={`inline-flex items-center justify-center rounded-full bg-rose-500 font-bold leading-none text-white shadow-sm ${sizeClasses} ${className}`}
      aria-label={`Непрочитанных: ${count}`}
    >
      {label}
    </span>
  );
};
