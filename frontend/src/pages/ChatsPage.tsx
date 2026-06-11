import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sidebar } from "../components/Sidebar";
import { useChats } from "../chats/ChatsContext";
import { chatsApi, usersApi, formatApiError } from "../api";
import type { ChatType, CreateChatRequest, User } from "../api";
import { ErrorBox, LoadingHint } from "../components/States";

export const ChatsPage = () => {
  const { chats, loading, error, refresh, upsertChat } = useChats();
  const navigate = useNavigate();

  const [type, setType] = useState<ChatType>("group");
  const [title, setTitle] = useState("");
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedParticipants, setSelectedParticipants] = useState<User[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    if (type === "personal" && selectedParticipants.length > 1) {
      setSelectedParticipants([selectedParticipants[0]]);
    }
  }, [type, selectedParticipants]);

  useEffect(() => {
    const q = search.trim();
    if (q.length < 2) {
      setSearchResults([]);
      setSearchError(null);
      return;
    }

    const id = setTimeout(async () => {
      setSearchLoading(true);
      setSearchError(null);
      try {
        const users = await usersApi.search(q, 10);
        const excluded = new Set(selectedParticipants.map((u) => u.id));
        setSearchResults(users.filter((u) => !excluded.has(u.id)));
      } catch (e) {
        const msg = formatApiError(e, "Ошибка поиска");
        setSearchError(msg);
      } finally {
        setSearchLoading(false);
      }
    }, 300);

    return () => clearTimeout(id);
  }, [search, selectedParticipants]);

  const addParticipant = (user: User) => {
    setCreateError(null);
    setSelectedParticipants((prev) => {
      if (prev.some((p) => p.id === user.id)) return prev;
      if (type === "personal") return [user];
      return [...prev, user];
    });
    setSearch("");
    setSearchResults([]);
  };

  const removeParticipant = (userId: string) => {
    setSelectedParticipants((prev) => prev.filter((u) => u.id !== userId));
  };

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setCreateError(null);
    if (search.trim().length > 0) {
      setCreateError(
        "Вы ввели никнейм, но не выбрали пользователя из списка. Нажмите на нужный вариант ниже."
      );
      return;
    }
    const ids = selectedParticipants.map((u) => u.id);
    if (ids.length === 0) {
      setCreateError("Добавьте хотя бы одного участника через поиск");
      return;
    }
    if (type === "personal" && ids.length !== 1) {
      setCreateError("Для личного чата нужно выбрать ровно одного собеседника");
      return;
    }
    const payload: CreateChatRequest = { type, participant_ids: ids };
    if (type === "group") payload.title = title.trim();

    setSubmitting(true);
    try {
      const created = await chatsApi.createChat(payload);
      upsertChat(created);
      setTitle("");
      setSearch("");
      setSearchResults([]);
      setSelectedParticipants([]);
      navigate(`/chats/${created.id}`);
    } catch (e) {
      setCreateError(formatApiError(e, "Не удалось создать чат"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex w-full flex-row gap-2 sm:gap-4">
      <Sidebar />

      <section className="card-surface flex flex-1 flex-col gap-6 overflow-hidden rounded-2xl px-5 py-6 sm:px-8">
        <div>
          <div className="pill mb-3 inline-flex">Онлайн-школа · пространство общения</div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Все чаты курса
            <span className="block text-primary-600">в одном защищённом месте</span>
          </h2>
          <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
            {loading ? <LoadingHint text="Обновление списка чатов" /> : <span>{chats.length} чатов</span>}
            <button
              type="button"
              onClick={refresh}
              className="rounded-full border border-slate-200 px-2.5 py-0.5 text-[11px] hover:bg-slate-100"
              disabled={loading}
            >
              Обновить
            </button>
          </div>
          {error && <div className="mt-3"><ErrorBox message={error} onRetry={refresh} /></div>}
        </div>

        <form onSubmit={handleCreate} className="rounded-2xl border border-slate-200 bg-white/60 p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Создать чат</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-[11px] text-slate-500">Тип</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as ChatType)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1"
              >
                <option value="group">Групповой</option>
                <option value="personal">Личный</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-[11px] text-slate-500">
                {type === "group" ? "Название" : "Название (для личного не используется)"}
              </label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={type === "personal"}
                maxLength={100}
                placeholder={type === "group" ? "Vibe Coding · 1 поток" : "—"}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1 disabled:bg-slate-100"
              />
            </div>
            <div className="sm:col-span-3">
              <label className="mb-1 block text-[11px] text-slate-500">
                Участники ({type === "personal" ? "ровно 1 собеседник" : "минимум 1 собеседник"})
              </label>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                  }
                }}
                placeholder="Введите никнейм (минимум 2 символа)"
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:ring-1"
              />
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedParticipants.map((u) => (
                  <span
                    key={u.id}
                    className="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-xs text-primary-700"
                  >
                    @{u.nickname}
                    <button
                      type="button"
                      onClick={() => removeParticipant(u.id)}
                      className="text-primary-500 hover:text-primary-700"
                      aria-label={`Удалить ${u.nickname}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              {searchLoading && (
                <div className="mt-2 text-[11px] text-slate-500">
                  <LoadingHint text="Обновление результатов" />
                </div>
              )}
              {searchError && <div className="mt-2"><ErrorBox message={searchError} /></div>}
              {!searchLoading && search.trim().length >= 2 && searchResults.length > 0 && (
                <div className="mt-2 max-h-44 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1">
                  {searchResults.map((u) => (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => addParticipant(u)}
                      className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs hover:bg-slate-100"
                    >
                      <span className="font-medium text-slate-800">@{u.nickname}</span>
                      <span className="text-[10px] text-slate-500">{u.role === "curator" ? "Куратор" : "Ученик"}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          {createError && <div className="mt-3"><ErrorBox message={createError} /></div>}
          <div className="mt-3 flex items-center gap-3">
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center justify-center rounded-xl bg-primary-500 px-4 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-primary-600 disabled:opacity-60"
            >
              {submitting ? "Создание…" : "Создать чат"}
            </button>
            <p className="text-[11px] text-slate-500">
              Ищите пользователей по никнейму и выбирайте из выпадающего списка.
            </p>
          </div>
        </form>
      </section>
    </div>
  );
};
