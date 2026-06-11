import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { chatsApi, formatApiError } from "../api";
import type { Chat } from "../api";
import { useAuth } from "../auth/AuthContext";

interface ChatsContextValue {
  chats: Chat[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  upsertChat: (chat: Chat) => void;
  removeChatLocally: (chatId: string) => void;
}

const ChatsContext = createContext<ChatsContextValue | null>(null);

export function ChatsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setChats([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await chatsApi.getChats();
      setChats(data);
    } catch (e) {
      setError(formatApiError(e, "Ошибка загрузки чатов"));
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const upsertChat = useCallback((chat: Chat) => {
    setChats((prev) => {
      const without = prev.filter((c) => c.id !== chat.id);
      return [chat, ...without];
    });
  }, []);

  const removeChatLocally = useCallback((chatId: string) => {
    setChats((prev) => prev.filter((c) => c.id !== chatId));
  }, []);

  const value: ChatsContextValue = { chats, loading, error, refresh, upsertChat, removeChatLocally };
  return <ChatsContext.Provider value={value}>{children}</ChatsContext.Provider>;
}

export function useChats(): ChatsContextValue {
  const ctx = useContext(ChatsContext);
  if (!ctx) throw new Error("useChats must be used inside <ChatsProvider>");
  return ctx;
}
