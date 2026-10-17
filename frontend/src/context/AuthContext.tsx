import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, onUnauthorized, tokenStore } from "../lib/api";
import type { TokenResponse, User } from "../lib/types";
import { useTheme } from "./ThemeContext";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: User | null;
  status: Status;
  sessionExpired: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
  clearSession: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { setTheme } = useTheme();
  const [user, setUserState] = useState<User | null>(null);
  const [status, setStatus] = useState<Status>(() => (tokenStore.get() ? "loading" : "anonymous"));
  const [sessionExpired, setSessionExpired] = useState(false);

  const setUser = useCallback(
    (u: User) => {
      setUserState(u);
      setTheme(u.theme);
    },
    [setTheme],
  );

  const clearSession = useCallback(() => {
    tokenStore.clear();
    setUserState(null);
    setStatus("anonymous");
  }, []);

  // Restore an existing session on page load.
  useEffect(() => {
    if (!tokenStore.get()) return;
    let cancelled = false;
    api
      .me()
      .then((u) => {
        if (cancelled) return;
        setUser(u);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        clearSession();
      });
    return () => {
      cancelled = true;
    };
  }, [setUser, clearSession]);

  // Any 401 from an authenticated call ends the session.
  useEffect(
    () =>
      onUnauthorized(() => {
        setSessionExpired(true);
        clearSession();
      }),
    [clearSession],
  );

  const accept = useCallback(
    (res: TokenResponse) => {
      tokenStore.set(res.access_token);
      setSessionExpired(false);
      setUser(res.user);
      setStatus("authenticated");
    },
    [setUser],
  );

  const login = useCallback(async (email: string, password: string) => accept(await api.login(email, password)), [accept]);
  const register = useCallback(
    async (email: string, fullName: string, password: string) => accept(await api.register(email, fullName, password)),
    [accept],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout(); // revokes the token on the server
    } catch {
      /* token may already be invalid; clear locally regardless */
    }
    setSessionExpired(false);
    clearSession();
  }, [clearSession]);

  const value = useMemo(
    () => ({ user, status, sessionExpired, login, register, logout, setUser, clearSession }),
    [user, status, sessionExpired, login, register, logout, setUser, clearSession],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
