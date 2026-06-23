import { useEffect, useState } from "react";
import { filesApi } from "../api";
import type { User, UUID } from "../api";
import { useSignedUrl } from "../hooks/useSignedUrl";
import { fullNameOf } from "../users/userCache";

const initialsOf = (user: User | undefined | null): string => {
  if (!user) return "?";
  const f = user.first_name?.[0] ?? "";
  const l = user.last_name?.[0] ?? "";
  return (f + l).toUpperCase() || user.nickname.slice(0, 2).toUpperCase();
};

interface UserAvatarProps {
  user: User | undefined | null;
  userId?: UUID | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeClasses = {
  sm: "h-9 w-9 text-xs",
  md: "h-14 w-14 text-lg",
  lg: "h-16 w-16 text-lg",
};

export const UserAvatar = ({ user, userId, size = "sm", className = "" }: UserAvatarProps) => {
  const id = userId ?? user?.id;
  const hasAvatar = user?.has_avatar ?? false;
  const [imgFailed, setImgFailed] = useState(false);
  const { url } = useSignedUrl(
    () => (id ? filesApi.avatarUrl(id) : Promise.resolve(null)),
    Boolean(id && hasAvatar && !imgFailed),
  );

  useEffect(() => {
    setImgFailed(false);
  }, [id, hasAvatar]);

  const base = `flex shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-primary-500 font-semibold text-white shadow-card ${sizeClasses[size]} ${className}`;
  const ariaLabel = user ? fullNameOf(user) : "Аватар";

  if (url && !imgFailed) {
    return (
      <img
        src={url}
        alt=""
        aria-label={ariaLabel}
        className={`${base} object-cover`}
        onError={() => setImgFailed(true)}
      />
    );
  }

  return (
    <div className={base} aria-label={ariaLabel}>
      {initialsOf(user)}
    </div>
  );
};
