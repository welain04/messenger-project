import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowUpIcon, PaperClipIcon } from "@heroicons/react/24/outline";
import { Sidebar } from "../components/Sidebar";
import { UserAvatar } from "../components/UserAvatar";
import { useAuth } from "../auth/AuthContext";
import { useChats } from "../chats/ChatsContext";
import { chatsApi, filesApi, messagesApi, uploadsApi, formatApiError } from "../api";
import type { Attachment, Chat, Message, StagedUpload } from "../api";
import { ErrorBox, LoadingHint } from "../components/States";
import { useSignedUrl } from "../hooks/useSignedUrl";
import { useUser, fullNameOf } from "../users/userCache";

const DRAFT_MAX_ROWS = 4;
const DRAFT_MIN_HEIGHT_PX = 40;

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

const AttachmentImage = ({ attachment }: { attachment: Attachment }) => {
  const { url } = useSignedUrl(
    () => filesApi.attachmentUrl(attachment.id),
    attachment.kind === "image",
  );
  if (!url) return null;
  return (
    <img
      src={url}
      alt={attachment.file_name ?? "Изображение"}
      className="max-h-48 rounded-lg object-cover"
    />
  );
};

const AttachmentFile = ({ attachment }: { attachment: Attachment }) => {
  const { url } = useSignedUrl(() => filesApi.attachmentUrl(attachment.id), true);
  if (!url) {
    return (
      <span className="text-[11px] opacity-80">
        📎 {attachment.file_name ?? "Файл"}
      </span>
    );
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[11px] underline opacity-90 hover:opacity-100"
    >
      📎 {attachment.file_name ?? "Скачать файл"}
    </a>
  );
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
      {message.attachments && message.attachments.length > 0 && (
        <div className="mb-2 space-y-2">
          {message.attachments.map((a) =>
            a.kind === "image" ? (
              <AttachmentImage key={a.id} attachment={a} />
            ) : (
              <AttachmentFile key={a.id} attachment={a} />
            ),
          )}
        </div>
      )}
      {message.text && <p className="whitespace-pre-wrap break-words">{message.text}</p>}
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
        <div className="flex min-w-0 items-center gap-2">
          <UserAvatar user={u} userId={id} size="sm" />
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-slate-900">
              {u ? fullNameOf(u) : id.slice(0, 8) + "…"}
              {isCurrent && <span className="text-slate-400"> (вы)</span>}
            </p>
            {u && <p className="truncate text-[11px] text-slate-400">@{u.nickname}</p>}
          </div>
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
  const [pendingUploads, setPendingUploads] = useState<StagedUpload[]>([]);
  const [uploading, setUploading] = useState(false);

  const [showMembers, setShowMembers] = useState(false);

  const listRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const syncTextareaHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const styles = getComputedStyle(el);
    const lineHeight = parseFloat(styles.lineHeight) || 18;
    const padding =
      parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom);
    const maxHeight = lineHeight * DRAFT_MAX_ROWS + padding;
    const next = Math.min(el.scrollHeight, maxHeight);
    el.style.height = `${Math.max(DRAFT_MIN_HEIGHT_PX, next)}px`;
    el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden";
  }, []);

  const loadAll = useCallback(async () => {
    if (!chatId) return;
    setLoading(true);
    setError(null);
    try {
      const [c, m] = await Promise.all([chatsApi.getChat(chatId), messagesApi.list(chatId)]);
      setChat(c);
      setMessages(m);
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

  useEffect(() => {
    syncTextareaHeight();
  }, [draft, syncTextareaHeight]);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setSendError(null);
    try {
      const staged = await uploadsApi.stage(file);
      setPendingUploads((prev) => [...prev, staged]);
    } catch (e) {
      setSendError(formatApiError(e));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const removePending = async (id: string) => {
    setPendingUploads((prev) => prev.filter((u) => u.id !== id));
    try {
      await uploadsApi.cancel(id);
    } catch {
      // отмена на сервере не критична для UX
    }
  };

  const handleSend = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!chatId) return;
    const text = draft.trim();
    if (!text && pendingUploads.length === 0) return;
    setSending(true);
    setSendError(null);
    try {
      const created = await messagesApi.send(chatId, {
        text: text || null,
        upload_ids: pendingUploads.map((u) => u.id),
      });
      setMessages((prev) => [...prev, created]);
      setDraft("");
      setPendingUploads([]);
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
    <div className="flex h-[calc(100dvh-7.5rem)] w-full min-h-0 flex-row items-stretch gap-2 sm:h-[calc(100dvh-9.5rem)]">
      <Sidebar />
      <section className="card-surface flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl">
        <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3 sm:px-5">
          <div className="flex items-center gap-3">
            {chat?.type === "personal" && otherId ? (
              <UserAvatar user={otherEntry?.user} userId={otherId} size="sm" />
            ) : (
              <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-sky-500/90 text-xs font-semibold text-white shadow-card">
                GRP
              </div>
            )}
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

        <div
          ref={listRef}
          className="minimal-scroll min-h-0 flex-1 space-y-2 overflow-y-auto bg-slate-50 px-3 py-3 text-xs sm:px-5"
        >
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

        <form onSubmit={handleSend} className="shrink-0 border-t border-slate-200 bg-white p-3">
          {sendError && (
            <div className="mb-2">
              <ErrorBox message={sendError} />
            </div>
          )}
          {pendingUploads.length > 0 && (
            <ul className="mb-2 flex flex-wrap gap-2">
              {pendingUploads.map((u) => (
                <li
                  key={u.id}
                  className="flex items-center gap-1 rounded-lg bg-slate-100 px-2 py-1 text-[11px] text-slate-700"
                >
                  <span className="max-w-[120px] truncate">{u.file_name}</span>
                  <button
                    type="button"
                    onClick={() => void removePending(u.id)}
                    className="text-slate-400 hover:text-rose-600"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-end gap-1.5">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileSelect}
            />
            <button
              type="button"
              disabled={uploading || sending}
              onClick={() => fileInputRef.current?.click()}
              className="mb-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-transparent text-slate-400 transition hover:bg-slate-100/70 hover:text-slate-600 disabled:opacity-40"
              title="Прикрепить файл"
            >
              {uploading ? (
                <span className="text-xs">…</span>
              ) : (
                <PaperClipIcon className="h-5 w-5" strokeWidth={1.75} />
              )}
            </button>
            <textarea
              ref={textareaRef}
              rows={1}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key !== "Enter") return;

                if (e.ctrlKey || e.metaKey) {
                  e.preventDefault();
                  const el = e.currentTarget;
                  const start = el.selectionStart ?? draft.length;
                  const end = el.selectionEnd ?? draft.length;
                  const next = `${draft.slice(0, start)}\n${draft.slice(end)}`;
                  setDraft(next);
                  requestAnimationFrame(() => {
                    el.selectionStart = el.selectionEnd = start + 1;
                    syncTextareaHeight();
                  });
                  return;
                }

                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSend(e as unknown as React.FormEvent);
                }
              }}
              maxLength={2000}
              disabled={sending}
              className="chat-input-scroll min-h-[40px] flex-1 resize-none rounded-xl border border-slate-200 bg-transparent px-3 py-2 text-xs leading-[18px] text-slate-900 outline-none placeholder:text-slate-400 focus:border-primary-400 focus:ring-1 focus:ring-primary-500/15 disabled:bg-slate-50"
              placeholder="Сообщение…"
            />
            <button
              type="submit"
              disabled={sending || uploading || (!draft.trim() && pendingUploads.length === 0)}
              className="mb-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-500 text-white shadow-sm transition hover:bg-primary-600 disabled:opacity-40"
              title="Отправить"
            >
              {sending ? (
                <span className="text-xs">…</span>
              ) : (
                <ArrowUpIcon className="h-4 w-4" strokeWidth={2.5} />
              )}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
};
