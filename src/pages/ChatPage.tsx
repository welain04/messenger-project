import { useParams } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { currentUser, mockChats, mockMessages } from "../mockData";

// Сообщение в списке с простым визуальным разделением своих и чужих сообщений.
const MessageBubble = ({
  text,
  time,
  isOwn
}: {
  text: string;
  time: string;
  isOwn: boolean;
}) => {
  return (
    <div className={`flex w-full ${isOwn ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-3 py-2 text-xs shadow-sm ${
          isOwn
            ? "rounded-br-sm bg-primary-500 text-slate-50"
            : "rounded-bl-sm bg-slate-800/80 text-slate-100 border border-slate-700/80"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{text}</p>
        <div className="mt-1 flex justify-end text-[10px] text-slate-200/80">{time}</div>
      </div>
    </div>
  );
};

// Поле ввода сообщения c «заглушкой» отправки.
const MessageInput = () => {
  return (
    <div className="border-t border-slate-800/80 p-3">
      <div className="flex items-end gap-2">
        <textarea
          rows={1}
          className="min-h-[44px] flex-1 resize-none rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-xs text-slate-50 outline-none ring-primary-500/40 placeholder:text-slate-500 focus:border-primary-500 focus:ring-1"
          placeholder="Напишите сообщение куратору или группе..."
        />
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600"
        >
          ➤
        </button>
      </div>
      <p className="mt-1 text-[10px] text-slate-500">
        В прототипе отправка сообщения не реализована — кнопка демонстрирует только структуру интерфейса.
      </p>
    </div>
  );
};

// Страница конкретного чата: список сообщений + поле ввода.
export const ChatPage = () => {
  const { chatId } = useParams<{ chatId: string }>();
  const chat = mockChats.find((c) => c.id === chatId);
  const messages = mockMessages.filter((m) => m.chatId === chatId);

  const getChatBadgeClasses = (type: "direct" | "group" | "course") => {
    if (type === "direct") {
      return "bg-emerald-500/90";
    }
    if (type === "group") {
      return "bg-sky-500/90";
    }
    return "bg-gradient-to-tr from-primary-500 to-fuchsia-500";
  };

  if (!chat) {
    return (
      <div className="flex w-full flex-row gap-2 sm:gap-4">
        <Sidebar />
        <section className="card-surface flex flex-1 items-center justify-center rounded-2xl">
          <p className="text-sm text-slate-300">Чат не найден. Вернитесь к списку чатов.</p>
        </section>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-row gap-2 sm:gap-4">
      <Sidebar />
      <section className="card-surface flex flex-1 flex-col rounded-2xl">
        <header className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-9 w-9 items-center justify-center rounded-2xl text-xs font-semibold text-white shadow-card ${getChatBadgeClasses(
                chat.type
              )}`}
            >
              {chat.type === "course" ? "CRS" : chat.type === "group" ? "GRP" : "DM"}
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-50">{chat.title}</p>
              <p className="text-[11px] text-slate-400">Кураторы и ученики курса общаются здесь</p>
            </div>
          </div>
          <div className="hidden text-[11px] text-slate-400 sm:block">
            В сети: <span className="font-medium text-emerald-300">{currentUser.name}</span> и куратор
          </div>
        </header>

        <div className="flex-1 space-y-2 overflow-y-auto px-4 py-3 text-xs">
          <div className="mb-1 flex justify-center">
            <span className="rounded-full bg-slate-900/80 px-3 py-0.5 text-[10px] text-slate-400">
              Сегодня
            </span>
          </div>
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              text={message.text}
              time={message.createdAt}
              isOwn={message.isOwn}
            />
          ))}
        </div>

        <MessageInput />
      </section>
    </div>
  );
};

