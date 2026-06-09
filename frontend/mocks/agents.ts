import type { AgentStatus } from "@/lib/types";

const now = () => new Date().toISOString();
const minsAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString();

export const MOCK_AGENTS: AgentStatus[] = [
  {
    name: "NewsHunter",
    last_action: "fetch_rss",
    last_message: "Ingested 14 articles from 8 feeds, 3 new embeddings stored",
    last_seen: minsAgo(2),
    level: "info",
  },
  {
    name: "MarketWatch",
    last_action: "price_check",
    last_message: "NVDA +4.2% spike detected — circuit breaker threshold not reached",
    last_seen: minsAgo(1),
    level: "info",
  },
  {
    name: "SentimentAnalyst",
    last_action: "classify_sentiment",
    last_message: "Classified 11 articles — 7 bullish, 2 bearish, 2 neutral",
    last_seen: minsAgo(5),
    level: "info",
  },
  {
    name: "RiskMonitor",
    last_action: "evaluate_risk",
    last_message: "2 spikes in last 15 min — below circuit breaker threshold (3)",
    last_seen: minsAgo(15),
    level: "warning",
  },
  {
    name: "ResearchAnalyst",
    last_action: "deep_research",
    last_message: "NVDA thesis generated — bullish (A/A/S) based on AI demand cycle",
    last_seen: minsAgo(60),
    level: "info",
  },
  {
    name: "MemoryAgent",
    last_action: "evaluate_outcomes",
    last_message: "Evaluated 12 past signals — 75% correct, 2 incorrect, 1 neutral",
    last_seen: minsAgo(120),
    level: "info",
  },
  {
    name: "FinancialAnalyst",
    last_action: "analyze_financials",
    last_message: "Analyzed 35 tickers — P/E, revenue growth, margins stored",
    last_seen: minsAgo(240),
    level: "info",
  },
  {
    name: "DiscoveryAgent",
    last_action: "scan_universe",
    last_message: "Found 3 new candidates from 199-ticker universe: SMCI, MSTR, PLTR",
    last_seen: minsAgo(360),
    level: "info",
  },
];
