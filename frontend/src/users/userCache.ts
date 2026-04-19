// Простейший process-wide кэш пользователей по UUID, плюс хук useUser.
// Нужен, чтобы не дёргать /users/{id} повторно из Sidebar и шапки ChatPage.

import { useEffect, useSyncExternalStore } from "react";
import { ApiError, usersApi } from "../api";
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

function notify() {
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
      const msg = e instanceof ApiError ? e.message : (e as Error).message;
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

const getSnapshot = () => cache;

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
