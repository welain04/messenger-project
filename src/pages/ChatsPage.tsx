import { Link } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { mockChats } from "../mockData";

// Главная страница после входа: список чатов и заглушка справа.
export const ChatsPage = () => {
  const firstChat = mockChats[0];

  return (
    <div className="flex w-full flex-row gap-2 sm:gap-4">
      <Sidebar />

      <section className="card-surface flex flex-1 flex-col items-center justify-center rounded-2xl px-4 py-8 text-center sm:px-8">
        <div className="pill mb-3">Онлайн-школа · Пространство общения</div>
        <h2 className="text-xl font-semibold text-slate-50 sm:text-2xl">
          Выберите чат, чтобы продолжить диалог
        </h2>
        <p className="mt-2 max-w-md text-sm text-slate-400">
          Здесь собраны чаты с кураторами, группами и потоком. Все обсуждения по курсу остаются в одном
          защищённом пространстве.
        </p>
        {firstChat && (
          <Link
            to={`/chats/${firstChat.id}`}
            className="mt-6 inline-flex items-center justify-center rounded-full bg-primary-500/90 px-5 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600"
          >
            Открыть чат курса «{firstChat.title}»
          </Link>
        )}
      </section>
    </div>
  );
};

