import { createContext, useContext, useEffect, useState } from "react";
import api, { clearTokens } from "./api";

const AuthCtx = createContext(null);

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // Start in the loading state only if there is a token to check
  const [loading, setLoading] = useState(() => !!localStorage.getItem("access"));

  useEffect(() => {
    if (!localStorage.getItem("access")) return;
    api.get("/auth/me/")
      .then((r) => setUser(r.data))
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const { data } = await api.post("/auth/login/", { email, password });
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    const me = await api.get("/auth/me/");
    setUser(me.data);
    return me.data;
  }

  async function logout() {
    try {
      await api.post("/auth/logout/", { refresh: localStorage.getItem("refresh") });
    } catch {
      // Ignore: tokens are cleared below either way
    }
    clearTokens();
    setUser(null);
  }

  return <AuthCtx.Provider value={{ user, loading, login, logout }}>{children}</AuthCtx.Provider>;
}