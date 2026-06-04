import type { AgentStatus, LogEntry, SignalOut } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

const NO_CACHE = { cache: "no-store" } as const;

export async function getAgents(): Promise<AgentStatus[]> {
  const res = await fetch(`${API}/agents`, NO_CACHE);
  return res.json();
}

export async function getSignals(hours = 6, limit = 20): Promise<SignalOut[]> {
  const res = await fetch(`${API}/signals?hours=${hours}&limit=${limit}`, NO_CACHE);
  return res.json();
}

export async function getLogs(hours = 1, limit = 100): Promise<LogEntry[]> {
  const res = await fetch(`${API}/logs?hours=${hours}&limit=${limit}`, NO_CACHE);
  return res.json();
}
