import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowUpIcon, PaperClipIcon, TrashIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { Sidebar } from "../components/Sidebar";
import { UserAvatar } from "../components/UserAvatar";
import { useAuth } from "../auth/AuthContext";
import { useChats } from "../chats/ChatsContext";
import { chatsApi, filesApi, messagesApi, uploadsApi, usersApi, formatApiError } from "../api";
import type { Attachment, Chat, Message, StagedUpload, User } from "../api";
import { ErrorBox, LoadingHint } from "../components/States";
import { useSignedUrl } from "../hooks/useSignedUrl";
import { useUser, fullNameOf } from "../users/userCache";

const DRAFT_MAX_ROWS = 4;
const DRAFT_MIN_HEIGHT_PX = 40;
const OWN_MESSAGE_DELETE_MS = 24 * 60 * 60 * 1000;

const canDeleteMessage = (
  message: Message,
  currentUserId: string | undefined,
  userRole: string | undefined,
  chat: Chat | null,
): boolean => {
  if (!currentUserId || !chat) return false;
  if (message.author_id === currentUserId) {
    return Date.now() - new Date(message.sent_at).getTime() <= OWN_MESSAGE_DELETE_MS;
  }
  if (userRole === "admin") return true;
  return (
    userRole === "curator" &&
    chat.type === "group" &&
    chat.created_by === currentUserId
  );
};

const canManageMembers = (
  chat: Chat | null,
  currentUserId: string | undefined,
  userRole: string | undefined,
): boolean => {
  if (!currentUserId || !chat || chat.type !== "group") return false;
  if (chat.created_by === currentUserId) return true;
  return userRole === "admin";
};

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

