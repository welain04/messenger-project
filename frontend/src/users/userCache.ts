// Простейший process-wide кэш пользователей по UUID, плюс хук useUser.
// Нужен, чтобы не дёргать /users/{id} повторно из Sidebar и шапки ChatPage.

import { useEffect, useSyncExternalStore } from "react";
import { formatApiError, usersApi } from "../api";
import type { User, UUID } from "../api";

type Status = "idle" | "loading" | "ok" | "error";

interface Entry {
  status: Status;
  user?: User;
  error?: string;
}

const cache = new Map<UUID, Entry>();
const inflight = new Map<UUID, Promise<void>>();
const listeners = new Set<() => void>();

// Версия инкрементируется при каждом изменении кэша. getSnapshot возвращает
// именно её (число), иначе useSyncExternalStore не увидит изменений в Map
// (ссылка на Map не меняется) и не перерисует компонент при дозагрузке.
let version = 0;

function notify() {
  version += 1;
  for (const l of listeners) l();
}

function ensureLoaded(id: UUID): void {
  const entry = cache.get(id);
  if (entry && (entry.status === "ok" || entry.status === "loading")) return;

  cache.set(id, { status: "loading" });
  notify();

  const p = usersApi
    .getById(id)
    .then((user) => {
      cache.set(id, { status: "ok", user });
    })
    .catch((e) => {
      const msg = formatApiError(e);
      cache.set(id, { status: "error", error: msg });
    })
    .finally(() => {
      inflight.delete(id);
      notify();
    });
  inflight.set(id, p);
}

const subscribe = (cb: () => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};

const getSnapshot = () => version;

export function invalidateUser(id: UUID): void {
  cache.delete(id);
  notify();
}

export function useUser(id: UUID | undefined | null): Entry | undefined {
  useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  useEffect(() => {
    if (id) ensureLoaded(id);
  }, [id]);
  return id ? cache.get(id) : undefined;
}

/** Достать никнейм или вернуть короткий UUID-плейсхолдер пока грузится. */
export function nicknameOf(id: UUID | undefined | null): string {
  if (!id) return "—";
  const entry = cache.get(id);
  if (entry?.status === "ok" && entry.user) return entry.user.nickname;
  return id.slice(0, 8) + "…";
}

/** Полное имя пользователя («Имя Фамилия») с откатом на никнейм. */
export function fullNameOf(user: User | undefined | null): string {
  if (!user) return "";
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return name || user.nickname;
}
