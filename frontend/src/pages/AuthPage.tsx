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
          onClick={() => setMode("login")}
          className={`flex-1 rounded-full px-4 py-1.5 transition ${
            mode === "login" ? "bg-primary-500 text-white shadow-card" : "hover:text-slate-900"
          }`}
        >
          Вход
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={`flex-1 rounded-full px-4 py-1.5 transition ${
            mode === "register" ? "bg-primary-500 text-white shadow-card" : "hover:text-slate-900"
          }`}
        >
          Регистрация
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        {mode === "register" && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-slate-600">Имя</label>
              <input
                required
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/20 placeholder:text-slate-400 focus:border-primary-500 focus:ring-1"
                placeholder="Саша"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-600">Фамилия</label>
              <input
                required
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/20 placeholder:text-slate-400 focus:border-primary-500 focus:ring-1"
                placeholder="Иванов(а)"
              />
            </div>
          </div>
        )}

        <div>
          <label className="mb-1 block text-xs text-slate-600">Email</label>
          <input
            type="email"
            required
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/20 placeholder:text-slate-400 focus:border-primary-500 focus:ring-1"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs text-slate-600">Пароль</label>
          <input
            type="password"
            required
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/20 placeholder:text-slate-400 focus:border-primary-500 focus:ring-1"
            placeholder="Минимум 8 символов"
          />
        </div>

        {mode === "register" && (
          <div>
            <label className="mb-1 block text-xs text-slate-600">Роль</label>
            <select
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none ring-primary-500/20 focus:border-primary-500 focus:ring-1"
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
          className="mt-2 inline-flex w-full items-center justify-center rounded-xl bg-primary-500 px-4 py-2.5 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-60"
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