const MessageBubble = ({
  message,
  isOwn,
  canDelete,
  deleting,
  onDelete,
}: {
  message: Message;
  isOwn: boolean;
  canDelete: boolean;
  deleting?: boolean;
  onDelete?: () => void;
}) => (
  <div
    data-testid="chat-message"
    className={`group flex w-full ${isOwn ? "justify-end" : "justify-start"}`}
  >
    <div className="flex max-w-[85%] items-end gap-1.5">
      {canDelete && onDelete && (
        <button
          type="button"
          onClick={onDelete}
          disabled={deleting}
          title="Удалить сообщение"
          aria-label="Удалить сообщение"
          data-testid="chat-delete-message"
          className="mb-1 shrink-0 rounded-full p-1.5 text-slate-400 opacity-0 transition hover:bg-slate-200/80 hover:text-rose-600 group-hover:opacity-100 focus:opacity-100 disabled:opacity-40"
        >
          <TrashIcon className="h-4 w-4" strokeWidth={2} />
        </button>
      )}
      <div
        className={`min-w-0 rounded-2xl px-3 py-2 text-xs shadow-sm ${
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
        <div className={`mt-1 flex items-center justify-end gap-2 text-[10px] ${isOwn ? "text-white/80" : "text-slate-400"}`}>
          {message.edited_at && <span>изм.</span>}
          <span>{formatTime(message.sent_at)}</span>
        </div>
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

const MemberRow = ({
  id,
  isCurrent,
  isCreator,
  canRemove,
  removing,
  onRemove,
}: {
  id: string;
  isCurrent: boolean;
  isCreator: boolean;
  canRemove: boolean;
  removing?: boolean;
  onRemove?: () => void;
}) => {
  const entry = useUser(id);
  const u = entry?.user;
  return (
    <li data-testid="chat-member-row" className="group flex items-center gap-1">
      <Link
        to={`/users/${id}`}
        className="flex min-w-0 flex-1 items-center justify-between gap-2 rounded-lg px-2 py-1.5 transition hover:bg-slate-100"
      >
        <div className="flex min-w-0 items-center gap-2">
          <UserAvatar user={u} userId={id} size="sm" />
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-slate-900">
              {u ? fullNameOf(u) : id.slice(0, 8) + "…"}
              {isCurrent && <span className="text-slate-400"> (вы)</span>}
              {isCreator && <span className="text-slate-400"> · создатель</span>}
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
      {canRemove && !isCreator && !isCurrent && onRemove && (
        <button
          type="button"
          onClick={onRemove}
          disabled={removing}
          title="Удалить из чата"
          aria-label="Удалить из чата"
          data-testid="chat-remove-member"
          className="shrink-0 rounded-full p-1.5 text-slate-400 opacity-0 transition hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100 focus:opacity-100 disabled:opacity-40"
        >
          <XMarkIcon className="h-4 w-4" strokeWidth={2} />
        </button>
      )}
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
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [pendingRemoveUserId, setPendingRemoveUserId] = useState<string | null>(null);
  const [removingMemberId, setRemovingMemberId] = useState<string | null>(null);
  const [memberError, setMemberError] = useState<string | null>(null);
  const [addMemberSearch, setAddMemberSearch] = useState("");
  const [addMemberResults, setAddMemberResults] = useState<User[]>([]);
  const [addMemberSearchLoading, setAddMemberSearchLoading] = useState(false);
  const [addMemberSearchError, setAddMemberSearchError] = useState<string | null>(null);
  const [addingMemberId, setAddingMemberId] = useState<string | null>(null);

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

  useEffect(() => {
    const q = addMemberSearch.trim();
    if (q.length < 2) {
      setAddMemberResults([]);
      setAddMemberSearchError(null);
      return;
    }

    const id = setTimeout(async () => {
      setAddMemberSearchLoading(true);
      setAddMemberSearchError(null);
      try {
        const users = await usersApi.search(q, 10);
        const inChat = new Set(chat?.participant_ids ?? []);
        setAddMemberResults(users.filter((u) => !inChat.has(u.id)));
      } catch (e) {
        setAddMemberSearchError(formatApiError(e, "Ошибка поиска"));
      } finally {
        setAddMemberSearchLoading(false);
      }
    }, 300);

    return () => clearTimeout(id);
  }, [addMemberSearch, chat?.participant_ids]);

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

  const handleDeleteMessage = async (messageId: string) => {
    setDeletingId(messageId);
    setDeleteError(null);
    try {
      await messagesApi.remove(messageId);
      setMessages((prev) => prev.filter((m) => m.id !== messageId));
      refreshChats();
    } catch (e) {
      setDeleteError(formatApiError(e));
    } finally {
      setDeletingId(null);
      setPendingDeleteId(null);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!chatId) return;
    setRemovingMemberId(userId);
    setMemberError(null);
    try {
      await chatsApi.removeParticipant(chatId, userId);
      setChat((prev) =>
        prev
          ? { ...prev, participant_ids: prev.participant_ids.filter((id) => id !== userId) }
          : prev,
      );
      refreshChats();
    } catch (e) {
      setMemberError(formatApiError(e));
    } finally {
      setRemovingMemberId(null);
      setPendingRemoveUserId(null);
    }
  };

  const handleAddMember = async (member: User) => {
    if (!chatId) return;
    setAddingMemberId(member.id);
    setMemberError(null);
    try {
      const updated = await chatsApi.addParticipant(chatId, { user_id: member.id });
      setChat(updated);
      refreshChats();
      setAddMemberSearch("");
      setAddMemberResults([]);
    } catch (e) {
      setMemberError(formatApiError(e));
    } finally {
      setAddingMemberId(null);
    }
  };

  const otherId = otherParticipantId(chat, user?.id);
  const otherEntry = useUser(otherId);
  const pendingRemoveEntry = useUser(pendingRemoveUserId);
  const canManage = canManageMembers(chat, user?.id, user?.role);

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
                data-testid="chat-members-toggle"
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
            {memberError && (
              <div className="mb-2">
                <ErrorBox message={memberError} />
              </div>
            )}
            {canManage && (
              <div className="mb-3">
                <label className="mb-1 block text-[11px] text-slate-500">Добавить участника</label>
                <input
                  value={addMemberSearch}
                  onChange={(e) => setAddMemberSearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") e.preventDefault();
                  }}
                  disabled={addingMemberId !== null}
                  data-testid="chat-add-member-input"
                  placeholder="Поиск по никнейму (минимум 2 символа)"
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs focus:border-primary-400 focus:ring-1 focus:ring-primary-500/15 disabled:bg-slate-50"
                />
                {addMemberSearchLoading && (
                  <div className="mt-1.5">
                    <LoadingHint text="Поиск" />
                  </div>
                )}
                {addMemberSearchError && (
                  <div className="mt-1.5">
                    <ErrorBox message={addMemberSearchError} />
                  </div>
                )}
                {!addMemberSearchLoading &&
                  addMemberSearch.trim().length >= 2 &&
                  addMemberResults.length > 0 && (
                    <div className="mt-1.5 max-h-36 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1">
                      {addMemberResults.map((u) => (
                        <button
                          key={u.id}
                          type="button"
                          data-testid="chat-add-member-result"
                          onClick={() => void handleAddMember(u)}
                          disabled={addingMemberId !== null}
                          className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs hover:bg-slate-100 disabled:opacity-40"
                        >
                          <span className="font-medium text-slate-800">
                            {[u.first_name, u.last_name].filter(Boolean).join(" ").trim() || u.nickname}
                            <span className="ml-1 text-slate-400">@{u.nickname}</span>
                          </span>
                          <span className="text-[10px] text-slate-500">
                            {addingMemberId === u.id
                              ? "Добавление…"
                              : u.role === "curator"
                                ? "Куратор"
                                : u.role === "admin"
                                  ? "Админ"
                                  : "Студент"}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                {!addMemberSearchLoading &&
                  addMemberSearch.trim().length >= 2 &&
                  addMemberResults.length === 0 && (
                    <p className="mt-1.5 text-[11px] text-slate-400">Никого не найдено</p>
                  )}
              </div>
            )}
            <ul className="max-h-56 space-y-0.5 overflow-y-auto">
              {chat.participant_ids.map((id) => (
                <MemberRow
                  key={id}
                  id={id}
                  isCurrent={id === user?.id}
                  isCreator={id === chat.created_by}
                  canRemove={canManage}
                  removing={removingMemberId === id}
                  onRemove={() => setPendingRemoveUserId(id)}
                />
              ))}
            </ul>
          </div>
        )}

        <div
          ref={listRef}
          className="minimal-scroll min-h-0 flex-1 space-y-2 overflow-y-auto bg-slate-50 px-3 py-3 text-xs sm:px-5"
        >
          {error && <ErrorBox message={error} onRetry={loadAll} />}
          {deleteError && <ErrorBox message={deleteError} />}
          {!loading && !error && messages.length === 0 && (
            <div className="py-8 text-center text-[11px] text-slate-500">
              Сообщений пока нет — напишите первым.
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              isOwn={m.author_id === user?.id}
              canDelete={canDeleteMessage(m, user?.id, user?.role, chat)}
              deleting={deletingId === m.id}
              onDelete={() => setPendingDeleteId(m.id)}
            />
          ))}
        </div>

        {pendingRemoveUserId && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
            onClick={() => setPendingRemoveUserId(null)}
            role="presentation"
          >
            <div
              className="card-surface w-full max-w-xs rounded-2xl p-5 shadow-lg"
              role="dialog"
              aria-modal="true"
              aria-labelledby="remove-member-title"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 id="remove-member-title" className="text-sm font-semibold text-slate-900">
                Удалить участника из чата?
              </h3>
              <p className="mt-1.5 text-xs text-slate-500">
                {pendingRemoveEntry?.user
                  ? `${fullNameOf(pendingRemoveEntry.user)} (@${pendingRemoveEntry.user.nickname}) больше не сможет читать и писать в этом чате.`
                  : "Участник больше не сможет читать и писать в этом чате."}
              </p>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setPendingRemoveUserId(null)}
                  disabled={removingMemberId === pendingRemoveUserId}
                  className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                >
                  Отмена
                </button>
                <button
                  type="button"
                  onClick={() => void handleRemoveMember(pendingRemoveUserId)}
                  disabled={removingMemberId === pendingRemoveUserId}
                  className="rounded-xl bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-40"
                >
                  {removingMemberId === pendingRemoveUserId ? "Удаление…" : "Удалить"}
                </button>
              </div>
            </div>
          </div>
        )}

        {pendingDeleteId && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
            onClick={() => setPendingDeleteId(null)}
            role="presentation"
          >
            <div
              className="card-surface w-full max-w-xs rounded-2xl p-5 shadow-lg"
              role="dialog"
              aria-modal="true"
              aria-labelledby="delete-message-title"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 id="delete-message-title" className="text-sm font-semibold text-slate-900">
                Удалить сообщение?
              </h3>
              <p className="mt-1.5 text-xs text-slate-500">Это действие нельзя отменить.</p>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setPendingDeleteId(null)}
                  disabled={deletingId === pendingDeleteId}
                  className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                >
                  Отмена
                </button>
                <button
                  type="button"
                  onClick={() => void handleDeleteMessage(pendingDeleteId)}
                  disabled={deletingId === pendingDeleteId}
                  className="rounded-xl bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-40"
                >
                  {deletingId === pendingDeleteId ? "Удаление…" : "Удалить"}
                </button>
              </div>
            </div>
          </div>
        )}

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
              data-testid="chat-attach-input"
              className="hidden"
              onChange={handleFileSelect}
            />
            <button
              type="button"
              disabled={uploading || sending}
              onClick={() => fileInputRef.current?.click()}
              className="mb-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-transparent text-slate-400 transition hover:bg-slate-100/70 hover:text-slate-600 disabled:opacity-40"
              title="Прикрепить файл"
              aria-label="Прикрепить файл"
              data-testid="chat-attach-button"
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
              data-testid="chat-message-input"
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
              aria-label="Отправить"
              data-testid="chat-send-button"
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
