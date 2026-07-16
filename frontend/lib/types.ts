export interface AgentStatus {
  name: string;
  last_action: string | null;
  last_message: string | null;
  last_seen: string | null;
  level: "info" | "warning" | "error";
}

export interface LogEntry {
  id: number;
  agent_name: string;
  action: string;
  message: string;
  level: string;
  created_at: string;
}

export interface SignalOut {
  id: number;
  ticker: string;
  signal_type: string;
  confidence: number;
  source_agent: string;
  rationale: string | null;
  grade_short: string | null;
  grade_mid: string | null;
  grade_long: string | null;
  created_at: string;
}

export interface StockBar {
  t: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

export interface StockMeta {
  ticker: string;
  name: string | null;
  market_cap: number | null;
  pe: number | null;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  volume: number | null;
}

export interface StockHistory {
  meta: StockMeta;
  bars: StockBar[];
}

export interface SignalOutcomeOut {
  id: number;
  signal_id: number;
  ticker: string;
  signal_type: string;
  source_agent: string;
  price_at_signal: number | null;
  price_5d: number | null;
  outcome_5d: string | null;
  change_pct_5d: number | null;
  created_at: string;
  evaluated_at: string | null;
}

export interface StockAnalysis {
  ticker: string;
  has_analysis: boolean;
  composite_score: number | null;
  composite_breakdown: Record<string, number>;
  signal_type: string | null;
  confidence: number | null;
  grade_short: string | null;
  grade_mid: string | null;
  grade_long: string | null;
  rationale: string | null;
  source_agent: string | null;
  created_at: string | null;
  outcomes: SignalOutcomeOut[];
  accuracy_pct: number | null;
}
