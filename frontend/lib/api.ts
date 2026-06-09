import type { AgentStatus, LogEntry, SignalOut } from "./types";
import { MOCK_AGENTS, MOCK_SIGNALS, MOCK_LOGS } from "@/mocks";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

const IS_MOCK = process.env.NEXT_PUBLIC_MOCK_DATA === "true";
const NO_CACHE = { cache: "no-store" } as const;

export async function getAgents(): Promise<AgentStatus[]> {
  if (IS_MOCK) return MOCK_AGENTS;
  try {
    const res = await fetch(`${API}/agents`, NO_CACHE);
    if (!res.ok) return [];
    return res.json();
  } catch { return []; }
}

export async function getSignals(hours = 6, limit = 20): Promise<SignalOut[]> {
  if (IS_MOCK) return MOCK_SIGNALS.slice(0, limit);
  try {
    const res = await fetch(`${API}/signals?hours=${hours}&limit=${limit}`, NO_CACHE);
    if (!res.ok) return [];
    return res.json();
  } catch { return []; }
}

export async function getLogs(hours = 1, limit = 100): Promise<LogEntry[]> {
  if (IS_MOCK) return MOCK_LOGS.slice(0, limit);
  try {
    const res = await fetch(`${API}/logs?hours=${hours}&limit=${limit}`, NO_CACHE);
    if (!res.ok) return [];
    return res.json();
  } catch { return []; }
}
