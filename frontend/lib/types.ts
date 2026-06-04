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
  created_at: string;
}
