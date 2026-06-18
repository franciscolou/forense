import axios from "axios";

// Single axios instance for the whole app. The base URL is `/api/v1`, proxied
// to the backend by Vite in dev (see vite.config.ts).
export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

const TOKEN_KEY = "forense.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Attach the bearer token to every request when present.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Normalise backend error messages (FastAPI uses the `detail` field).
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail.map((d: { msg?: string }) => d.msg ?? "Erro de validação").join("; ");
    }
  }
  return "Algo deu errado. Tente novamente.";
}
