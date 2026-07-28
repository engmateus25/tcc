import { API_BASE_URL } from "./env";

export type Role = "system" | "user" | "assistant";

export async function sendChat(messages: {role: Role; content: string}[], sessionId?: string) {
  const resp = await fetch(`${API_BASE_URL}/llm/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ messages, session_id: sessionId || null }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json() as Promise<{
    content: string;
    session_id?: string;
    provider?: string | null;
    model?: string | null;
  }>;
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
    | "count_empty_and_full"
    | "count_and_duration_empty"
    | "count_and_duration_full"
    | "health_check"
    | "water_consumption"
    | "energy_consumption"
    | "alerts_summary"
    | "smalltalk"
    | "unknown";
  period?: string | null;
  sensor?: "baixo" | "alto" | null;
  estado?: "subiu" | "desceu" | null;
}

export interface AgentResponse {
  answer: string;
  intent: AquaIntent;
  provider?: string | null;
  model?: string | null;
  session_id?: string | null;
  fallback_used?: boolean;
  llm_error?: string | null;
  metadata?: Record<string, unknown>;
}

export async function sendAgentQuestion(
  question: string,
  sessionId?: string | null,
): Promise<AgentResponse> {
  const resp = await fetch(`${API_BASE_URL}/agent`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId || null }),
  });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return resp.json() as Promise<AgentResponse>;
}
