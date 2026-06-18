import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { formatApiError } from "../api";

type Status = "pending" | "success" | "error";

export const VerifyEmailPage = () => {
  const [params] = useSearchParams();
  const { verifyEmail } = useAuth();
  const token = params.get("token");

  const [status, setStatus] = useState<Status>("pending");
  const [message, setMessage] = useState("Подтверждаем email…");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    if (!token) {
      setStatus("error");
      setMessage("Ссылка подтверждения некорректна: отсутствует токен.");
      return;
    }

    verifyEmail(token)
      .then(() => {
        setStatus("success");
        setMessage("Email подтверждён. Теперь доступны все возможности мессенджера.");
      })
      .catch((e) => {
        setStatus("error");
        setMessage(formatApiError(e));
      });
  }, [token, verifyEmail]);

  return (
    <div className="card-surface mx-auto w-full max-w-md rounded-[32px] p-8 text-center">
      <h1 className="mb-3 text-xl font-semibold text-slate-900">Подтверждение email</h1>
      <p
        className={`text-sm ${
          status === "success"
            ? "text-emerald-600"
            : status === "error"
            ? "text-rose-600"
            : "text-slate-500"
        }`}
      >
        {message}
      </p>
      <div className="mt-6">
        <Link
          to="/chats"
          className="inline-flex items-center justify-center rounded-xl bg-primary-500 px-4 py-2.5 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600"
        >
          Перейти к чатам
        </Link>
      </div>
    </div>
  );
};
