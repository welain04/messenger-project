import { Link, useLocation } from "react-router-dom";
import { ChatSummary, mockChats } from "../mockData";

// Возвращает классы для цветной иконки чата в зависимости от его типа.
const chatBadgeClasses = (type: ChatSummary["type"]) => {
  if (type === "direct") {
    return "bg-emerald-500/90";
  }
  if (type === "group") {
    return "bg-sky-500/90";
  }
  return "bg-gradient-to-tr from-primary-500 to-fuchsia-500";
};

// Отдельный элемент списка чата: на мобильном оставляем только иконку,
// на десктопе показываем полную информацию о чате.
const ChatListItem = ({ chat }: { chat: ChatSummary }) => {
  const location = useLocation();
  const isActive = location.pathname.startsWith(`/chats/${chat.id}`);

  return (
    <Link
      to={`/chats/${chat.id}`}
      className={`group flex cursor-pointer items-center justify-center gap-3 rounded-xl px-1.5 py-1.5 text-sm transition 
      ${isActive ? "bg-slate-800/80 text-slate-50" : "hover:bg-slate-800/40 text-slate-200"} sm:justify-start sm:px-3 sm:py-2`}
    >
      <div
        className={`flex h-9 w-9 items-center justify-center rounded-2xl text-xs font-semibold text-white shadow-card ${chatBadgeClasses(
          chat.type
        )}`}
      >
        {chat.type === "course" ? "CRS" : chat.type === "group" ? "GRP" : "DM"}
      </div>
      <div className="hidden min-w-0 flex-1 sm:block">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-xs font-medium">{chat.title}</p>
          <span className="shrink-0 text-[11px] text-slate-400">{chat.lastTime}</span>
        </div>
        <div className="mt-0.5 flex items-center justify-between gap-2">
          <p className="truncate text-[11px] text-slate-400">{chat.lastMessage}</p>
          {chat.unread > 0 && (
            <span className="ml-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary-500 text-[10px] font-semibold text-white">
              {chat.unread}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
};

// Левая колонка со списком всех чатов.
export const Sidebar = () => {
  return (
    <aside className="flex h-full w-16 flex-col gap-2 sm:mb-0 sm:w-full sm:max-w-xs sm:gap-3 sm:pr-4">
      <div className="card-surface flex h-full flex-col items-center rounded-2xl p-1.5 sm:p-3">
        <div className="mb-2 hidden w-full items-center justify-between gap-2 sm:flex">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Все чаты</span>
          <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[10px] text-slate-300">
            {mockChats.length} активных
          </span>
        </div>
        <div className="flex-1 space-y-1 overflow-y-auto pb-1">
          {mockChats.map((chat) => (
            <ChatListItem key={chat.id} chat={chat} />
          ))}
        </div>
      </div>
    </aside>
  );
};

