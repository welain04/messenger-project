import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { formatApiError } from "../api";
import { ErrorBox, LoadingHint } from "../components/States";

export const ProfilePage = () => {
  const { user, initializing, updateMe, logout } = useAuth();
  const navigate = useNavigate();

  const [nickname, setNickname] = useState(user?.nickname ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  const handleLogout = () => {
    logout();
    navigate("/auth", { replace: true });
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!nickname.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await updateMe({ nickname: nickname.trim() });
      setSavedAt(new Date());
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (initializing) {
    return (
      <section className="card-surface flex w-full items-center justify-center rounded-2xl p-10">
        <LoadingHint text="Загрузка профиля" />
      </section>
    );
  }

  if (!user) {
    return (
      <section className="card-surface w-full rounded-2xl p-6">
        <ErrorBox message="Пользователь не загружен. Перезайдите в систему." />
      </section>
    );
  }

  return (
    <section className="card-surface flex w-full flex-col gap-5 rounded-2xl p-4 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-500 text-lg font-semibold text-white shadow-card">
            {user.nickname[0]?.toUpperCase()}
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-slate-900">Профиль: {user.nickname}</h2>
            <p className="text-xs text-slate-600">
              Роль: {user.role === "student" ? "Ученик" : "Куратор"} · ID&nbsp;
              <span className="font-mono text-[11px] text-slate-500">{user.id}</span>
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="self-start rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
        >
          Выйти
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Сменить никнейм
          </h3>
          <div>
            <label className="mb-1 block text-[11px] text-slate-500">Никнейм</label>
            <input
              required
              minLength={3}
              maxLength={30}
              pattern="[A-Za-z0-9_]+"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1"
            />
          </div>
          {error && <div className="mt-2"><ErrorBox message={error} /></div>}
          <div className="mt-3 flex items-center gap-3">
            <button
              type="submit"
              disabled={submitting || nickname.trim() === user.nickname}
              className="inline-flex items-center justify-center rounded-xl bg-primary-500 px-4 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-60"
            >
              {submitting ? "Сохраняем…" : "Сохранить"}
            </button>
            {savedAt && !submitting && (
              <span className="text-[11px] text-emerald-600">
                Сохранено в {savedAt.toLocaleTimeString()}
              </span>
            )}
          </div>
        </form>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Информация
          </h3>
          <ul className="space-y-2 text-xs text-slate-700">
            <li>
              <span className="text-[11px] text-slate-500">Создан:</span>{" "}
              {new Date(user.created_at).toLocaleString()}
            </li>
            <li>
              <span className="text-[11px] text-slate-500">Роль:</span> {user.role}
            </li>
            <li>
              <span className="text-[11px] text-slate-500">UUID:</span>{" "}
              <span className="font-mono text-[11px]">{user.id}</span>
            </li>
          </ul>
          <p className="mt-3 text-[11px] text-slate-500">
            UUID можно скопировать и использовать в форме создания чата для добавления собеседника.
          </p>
        </div>
      </div>
    </section>
  );
};
