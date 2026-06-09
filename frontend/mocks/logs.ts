import type { LogEntry } from "@/lib/types";

const minsAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString();

export const MOCK_LOGS: LogEntry[] = [
  { id: 1,  agent_name: "MarketWatch",     action: "price_check",       message: "NVDA +4.2% — spike logged",                                 level: "info",    created_at: minsAgo(1)   },
  { id: 2,  agent_name: "NewsHunter",      action: "fetch_rss",         message: "14 articles ingested, 3 new embeddings",                    level: "info",    created_at: minsAgo(2)   },
  { id: 3,  agent_name: "MarketWatch",     action: "price_check",       message: "TSLA -1.8% — no threshold breach",                         level: "info",    created_at: minsAgo(3)   },
  { id: 4,  agent_name: "SentimentAnalyst",action: "classify_sentiment","message": "NVDA article: bullish (0.91)",                            level: "info",    created_at: minsAgo(5)   },
  { id: 5,  agent_name: "SentimentAnalyst",action: "classify_sentiment", message: "TSLA article: bearish (0.78)",                             level: "info",    created_at: minsAgo(6)   },
  { id: 6,  agent_name: "RiskMonitor",     action: "evaluate_risk",     message: "2 spikes detected — circuit breaker not triggered",         level: "warning", created_at: minsAgo(15)  },
  { id: 7,  agent_name: "NewsHunter",      action: "fetch_rss",         message: "9 articles ingested, 1 new embedding",                      level: "info",    created_at: minsAgo(17)  },
  { id: 8,  agent_name: "SentimentAnalyst",action: "classify_sentiment", message: "OKLO article: bullish (0.84)",                             level: "info",    created_at: minsAgo(20)  },
  { id: 9,  agent_name: "MarketWatch",     action: "price_check",       message: "OKLO +6.7% — spike logged",                                 level: "info",    created_at: minsAgo(21)  },
  { id: 10, agent_name: "MarketWatch",     action: "price_check",       message: "All 35 tickers within normal range",                        level: "info",    created_at: minsAgo(31)  },
  { id: 11, agent_name: "NewsHunter",      action: "fetch_rss",         message: "12 articles ingested, 0 new embeddings (duplicates)",       level: "info",    created_at: minsAgo(32)  },
  { id: 12, agent_name: "RiskMonitor",     action: "evaluate_risk",     message: "0 spikes in last 15 min — all clear",                       level: "info",    created_at: minsAgo(45)  },
  { id: 13, agent_name: "SentimentAnalyst",action: "classify_sentiment", message: "AAPL article: neutral (0.50)",                             level: "info",    created_at: minsAgo(46)  },
  { id: 14, agent_name: "ResearchAnalyst", action: "deep_research",     message: "NVDA thesis complete — bullish, grade A/A/S",               level: "info",    created_at: minsAgo(62)  },
  { id: 15, agent_name: "NewsHunter",      action: "fetch_rss",         message: "8 articles ingested, 2 new embeddings",                     level: "info",    created_at: minsAgo(92)  },
  { id: 16, agent_name: "ResearchAnalyst", action: "deep_research",     message: "MSFT thesis complete — bullish, grade A/S/S",               level: "info",    created_at: minsAgo(94)  },
  { id: 17, agent_name: "RiskMonitor",     action: "evaluate_risk",     message: "Portfolio risk level: moderate",                            level: "info",    created_at: minsAgo(105) },
  { id: 18, agent_name: "MemoryAgent",     action: "evaluate_outcomes", message: "12 signals evaluated — 9 correct, 2 incorrect, 1 neutral",  level: "info",    created_at: minsAgo(120) },
  { id: 19, agent_name: "FinancialAnalyst",action: "analyze_financials", message: "35 tickers analyzed — metrics stored in DB",               level: "info",    created_at: minsAgo(240) },
  { id: 20, agent_name: "DiscoveryAgent",  action: "scan_universe",     message: "3 candidates found: SMCI, MSTR, PLTR",                      level: "info",    created_at: minsAgo(360) },
];
