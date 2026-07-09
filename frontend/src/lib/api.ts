import type {
  Comparison,
  Overlay,
  ReferenceSummary,
  SwingDetail,
  SwingSummary,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

/** Absolute URL for an API path (video artifacts, thumbnails, ...). */
export function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

/** WebSocket URL for a swing's live progress stream. */
export function progressSocketUrl(swingId: string): string {
  return `${API_BASE.replace(/^http/, "ws")}/ws/swings/${swingId}/progress`;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), { cache: "no-store", ...init });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function uploadSwing(
  file: File,
  handedness: "right" | "left",
): Promise<{ id: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  form.append("handedness", handedness);
  return request("/api/v1/swings/upload", { method: "POST", body: form });
}

export function getSwing(id: string): Promise<SwingDetail> {
  return request(`/api/v1/swings/${id}`);
}

export function listSwings(): Promise<SwingSummary[]> {
  return request("/api/v1/swings");
}

export function deleteSwing(id: string): Promise<void> {
  return request(`/api/v1/swings/${id}`, { method: "DELETE" });
}

export function listReferences(): Promise<ReferenceSummary[]> {
  return request("/api/v1/references");
}

export function getComparison(swingId: string, refId: string): Promise<Comparison> {
  return request(`/api/v1/swings/${swingId}/compare/${refId}`);
}

export function getOverlay(swingId: string, refId: string): Promise<Overlay> {
  return request(`/api/v1/swings/${swingId}/compare/${refId}/overlay`);
}

export { ApiError };
