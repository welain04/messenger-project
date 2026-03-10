import { useState } from "react";
import { useNavigate } from "react-router-dom";

// Простая страница входа/регистрации.
// Здесь нет реального запроса — после сабмита просто перенаправляем пользователя в чаты.
export const AuthPage = () => {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setIsLoading(true);

    // Имитация сетевого запроса.
    setTimeout(() => {
      setIsLoading(false);
      navigate("/chats");
    }, 700);
  };

  return (
    <div className="card-surface w-full max-w-lg rounded-3xl p-6 sm:p-8">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="pill mb-2">Messenger · Online School</div>
          <h1 className="text-xl font-semibold text-slate-50 sm:text-2xl">
            Войдите в пространство общения по курсу
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Все чаты с кураторами, группой и потоком — в одном месте.
          </p>
        </div>
      </div>

      <div className="mb-4 inline-flex rounded-full bg-slate-900/60 p-1 text-xs text-slate-300">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={`flex-1 rounded-full px-4 py-1.5 transition ${
            mode === "login" ? "bg-primary-500 text-slate-50 shadow-card" : "hover:text-slate-100"
          }`}
        >
          Вход
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={`flex-1 rounded-full px-4 py-1.5 transition ${
            mode === "register" ? "bg-primary-500 text-slate-50 shadow-card" : "hover:text-slate-100"
          }`}
        >
          Регистрация
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        {mode === "register" && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-slate-300">Имя</label>
              <input
                required
                className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-50 outline-none ring-primary-500/40 placeholder:text-slate-500 focus:border-primary-500 focus:ring-1"
                placeholder="Саша"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-300">Фамилия</label>
              <input
                required
                className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-50 outline-none ring-primary-500/40 placeholder:text-slate-500 focus:border-primary-500 focus:ring-1"
                placeholder="Иванов(а)"
              />
            </div>
          </div>
        )}

        <div>
          <label className="mb-1 block text-xs text-slate-300">Email</label>
          <input
            type="email"
            required
            className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-50 outline-none ring-primary-500/40 placeholder:text-slate-500 focus:border-primary-500 focus:ring-1"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs text-slate-300">Пароль</label>
          <input
            type="password"
            required
            className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-50 outline-none ring-primary-500/40 placeholder:text-slate-500 focus:border-primary-500 focus:ring-1"
            placeholder="Минимум 8 символов"
          />
        </div>

        {mode === "register" && (
          <div>
            <label className="mb-1 block text-xs text-slate-300">Роль</label>
            <select
              className="w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-50 outline-none ring-primary-500/40 focus:border-primary-500 focus:ring-1"
              defaultValue="student"
            >
              <option value="student">Ученик</option>
              <option value="mentor">Куратор</option>
            </select>
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          className="mt-2 inline-flex w-full items-center justify-center rounded-xl bg-gradient-to-tr from-primary-500 to-fuchsia-500 px-4 py-2.5 text-sm font-semibold text-white shadow-card transition hover:from-primary-600 hover:to-fuchsia-600 disabled:opacity-60"
        >
          {isLoading ? "Входим..." : mode === "login" ? "Войти в мессенджер" : "Создать аккаунт"}
        </button>

        <p className="mt-2 text-[11px] text-slate-500">
          Для прототипа аутентификация не реализована: после нажатия кнопки вы сразу попадаете в чаты.
        </p>
      </form>
    </div>
  );
};

