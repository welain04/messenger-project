import { useState } from "react";
import { Link } from "react-router-dom";
import { authApi, formatApiError } from "../api";
import { ErrorBox } from "../components/States";

export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const res = await authApi.forgotPassword({ email: email.trim() });
      setMessage(res.detail);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card-surface mx-auto w-full max-w-md rounded-[32px] p-8">
      <h1 className="mb-2 text-xl font-semibold text-slate-900">Восстановление пароля</h1>
      <p className="mb-5 text-sm text-slate-600">
        Укажите email, который вы использовали при регистрации. Мы отправим ссылку для
        установки нового пароля.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        <div>
          <label className="mb-1 block text-xs text-slate-600">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/20 placeholder:text-slate-400 focus:border-primary-500 focus:ring-1"
            placeholder="you@example.com"
          />
        </div>

        {error && <ErrorBox message={error} />}
        {message && (
          <p className="rounded-xl bg-emerald-50 px-3 py-2 text-xs text-emerald-700">{message}</p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex w-full items-center justify-center rounded-xl bg-primary-500 px-4 py-2.5 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-60"
        >
          {submitting ? "Отправляем…" : "Отправить ссылку"}
        </button>
      </form>

      <div className="mt-5 text-center text-xs">
        <Link to="/auth" className="text-primary-600 hover:underline">
          ← Вернуться ко входу
        </Link>
      </div>
    </div>
  );
};
