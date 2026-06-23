import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { formatApiError, usersApi } from "../api";
import type { RoleUpgradeRequest, Session, UserRole } from "../api";
import { ErrorBox, LoadingHint } from "../components/States";
import { UserAvatar } from "../components/UserAvatar";
import { invalidateUser } from "../users/userCache";

const requestStatusLabel: Record<RoleUpgradeRequest["status"], string> = {
  pending: "на рассмотрении",
  approved: "одобрена",
  rejected: "отклонена",
};

const roleLabel = (role: UserRole): string =>
  role === "student" ? "Ученик" : role === "curator" ? "Куратор" : "Администратор";

export const ProfilePage = () => {
  const { user, initializing, updateMe, logout, logoutAll, refresh } = useAuth();
  const navigate = useNavigate();

  const [nickname, setNickname] = useState(user?.nickname ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  const [roleRequests, setRoleRequests] = useState<RoleUpgradeRequest[]>([]);
  const [roleReqError, setRoleReqError] = useState<string | null>(null);
  const [roleReqSubmitting, setRoleReqSubmitting] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const [avatarSubmitting, setAvatarSubmitting] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);

  const loadSessions = async () => {
    try {
      setSessions(await usersApi.listSessions());
      setSessionsError(null);
    } catch (e) {
      setSessionsError(formatApiError(e));
    }
  };

  const loadRoleRequests = async () => {
    try {
      setRoleRequests(await usersApi.myRoleUpgradeRequests());
    } catch {
      // не критично для страницы профиля
    }
  };

  useEffect(() => {
    void loadSessions();
    void loadRoleRequests();
  }, []);

  const handleRequestUpgrade = async () => {
    setRoleReqSubmitting(true);
    setRoleReqError(null);
    try {
      await usersApi.requestRoleUpgrade();
      await loadRoleRequests();
    } catch (e) {
      setRoleReqError(formatApiError(e));
    } finally {
      setRoleReqSubmitting(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/auth", { replace: true });
  };

  const handleRevoke = async (id: string) => {
    try {
      await usersApi.revokeSession(id);
      await loadSessions();
    } catch (e) {
      setSessionsError(formatApiError(e));
    }
  };

  const handleLogoutAll = async () => {
    await logoutAll();
    navigate("/auth", { replace: true });
  };

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setPasswordError("Новый пароль и подтверждение не совпадают");
      return;
    }
    setPasswordSubmitting(true);
    setPasswordError(null);
    try {
      await usersApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      logout();
      navigate("/auth", { replace: true });
    } catch (e) {
      setPasswordError(formatApiError(e));
    } finally {
      setPasswordSubmitting(false);
    }
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

  const handleAvatarChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !user) return;
    setAvatarSubmitting(true);
    setAvatarError(null);
    try {
      await usersApi.uploadAvatar(file);
      invalidateUser(user.id);
      await refresh();
    } catch (e) {
      setAvatarError(formatApiError(e));
    } finally {
      setAvatarSubmitting(false);
      event.target.value = "";
    }
  };

  const handleAvatarDelete = async () => {
    if (!user) return;
    setAvatarSubmitting(true);
    setAvatarError(null);
    try {
      await usersApi.deleteAvatar();
      invalidateUser(user.id);
      await refresh();
    } catch (e) {
      setAvatarError(formatApiError(e));
    } finally {
      setAvatarSubmitting(false);
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
          <UserAvatar user={user} size="md" />
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-slate-900">
              {user.first_name || user.last_name
                ? `${user.first_name} ${user.last_name}`.trim()
                : user.nickname}
            </h2>
            <p className="text-xs text-slate-600">
              @{user.nickname} · Роль: {roleLabel(user.role)}
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

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Аватар
        </h3>
        <div className="flex flex-wrap items-center gap-3">
          <label className="cursor-pointer rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100">
            {avatarSubmitting ? "Загрузка…" : "Загрузить фото"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={avatarSubmitting}
              onChange={handleAvatarChange}
            />
          </label>
          {user.has_avatar && (
            <button
              type="button"
              onClick={handleAvatarDelete}
              disabled={avatarSubmitting}
              className="rounded-xl border border-rose-200 px-4 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 disabled:opacity-50"
            >
              Удалить
            </button>
          )}
        </div>
        {avatarError && (
          <div className="mt-2">
            <ErrorBox message={avatarError} />
          </div>
        )}
        <p className="mt-2 text-[11px] text-slate-500">JPEG, PNG или WebP, до 5 МБ.</p>
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
              <span className="text-[11px] text-slate-500">Имя:</span>{" "}
              {`${user.first_name} ${user.last_name}`.trim() || "—"}
            </li>
            <li>
              <span className="text-[11px] text-slate-500">Email:</span> {user.email ?? "—"}{" "}
              {user.email_verified ? (
                <span className="text-emerald-600">(подтверждён)</span>
              ) : (
                <span className="text-amber-600">(не подтверждён)</span>
              )}
            </li>
            <li>
              <span className="text-[11px] text-slate-500">Создан:</span>{" "}
              {new Date(user.created_at).toLocaleString()}
            </li>
            <li>
              <span className="text-[11px] text-slate-500">Роль:</span> {roleLabel(user.role)}
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

        <form
          onSubmit={handleChangePassword}
          className="rounded-2xl border border-slate-200 bg-white p-4 sm:col-span-2"
        >
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Сменить пароль
          </h3>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Текущий пароль</label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Новый пароль</label>
              <input
                type="password"
                required
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1"
              />
            </div>
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Подтверждение</label>
              <input
                type="password"
                required
                minLength={6}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1"
              />
            </div>
          </div>
          {passwordError && (
            <div className="mt-2">
              <ErrorBox message={passwordError} />
            </div>
          )}
          <p className="mt-2 text-[11px] text-slate-500">
            После смены пароля все активные сессии будут завершены — потребуется войти снова.
          </p>
          <button
            type="submit"
            disabled={passwordSubmitting}
            className="mt-3 inline-flex items-center justify-center rounded-xl bg-primary-500 px-4 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-60"
          >
            {passwordSubmitting ? "Сохраняем…" : "Обновить пароль"}
          </button>
        </form>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Активные сессии
          </h3>
          <button
            type="button"
            onClick={handleLogoutAll}
            className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-semibold text-slate-700 hover:bg-slate-100"
          >
            Выйти на всех устройствах
          </button>
        </div>
        {sessionsError && <div className="mb-2"><ErrorBox message={sessionsError} /></div>}
        {sessions.length === 0 ? (
          <p className="text-xs text-slate-500">Активных сессий не найдено.</p>
        ) : (
          <ul className="space-y-2">
            {sessions.map((s) => (
              <li
                key={s.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-700"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium text-slate-800">
                    {s.user_agent || "Неизвестное устройство"}
                    {s.current && (
                      <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                        текущая
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    {s.ip || "—"} · активна {new Date(s.last_seen_at).toLocaleString()}
                  </div>
                </div>
                {!s.current && (
                  <button
                    type="button"
                    onClick={() => handleRevoke(s.id)}
                    className="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-rose-600 hover:bg-rose-50"
                  >
                    Завершить
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {user.role === "student" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Роль куратора
          </h3>
          {(() => {
            const pending = roleRequests.find((r) => r.status === "pending");
            const last = roleRequests[0];
            if (pending) {
              return (
                <p className="text-xs text-slate-600">
                  Заявка на роль куратора — {requestStatusLabel.pending}. Ожидайте
                  решения администратора.
                </p>
              );
            }
            return (
              <div className="space-y-2">
                <p className="text-xs text-slate-600">
                  Вы можете запросить роль куратора. Заявку рассматривает
                  администратор.
                  {last && (
                    <span className="ml-1">
                      Предыдущая заявка: {requestStatusLabel[last.status]}.
                    </span>
                  )}
                </p>
                {roleReqError && <ErrorBox message={roleReqError} />}
                <button
                  type="button"
                  onClick={handleRequestUpgrade}
                  disabled={roleReqSubmitting}
                  className="rounded-xl bg-primary-500 px-4 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-60"
                >
                  {roleReqSubmitting ? "Отправляем…" : "Запросить роль куратора"}
                </button>
              </div>
            );
          })()}
        </div>
      )}
    </section>
  );
};
