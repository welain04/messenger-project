import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import { useChats } from "../chats/ChatsContext";
import { useAuth } from "../auth/AuthContext";
import { ErrorBox, LoadingHint } from "./States";
import { UserAvatar } from "./UserAvatar";
import { UnreadBadge } from "./UnreadBadge";
import type { Chat } from "../api";
import { useUser, fullNameOf } from "../users/userCache";

const SIDEBAR_COLLAPSED_KEY = "messenger.sidebar.collapsed";

function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function persistSidebarCollapsed(value: boolean): void {
  try {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, value ? "1" : "0");
  } catch {
    // ignore (приватный режим / SSR)
  }
}

let sidebarCollapsed = readSidebarCollapsed();
const sidebarListeners = new Set<() => void>();

function useSidebarCollapsed() {
  const [, bump] = useState(0);
  useEffect(() => {
    const notify = () => bump((n) => n + 1);
    sidebarListeners.add(notify);
    return () => {
      sidebarListeners.delete(notify);
    };
  }, []);
  return {
    collapsed: sidebarCollapsed,
    setCollapsed(next: boolean) {
      sidebarCollapsed = next;
      persistSidebarCollapsed(next);
      sidebarListeners.forEach((l) => l());
    },
  };
};

const groupInitials = (title: string | null | undefined): string => {
  const t = (title || "Группа").trim();
  const words = t.split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return t.slice(0, 2).toUpperCase();
};

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

const ChatListItem = ({ chat, compact = false }: { chat: Chat; compact?: boolean }) => {
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
      : otherEntry?.user
        ? fullNameOf(otherEntry.user)
        : otherId
          ? otherId.slice(0, 8) + "…"
          : "Личный чат";

  const lastText = chat.last_message?.text ?? "Сообщений пока нет";
  const lastTime = chat.last_message ? formatTime(chat.last_message.sent_at) : formatTime(chat.created_at);

  const hasUnread = chat.unread_count > 0;

  return (
    <Link
      to={`/chats/${chat.id}`}
      className={`group flex cursor-pointer items-center gap-3 rounded-xl px-1.5 py-1.5 text-sm transition
      ${compact ? "justify-center" : "justify-center sm:justify-start sm:px-3 sm:py-2"}
      ${isActive ? "bg-primary-50 text-primary-700" : "hover:bg-slate-100 hover:text-slate-900"}`}
    >
      <div className="relative shrink-0">
        {chat.type === "personal" ? (
          <UserAvatar user={otherEntry?.user} userId={otherId} size="sm" className="shadow-sm" />
        ) : (
          <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-sky-500 text-xs font-semibold text-white shadow-sm">
            {groupInitials(chat.title)}
          </div>
        )}
        {hasUnread && (
          <UnreadBadge
            count={chat.unread_count}
            size="md"
            className="absolute -right-1 -top-1"
          />
        )}
      </div>
      <div className={`hidden min-w-0 flex-1 ${compact ? "" : "sm:block"}`}>
        <div className="flex items-center justify-between gap-2">
          <p className={`truncate text-xs ${hasUnread ? "font-semibold text-slate-900" : "font-medium text-slate-900"}`}>
            {title}
          </p>
          <span className="shrink-0 text-[11px] text-slate-400">{lastTime}</span>
        </div>
        <div className="mt-0.5 flex items-center justify-between gap-2">
          <p className={`truncate text-[11px] ${hasUnread ? "font-medium text-slate-600" : "text-slate-400"}`}>
            {lastText}
          </p>
          {hasUnread && <UnreadBadge count={chat.unread_count} size="md" />}
        </div>
      </div>
    </Link>
  );
};

export const Sidebar = () => {
  const { chats, loading, error, refresh } = useChats();
  const { collapsed, setCollapsed } = useSidebarCollapsed();

  return (
    <aside
      className={`flex h-full w-16 shrink-0 flex-col gap-2 transition-[width] duration-300 ease-in-out sm:mb-0 ${
        collapsed ? "sm:w-16" : "sm:w-full sm:max-w-xs sm:gap-3"
      }`}
    >
      <div className={`card-surface flex h-full flex-col items-stretch rounded-2xl p-1.5 ${collapsed ? "" : "sm:p-3"}`}>
        <div className="mb-2 hidden w-full items-center justify-between gap-2 sm:flex">
          {collapsed ? (
            <button
              type="button"
              onClick={() => setCollapsed(false)}
              className="mx-auto inline-flex h-6 w-6 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              title="Развернуть список чатов"
              aria-label="Развернуть список чатов"
            >
              <ChevronRightIcon className="h-4 w-4" />
            </button>
          ) : (
            <>
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {loading ? <LoadingHint text="Обновление чатов" /> : "Все чаты"}
              </span>
              <div className="flex items-center gap-1.5">
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
                  {chats.length} активных
                </span>
                <button
                  type="button"
                  onClick={() => setCollapsed(true)}
                  className="inline-flex h-6 w-6 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
                  title="Свернуть список чатов"
                  aria-label="Свернуть список чатов"
                >
                  <ChevronLeftIcon className="h-4 w-4" />
                </button>
              </div>
            </>
          )}
        </div>
        {error && !collapsed && (
          <div className="hidden sm:block mb-2">
            <ErrorBox message={error} onRetry={refresh} />
          </div>
        )}
        <div className="flex-1 space-y-1 overflow-y-auto pb-1">
          {!loading && !error && chats.length === 0 && (
            <p className={`px-2 py-3 text-[11px] text-slate-500 ${collapsed ? "hidden" : "hidden sm:block"}`}>
              Пока нет чатов. Создайте первый на странице «Чаты».
            </p>
          )}
          {chats.map((chat) => (
            <ChatListItem key={chat.id} chat={chat} compact={collapsed} />
          ))}
        </div>
      </div>
    </aside>
  );
};
