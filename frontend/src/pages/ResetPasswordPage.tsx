import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { authApi, formatApiError } from "../api";
import {
  MIN_PASSWORD_LENGTH,
  PASSWORD_HINT,
  PASSWORD_PATTERN,
  PASSWORD_TITLE,
} from "../auth/passwordPolicy";
import { ErrorBox } from "../components/States";

export const ResetPasswordPage = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirm) {
      setError("Пароли не совпадают");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await authApi.resetPassword({ token, new_password: password });
      setDone(true);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <div className="card-surface mx-auto w-full max-w-md rounded-[32px] p-8 text-center">
        <h1 className="mb-3 text-xl font-semibold text-slate-900">Сброс пароля</h1>
        <p className="text-sm text-rose-600">Ссылка некорректна: отсутствует токен.</p>
        <Link to="/forgot-password" className="mt-5 inline-block text-sm text-primary-600 hover:underline">
          Запросить новую ссылку
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="card-surface mx-auto w-full max-w-md rounded-[32px] p-8 text-center">
        <h1 className="mb-3 text-xl font-semibold text-slate-900">Пароль изменён</h1>
        <p className="text-sm text-emerald-600">
          Новый пароль сохранён. Войдите в аккаунт с новым паролем.
        </p>
        <button
          type="button"
          onClick={() => navigate("/auth", { replace: true })}
          className="mt-6 inline-flex items-center justify-center rounded-xl bg-primary-500 px-4 py-2.5 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600"
        >
          Перейти ко входу
        </button>
      </div>
    );
  }

  return (
    <div className="card-surface mx-auto w-full max-w-md rounded-[32px] p-8">
      <h1 className="mb-2 text-xl font-semibold text-slate-900">Новый пароль</h1>
      <p className="mb-5 text-sm text-slate-600">Придумайте новый пароль для вашего аккаунта.</p>

      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        <div>
          <label className="mb-1 block text-xs text-slate-600">Новый пароль</label>
          <input
            type="password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            pattern={PASSWORD_PATTERN}
            title={PASSWORD_TITLE}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1"
            placeholder={PASSWORD_HINT}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-600">Повторите пароль</label>
          <input
            type="password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1"
          />
        </div>

        {error && <ErrorBox message={error} />}

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex w-full items-center justify-center rounded-xl bg-primary-500 px-4 py-2.5 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-60"
        >
          {submitting ? "Сохраняем…" : "Сохранить пароль"}
        </button>
      </form>
    </div>
  );
};
