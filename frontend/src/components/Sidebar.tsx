import { Link, useLocation } from "react-router-dom";
import { useChats } from "../chats/ChatsContext";
import { useAuth } from "../auth/AuthContext";
import { ErrorBox, LoadingHint } from "./States";
import type { Chat } from "../api";
import { useUser } from "../users/userCache";

const chatBadgeClasses = (type: Chat["type"]) =>
  type === "personal" ? "bg-primary-500" : "bg-sky-500";

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

const ChatListItem = ({ chat }: { chat: Chat }) => {
  const location = useLocation();
  const { user } = useAuth();
  const isActive = location.pathname.startsWith(`/chats/${chat.id}`);

  const otherId =
    chat.type === "personal"
      ? chat.participant_ids.find((id) => id !== user?.id) ?? null
      : null;
  const otherEntry = useUser(otherId);

  const title =
    chat.type === "group"
      ? chat.title || "Без названия"
      : otherEntry?.user?.nickname
        ? otherEntry.user.nickname
        : otherId
          ? otherId.slice(0, 8) + "…"
          : "Личный чат";

  const lastText = chat.last_message?.text ?? "Сообщений пока нет";
  const lastTime = chat.last_message ? formatTime(chat.last_message.sent_at) : formatTime(chat.created_at);

  return (
    <Link
      to={`/chats/${chat.id}`}
      className={`group flex cursor-pointer items-center justify-center gap-3 rounded-xl px-1.5 py-1.5 text-sm transition
      ${isActive ? "bg-primary-50 text-primary-700" : "hover:bg-slate-100 hover:text-slate-900"} sm:justify-start sm:px-3 sm:py-2`}
    >
      <div
        className={`flex h-9 w-9 items-center justify-center rounded-2xl text-xs font-semibold text-white shadow-sm ${chatBadgeClasses(
          chat.type
        )}`}
      >
        {chat.type === "personal" ? "DM" : "GRP"}
      </div>
      <div className="hidden min-w-0 flex-1 sm:block">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-xs font-medium text-slate-900">{title}</p>
          <span className="shrink-0 text-[11px] text-slate-400">{lastTime}</span>
        </div>
        <div className="mt-0.5 flex items-center justify-between gap-2">
          <p className="truncate text-[11px] text-slate-400">{lastText}</p>
          {chat.unread_count > 0 && (
            <span className="ml-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary-500 text-[10px] font-semibold text-white">
              {chat.unread_count}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
};

export const Sidebar = () => {
  const { chats, loading, error, refresh } = useChats();

  return (
    <aside className="flex h-full w-16 flex-col gap-2 sm:mb-0 sm:w-full sm:max-w-xs sm:gap-3 sm:pr-4">
      <div className="card-surface flex h-full flex-col items-stretch rounded-2xl p-1.5 sm:p-3">
        <div className="mb-2 hidden w-full items-center justify-between gap-2 sm:flex">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {loading ? <LoadingHint text="Обновление чатов" /> : "Все чаты"}
          </span>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
            {chats.length} активных
          </span>
        </div>
        {error && (
          <div className="hidden sm:block mb-2">
            <ErrorBox message={error} onRetry={refresh} />
          </div>
        )}
        <div className="flex-1 space-y-1 overflow-y-auto pb-1">
          {!loading && !error && chats.length === 0 && (
            <p className="hidden sm:block px-2 py-3 text-[11px] text-slate-500">
              Пока нет чатов. Создайте первый на странице «Чаты».
            </p>
          )}
          {chats.map((chat) => (
            <ChatListItem key={chat.id} chat={chat} />
          ))}
        </div>
      </div>
    </aside>
  );
};
