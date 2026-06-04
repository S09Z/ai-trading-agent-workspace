import type { SignalOut } from "@/lib/types";

const TYPE_STYLE: Record<string, string> = {
  BUY:  "bg-green-500/20 text-green-400 border-green-500/30",
  SELL: "bg-red-500/20 text-red-400 border-red-500/30",
  HOLD: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
};

function timeAgo(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export default function SignalCard({ signal }: { signal: SignalOut }) {
  const typeStyle =
    TYPE_STYLE[signal.signal_type.toUpperCase()] ??
    "bg-slate-500/20 text-slate-400 border-slate-500/30";

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xl font-bold text-white font-mono">{signal.ticker}</span>
        <span className={`text-xs font-semibold px-2 py-1 rounded border ${typeStyle}`}>
          {signal.signal_type.toUpperCase()}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 bg-slate-700 rounded-full h-1.5">
          <div
            className="h-1.5 rounded-full bg-blue-500 transition-all"
            style={{ width: `${signal.confidence * 100}%` }}
          />
        </div>
        <span className="text-xs text-slate-400 font-mono w-8 text-right">
          {(signal.confidence * 100).toFixed(0)}%
        </span>
      </div>

      {signal.rationale && (
        <p className="text-xs text-slate-400 line-clamp-2">{signal.rationale}</p>
      )}

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{signal.source_agent.replace(/_/g, " ")}</span>
        <span>{timeAgo(signal.created_at)}</span>
      </div>
    </div>
  );
}
