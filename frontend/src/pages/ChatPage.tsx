import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { useAuth } from "../auth/AuthContext";
import { useChats } from "../chats/ChatsContext";
import { chatsApi, messagesApi, formatApiError } from "../api";
import type { Chat, Message } from "../api";
import { ErrorBox, LoadingHint } from "../components/States";
import { useUser, fullNameOf } from "../users/userCache";

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

const MessageBubble = ({ message, isOwn }: { message: Message; isOwn: boolean }) => (
  <div className={`flex w-full ${isOwn ? "justify-end" : "justify-start"}`}>
    <div
      className={`max-w-[80%] rounded-2xl px-3 py-2 text-xs shadow-sm ${
        isOwn
          ? "rounded-br-sm bg-primary-500 text-white"
          : "rounded-bl-sm bg-slate-100 text-slate-900 border border-slate-200"
      }`}
    >
      <p className="whitespace-pre-wrap break-words">{message.text}</p>
      <div className={`mt-1 flex justify-end gap-2 text-[10px] ${isOwn ? "text-white/80" : "text-slate-400"}`}>
        {message.edited_at && <span>изм.</span>}
        <span>{formatTime(message.sent_at)}</span>
      </div>
    </div>
  </div>
);

const otherParticipantId = (chat: Chat | null, currentUserId: string | undefined) => {
  if (!chat || chat.type !== "personal") return null;
  return chat.participant_ids.find((id) => id !== currentUserId) ?? null;
};

const roleLabel = (role: string) =>
  role === "admin" ? "Админ" : role === "curator" ? "Куратор" : "Студент";

const MemberRow = ({ id, isCurrent }: { id: string; isCurrent: boolean }) => {
  const entry = useUser(id);
  const u = entry?.user;
  return (
    <li>
      <Link
        to={`/users/${id}`}
        className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 transition hover:bg-slate-100"
      >
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-slate-900">
            {u ? fullNameOf(u) : id.slice(0, 8) + "…"}
            {isCurrent && <span className="text-slate-400"> (вы)</span>}
          </p>
          {u && <p className="truncate text-[11px] text-slate-400">@{u.nickname}</p>}
        </div>
        {u && (
          <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
            {roleLabel(u.role)}
          </span>
        )}
      </Link>
    </li>
  );
};

export const ChatPage = () => {
  const { chatId } = useParams<{ chatId: string }>();
  const { user } = useAuth();
  const { refresh: refreshChats } = useChats();

  const [chat, setChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const [showMembers, setShowMembers] = useState(false);

  const listRef = useRef<HTMLDivElement | null>(null);

  const loadAll = useCallback(async () => {
    if (!chatId) return;
    setLoading(true);
    setError(null);
    try {
      const [c, m] = await Promise.all([chatsApi.getChat(chatId), messagesApi.list(chatId)]);
      setChat(c);
      setMessages(m);
      // refresh sidebar (unread_count может измениться после прочтения)
      refreshChats();
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, [chatId, refreshChats]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages.length]);

  const handleSend = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!chatId) return;
    const text = draft.trim();
    if (!text) return;
    setSending(true);
    setSendError(null);
    try {
      const created = await messagesApi.send(chatId, { text });
      setMessages((prev) => [...prev, created]);
      setDraft("");
      refreshChats();
    } catch (e) {
      setSendError(formatApiError(e));
    } finally {
      setSending(false);
    }
  };

  const otherId = otherParticipantId(chat, user?.id);
  const otherEntry = useUser(otherId);

  const headerTitle = !chat
    ? "Загружается…"
    : chat.type === "group"
      ? chat.title || "Без названия"
      : otherEntry?.user
        ? fullNameOf(otherEntry.user)
        : otherId
          ? otherId.slice(0, 8) + "…"
          : "Личный чат";

  if (!chatId) return null;

  return (
    <div className="flex w-full flex-row gap-2 sm:gap-4">
      <Sidebar />
      <section className="card-surface flex flex-1 flex-col rounded-2xl">
        <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3 sm:px-5">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-9 w-9 items-center justify-center rounded-2xl text-xs font-semibold text-white shadow-card ${
                chat?.type === "personal" ? "bg-emerald-500/90" : "bg-sky-500/90"
              }`}
            >
              {chat?.type === "personal" ? "DM" : "GRP"}
            </div>
            {chat?.type === "personal" && otherId ? (
              <Link
                to={`/users/${otherId}`}
                className="text-sm font-semibold text-slate-900 hover:text-primary-600 hover:underline"
              >
                {headerTitle}
              </Link>
            ) : (
              <p className="text-sm font-semibold text-slate-900">{headerTitle}</p>
            )}
          </div>
          <div className="flex items-center gap-3 text-[11px] text-slate-500">
            {loading && <LoadingHint text="Обновление" />}
            {chat?.type === "group" && (
              <button
                type="button"
                onClick={() => setShowMembers((v) => !v)}
                className={`rounded-full border px-2.5 py-0.5 transition ${
                  showMembers
                    ? "border-primary-300 bg-primary-50 text-primary-700"
                    : "border-slate-200 hover:bg-slate-100"
                }`}
              >
                Участники · {chat.participant_ids.length}
              </button>
            )}
            <button
              type="button"
              onClick={loadAll}
              disabled={loading}
              className="rounded-full border border-slate-200 px-2.5 py-0.5 hover:bg-slate-100"
            >
              Обновить
            </button>
          </div>
        </header>

        {chat?.type === "group" && showMembers && (
          <div className="border-b border-slate-200 bg-white px-4 py-3 sm:px-5">
            <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Участники ({chat.participant_ids.length})
            </p>
            <ul className="max-h-56 space-y-0.5 overflow-y-auto">
              {chat.participant_ids.map((id) => (
                <MemberRow key={id} id={id} isCurrent={id === user?.id} />
              ))}
            </ul>
          </div>
        )}

        <div ref={listRef} className="flex-1 space-y-2 overflow-y-auto bg-slate-50 px-3 py-3 text-xs sm:px-5">
          {error && <ErrorBox message={error} onRetry={loadAll} />}
          {!loading && !error && messages.length === 0 && (
            <div className="py-8 text-center text-[11px] text-slate-500">
              Сообщений пока нет — напишите первым.
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} isOwn={m.author_id === user?.id} />
          ))}
        </div>

        <form onSubmit={handleSend} className="border-t border-slate-200 bg-white p-3">
          {sendError && <div className="mb-2"><ErrorBox message={sendError} /></div>}
          <div className="flex items-end gap-2">
            <textarea
              rows={1}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e as unknown as React.FormEvent);
                }
              }}
              maxLength={2000}
              disabled={sending}
              className="min-h-[44px] flex-1 resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 outline-none ring-primary-500/20 placeholder:text-slate-400 focus:border-primary-500 focus:ring-1 disabled:bg-slate-100"
              placeholder="Напишите сообщение… (Enter — отправить, Shift+Enter — перенос)"
            />
            <button
              type="submit"
              disabled={sending || !draft.trim()}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-50"
            >
              {sending ? "…" : "➤"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};
