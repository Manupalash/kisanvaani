const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); this.name = "ApiError"; }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: init.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init.headers },
    });
  } catch {
    throw new ApiError("Could not reach KisanVaani server. Check that the backend is running.", 0);
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { const body = await response.json(); message = body.detail || message; } catch { /* use status message */ }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type Farmer = { id: number; name: string; phone: string | null; village: string | null; district: string | null; land_area_acres: number | null; preferred_language: string };
export type Crop = { id: number; farmer_id: number; name: string; variety: string | null; season: string | null; stage: string | null; area_acres: number | null };
export type Conversation = { id: number; farmer_id: number; title: string; language: string };
export type Message = { id: number; conversation_id: number; role: string; text: string | null; audio_mime_type: string | null };
export type Advisory = { id: number; farmer_id: number; title: string; body: string; category: string; is_demo: boolean };

export const farmerApi = {
  list: () => api<Farmer[]>("/farmers/"),
  create: (data: Omit<Farmer, "id">) => api<Farmer>("/farmers/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: Partial<Omit<Farmer, "id">>) => api<Farmer>(`/farmers/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
};
export const cropApi = {
  list: (farmerId: number) => api<Crop[]>(`/farmers/${farmerId}/crops`),
  create: (farmerId: number, data: Omit<Crop, "id" | "farmer_id">) => api<Crop>(`/farmers/${farmerId}/crops`, { method: "POST", body: JSON.stringify(data) }),
  remove: (id: number) => api<void>(`/crops/${id}`, { method: "DELETE" }),
};
export const conversationApi = {
  list: (farmerId: number) => api<Conversation[]>(`/farmers/${farmerId}/conversations`),
  messages: (id: number) => api<Message[]>(`/conversations/${id}/messages`),
  create: (farmerId: number, title: string, language = "te") => api<Conversation>(`/farmers/${farmerId}/conversations`, { method: "POST", body: JSON.stringify({ title, language }) }),
};
export type AssistantSource = { id: number; title: string; content: string; source_name: string | null; source_url: string | null; crop: string | null; topic: string | null };
export type AssistantReply = { answer: string; language: string; retrieved_sources: AssistantSource[]; conversation_id: number };
export const assistantApi = {
  chat: (farmerId: number, conversationId: number, message: string, requestId?: string) => api<AssistantReply>("/assistant/chat", { method: "POST", body: JSON.stringify({ farmer_id: farmerId, conversation_id: conversationId, message, request_id: requestId }) }),
  synthesize: async (text: string, language: "te-IN" | "en-IN" | "auto", voice?: string) => {
    let response: Response;
    try {
      response = await fetch(`${API_BASE}/voice/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, language, ...(voice ? { voice } : {}) }),
      });
    } catch {
      throw new ApiError("Could not reach KisanVaani to generate audio.", 0);
    }
    if (!response.ok) {
      let message = `Speech generation failed (${response.status}).`;
      try { const body = await response.json(); message = body.detail || message; } catch { /* use status message */ }
      throw new ApiError(message, response.status);
    }
    const contentType = response.headers.get("Content-Type")?.split(";")[0].trim() || "";
    if (!contentType.startsWith("audio/")) throw new ApiError("The speech service returned an invalid audio response.", 502);
    const audio = await response.blob();
    if (!audio.size) throw new ApiError("The speech service returned empty audio.", 502);
    return audio;
  },
};
export type Transcription = { success: true; transcript: string; model: string; request_id: string | null; language: string };
export const transcribeAudio = async (blob: Blob, mimeType: string, duration: number, farmerId?: number, conversationId?: number) => {
  const extension = mimeType.includes("ogg") ? "ogg" : mimeType.includes("wav") ? "wav" : mimeType.includes("mp4") ? "m4a" : mimeType.includes("mpeg") ? "mp3" : mimeType.includes("webm") ? "webm" : "audio";
  const form = new FormData(); form.append("audio", blob, `recording.${extension}`); form.append("language", "te-IN"); form.append("duration_seconds", duration.toFixed(3));
  if (farmerId !== undefined) form.append("farmer_id", String(farmerId));
  if (conversationId !== undefined) form.append("conversation_id", String(conversationId));
  return api<Transcription>("/voice/transcribe", { method: "POST", body: form });
};
