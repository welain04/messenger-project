import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { authApi, usersApi, getToken, ApiError } from "../api";
import type { LoginRequest, RegisterRequest, UpdateUserRequest, User } from "../api";

interface AuthContextValue {
  user: User | null;
  initializing: boolean;
  login: (payload: LoginRequest) => Promise<User>;
  register: (payload: RegisterRequest) => Promise<User>;
  logout: () => void;
  updateMe: (payload: UpdateUserRequest) => Promise<User>;
  refresh: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  const refresh = useCallback(async (): Promise<User | null> => {
    if (!getToken()) {
      setUser(null);
      return null;
    }
    try {
      const me = await usersApi.me();
      setUser(me);
      return me;
    } catch (e) {
      // Если токен протух/невалиден — забываем пользователя.
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        authApi.logout();
        setUser(null);
        return null;
      }
      throw e;
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setInitializing(false));
  }, [refresh]);

  const login = useCallback(async (payload: LoginRequest) => {
    await authApi.login(payload);
    const me = await usersApi.me();
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (payload: RegisterRequest) => {
    const created = await authApi.register(payload);
    await authApi.login({ nickname: payload.nickname, password: payload.password });
    setUser(created);
    return created;
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
  }, []);

  const updateMe = useCallback(async (payload: UpdateUserRequest) => {
    const updated = await usersApi.updateMe(payload);
    setUser(updated);
    return updated;
  }, []);

  const value: AuthContextValue = { user, initializing, login, register, logout, updateMe, refresh };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
