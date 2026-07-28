import { API_BASE_URL } from "./env";

export type Role = "system" | "user" | "assistant";

export async function sendChat(messages: {role: Role; content: string}[], sessionId?: string) {
  const resp = await fetch(`${API_BASE_URL}/llm/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ messages, session_id: sessionId || null }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json() as Promise<{ content: string; session_id?: string }>;
}


export interface AquaIntent {
  kind:
    | "summary_all"
    | "summary_low"
    | "count_events_all"
    | "count_low"
    | "count_full"
    | "duration_empty"
    | "duration_full"
    | "unknown";
  period?: string | null;
  sensor?: "baixo" | "alto" | null;
  estado?: "subiu" | "desceu" | null;
}

export interface AgentResponse {
  answer: string;
  intent: AquaIntent;
}

export async function sendAgentQuestion(
  question: string
): Promise<AgentResponse> {
  const resp = await fetch(`${API_BASE_URL}/agent`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return resp.json() as Promise<AgentResponse>;
}
