import { Link, useParams } from "react-router-dom";
import { UserAvatar } from "../components/UserAvatar";
import { useUser, fullNameOf } from "../users/userCache";
import { ErrorBox, LoadingHint } from "../components/States";
import type { UserRole } from "../api";

const roleLabel = (role: UserRole): string =>
  role === "student" ? "Ученик" : role === "curator" ? "Куратор" : "Администратор";

const formatDate = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
};

export const UserProfilePage = () => {
  const { userId } = useParams<{ userId: string }>();
  const entry = useUser(userId);

  return (
    <div className="mx-auto w-full max-w-xl">
      <Link to="/chats" className="mb-3 inline-block text-xs text-primary-600 hover:underline">
        ← Назад к чатам
      </Link>

      <section className="card-surface rounded-2xl p-5">
        {!entry || entry.status === "loading" ? (
          <LoadingHint text="Загрузка профиля" />
        ) : entry.status === "error" || !entry.user ? (
          <ErrorBox message={entry.error ?? "Пользователь не найден"} />
        ) : (
          <>
            <div className="flex items-center gap-4">
              <UserAvatar user={entry.user} userId={entry.user.id} size="lg" />
              <div className="min-w-0">
                <h2 className="truncate text-lg font-semibold text-slate-900">
                  {fullNameOf(entry.user)}
                </h2>
                <p className="truncate text-sm text-slate-400">@{entry.user.nickname}</p>
              </div>
            </div>

            <dl className="mt-5 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-slate-400">Имя</dt>
                <dd className="text-slate-900">{entry.user.first_name || "—"}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-slate-400">Фамилия</dt>
                <dd className="text-slate-900">{entry.user.last_name || "—"}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-slate-400">Никнейм</dt>
                <dd className="text-slate-900">@{entry.user.nickname}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-slate-400">Роль</dt>
                <dd className="text-slate-900">{roleLabel(entry.user.role)}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wide text-slate-400">В системе с</dt>
                <dd className="text-slate-900">{formatDate(entry.user.created_at)}</dd>
              </div>
            </dl>
          </>
        )}
      </section>
    </div>
  );
};
