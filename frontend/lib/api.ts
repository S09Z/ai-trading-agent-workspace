import type { AgentStatus, LogEntry, SignalOut, SwarmPreset } from "./types";
import { MOCK_AGENTS, MOCK_SIGNALS, MOCK_LOGS, MOCK_PRESETS } from "@/mocks";

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

export async function getSwarmPresets(): Promise<SwarmPreset[]> {
  if (IS_MOCK) return MOCK_PRESETS;
  try {
    const res = await fetch(`${API}/swarm/presets`, NO_CACHE);
    if (!res.ok) return [];
    return res.json();
  } catch { return []; }
}

export async function runSwarm(preset: string): Promise<{ ok: boolean; detail?: string }> {
  try {
    const res = await fetch(`${API}/swarm/run/${preset}`, { method: "POST" });
    if (res.ok) return { ok: true };
    const body = await res.json().catch(() => null);
    return { ok: false, detail: body?.detail ?? `HTTP ${res.status}` };
  } catch (e) {
    return { ok: false, detail: e instanceof Error ? e.message : "network error" };
  }
}
