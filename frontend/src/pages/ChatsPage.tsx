import { Link } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { mockChats } from "../mockData";

// Главная страница после входа: список чатов и заглушка справа.
export const ChatsPage = () => {
  const firstChat = mockChats[0];

  return (
    <div className="flex w-full flex-row gap-2 sm:gap-4">
      <Sidebar />

      <section className="card-surface relative flex flex-1 flex-col justify-center overflow-hidden rounded-2xl px-5 py-8 text-center sm:px-10">
        <div className="relative">
          <div className="pill mb-4 inline-flex">Онлайн-школа · пространство общения</div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Все чаты курса
            <span className="block text-primary-600">в одном защищённом месте</span>
          </h2>
          <p className="mt-3 mx-auto max-w-md text-sm text-slate-600">
            Выбирайте личные диалоги, групповые созвоны и чаты потоков — без шума сторонних мессенджеров.
          </p>
        </div>
        {firstChat && (
          <Link
            to={`/chats/${firstChat.id}`}
            className="relative mt-7 inline-flex items-center justify-center rounded-full bg-primary-500 px-6 py-2.5 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600"
          >
            Открыть чат курса «{firstChat.title}»
          </Link>
        )}
      </section>
    </div>
  );
};

