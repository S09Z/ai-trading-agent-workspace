import type { AgentStatus } from "@/lib/types";

const LEVEL_DOT: Record<string, string> = {
  info:    "bg-green-400",
  warning: "bg-yellow-400",
  error:   "bg-red-400",
};

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export default function AgentStatusBadge({ agent }: { agent: AgentStatus }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3 flex items-center gap-3">
      <div
        className={`w-2 h-2 rounded-full shrink-0 ${LEVEL_DOT[agent.level] ?? "bg-slate-400"}`}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-mono text-white truncate">{agent.name}</p>
        <p className="text-xs text-slate-400 truncate">{agent.last_action ?? "—"}</p>
      </div>
      <span className="text-xs text-slate-500 shrink-0">{timeAgo(agent.last_seen)}</span>
    </div>
  );
}
