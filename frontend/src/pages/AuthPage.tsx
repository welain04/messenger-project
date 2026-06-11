import { useState } from "react";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { formatApiError } from "../api";
import type { UserRole } from "../api";
import { ErrorBox } from "../components/States";

type Mode = "login" | "register";

export const AuthPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("student");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login({ nickname, password });
      } else {
        await register({ nickname, password, role });
      }
      const redirectTo = (location.state as { from?: string } | null)?.from ?? "/chats";
      navigate(redirectTo, { replace: true });
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card-surface w-full max-w-xl rounded-[32px] p-6 sm:p-8">
      <div className="mb-6 space-y-3 text-center sm:text-left">
        <div className="pill mx-auto sm:mx-0">Messenger · Online School</div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          Пространство общения
          <span className="block text-primary-600">между учениками и кураторами</span>
        </h1>
        <p className="text-sm text-slate-600">
          Личные диалоги, групповые чаты потоков и команды проектов — в одном защищённом мессенджере.
        </p>
      </div>

      <div className="mb-5 inline-flex rounded-full bg-slate-100 p-1 text-[11px] text-slate-500">
        <button
          type="button"
          onClick={() => { setMode("login"); setError(null); setShowPassword(false); }}
          className={`flex-1 rounded-full px-4 py-1.5 transition ${
            mode === "login" ? "bg-primary-500 text-white shadow-card" : "hover:text-slate-900"
          }`}
        >
          Вход
        </button>
        <button
          type="button"
          onClick={() => { setMode("register"); setError(null); setShowPassword(false); }}
          className={`flex-1 rounded-full px-4 py-1.5 transition ${
            mode === "register" ? "bg-primary-500 text-white shadow-card" : "hover:text-slate-900"
          }`}
        >
          Регистрация
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        <div>
          <label className="mb-1 block text-xs text-slate-600">Никнейм</label>
          <input
            required
            minLength={3}
            maxLength={30}
            pattern="[A-Za-z0-9_]+"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/20 placeholder:text-slate-400 focus:border-primary-500 focus:ring-1"
            placeholder="alice (буквы, цифры, _, 3–30 симв.)"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs text-slate-600">Пароль</label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-3 pr-10 text-sm text-slate-900 outline-none ring-primary-500/20 placeholder:text-slate-400 focus:border-primary-500 focus:ring-1"
              placeholder="минимум 6 символов"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
              title={showPassword ? "Скрыть пароль" : "Показать пароль"}
            >
              {showPassword ? (
                <EyeSlashIcon className="h-4 w-4" aria-hidden="true" />
              ) : (
                <EyeIcon className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {mode === "register" && (
          <div>
            <label className="mb-1 block text-xs text-slate-600">Роль</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/20 focus:border-primary-500 focus:ring-1"
            >
              <option value="student">Ученик</option>
              <option value="curator">Куратор</option>
            </select>
          </div>
        )}

        {error && <ErrorBox message={error} />}

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 inline-flex w-full items-center justify-center rounded-xl bg-primary-500 px-4 py-2.5 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-60"
        >
          {submitting
            ? mode === "login" ? "Входим…" : "Создаём аккаунт…"
            : mode === "login" ? "Войти в мессенджер" : "Создать аккаунт"}
        </button>
      </form>
    </div>
  );
};
