import type { SignalOut } from "@/lib/types";

const TYPE_STYLE: Record<string, string> = {
  bullish:   "bg-green-500/20 text-green-400 border-green-500/30",
  bearish:   "bg-red-500/20 text-red-400 border-red-500/30",
  watchlist: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  alert:     "bg-orange-500/20 text-orange-400 border-orange-500/30",
};

const GRADE_STYLE: Record<string, string> = {
  S: "bg-yellow-400/20 text-yellow-300 border-yellow-400/40 font-bold",
  A: "bg-green-500/20 text-green-400 border-green-500/30",
  B: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  C: "bg-red-500/20 text-red-400 border-red-500/30",
};

const GRADE_LABEL: Record<string, string> = {
  S: "Strong Buy",
  A: "Buy",
  B: "Hold",
  C: "Sell",
};

function GradeBadge({ label, grade }: { label: string; grade: string | null }) {
  if (!grade) return null;
  const style = GRADE_STYLE[grade] ?? GRADE_STYLE.B;
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className={`text-sm font-mono font-bold px-2 py-0.5 rounded border ${style}`}>
        {grade}
      </span>
      <span className="text-[10px] text-slate-500">{label}</span>
    </div>
  );
}

function timeAgo(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export default function SignalCard({ signal }: { signal: SignalOut }) {
  const typeStyle =
    TYPE_STYLE[signal.signal_type.toLowerCase()] ??
    "bg-slate-500/20 text-slate-400 border-slate-500/30";

  const hasGrades = signal.grade_short || signal.grade_mid || signal.grade_long;

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xl font-bold text-white font-mono">{signal.ticker}</span>
        <span className={`text-xs font-semibold px-2 py-1 rounded border ${typeStyle}`}>
          {signal.signal_type.toUpperCase()}
        </span>
      </div>

      {/* Grade row */}
      {hasGrades && (
        <div className="flex items-center justify-around bg-slate-900/40 rounded-lg py-2 px-1">
          <GradeBadge label="Short" grade={signal.grade_short} />
          <div className="w-px h-8 bg-slate-700" />
          <GradeBadge label="Mid" grade={signal.grade_mid} />
          <div className="w-px h-8 bg-slate-700" />
          <GradeBadge label="Long" grade={signal.grade_long} />
        </div>
      )}

      {/* Confidence bar */}
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
