export function apiBaseUrl(): string {
  const env = process.env.NEXT_PUBLIC_API_URL?.trim();
  const fallback = "http://localhost:8000";

  // Saat UI diakses lewat IP/domain VPS tapi build mem-bake localhost (umum di Docker),
  // pakai host halaman ini + port API default agar login/API jalan tanpa rebuild.
  if (typeof window !== "undefined") {
    const { hostname, protocol } = window.location;
    const pageIsLocal = hostname === "localhost" || hostname === "127.0.0.1";
    const envMissingOrLocal =
      !env || env.includes("localhost") || env.includes("127.0.0.1");
    if (!pageIsLocal && envMissingOrLocal) {
      return `${protocol}//${hostname}:8000`;
    }
  }

  return env || fallback;
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }

  const token =
    typeof window !== "undefined" ? window.localStorage.getItem("sayai_token") : null;
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(`${apiBaseUrl()}${path}`, { ...init, headers });
}
