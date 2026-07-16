import type { AgentStatus, LogEntry, SignalOut, StockHistory, StockAnalysis } from "./types";
import { MOCK_AGENTS, MOCK_SIGNALS, MOCK_LOGS, MOCK_STOCK_HISTORY, MOCK_STOCK_ANALYSIS } from "@/mocks";

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

export async function getStockHistory(ticker: string): Promise<StockHistory | null> {
  const key = ticker.toUpperCase();
  if (IS_MOCK) return MOCK_STOCK_HISTORY[key] ?? MOCK_STOCK_HISTORY["NVDA"] ?? null;
  try {
    const res = await fetch(`${API}/stocks/${key}/history`, NO_CACHE);
    if (!res.ok) return null;
    return res.json();
  } catch { return null; }
}

export async function getStockAnalysis(ticker: string): Promise<StockAnalysis | null> {
  const key = ticker.toUpperCase();
  if (IS_MOCK) return MOCK_STOCK_ANALYSIS[key] ?? null;
  try {
    const res = await fetch(`${API}/stocks/${key}/analysis`, NO_CACHE);
    if (!res.ok) return null;
    return res.json();
  } catch { return null; }
}
