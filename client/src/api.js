import axios from "axios";

const BASE = import.meta.env.VITE_API_URL;
const api = axios.create({ baseURL: BASE });

export const clearTokens = () => {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
};

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("access");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    const canRetry =
      err.response?.status === 401 &&
      !orig._retry &&
      !orig.url.includes("/auth/") &&
      localStorage.getItem("refresh");
    if (canRetry) {
      orig._retry = true;
      try {
        refreshing =
          refreshing ||
          axios
            .post(`${BASE}/auth/refresh/`, { refresh: localStorage.getItem("refresh") })
            .finally(() => (refreshing = null));
        const { data } = await refreshing;
        localStorage.setItem("access", data.access);
        if (data.refresh) localStorage.setItem("refresh", data.refresh);
        orig.headers.Authorization = `Bearer ${data.access}`;
        return api(orig);
      } catch {
        clearTokens();
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

// Turns the server's {error:{message,details}} into one readable string
export function errorMessage(err) {
  const e = err.response?.data?.error;
  if (!e) return err.message || "Something went wrong";
  const flat = (d) =>
    Array.isArray(d) ? d.map(flat).join(" ")
    : d && typeof d === "object" ? Object.entries(d).map(([k, v]) => `${k}: ${flat(v)}`).join(" | ")
    : String(d);
  return e.details ? flat(e.details) : e.message;
}

export default api;