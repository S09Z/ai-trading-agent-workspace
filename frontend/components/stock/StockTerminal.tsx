"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { getStockAnalysis, getStockHistory } from "@/lib/api";
import type { StockAnalysis, StockBar, StockHistory } from "@/lib/types";

// ── palette (inline style values) ────────────────────────────────────────────
const C = {
  bg: "#0a0d3a",
  panel: "#1e2353",
  border: "#2d3478",
  green: "#35ed7e",
  magenta: "#ec48bd",
  blurple: "#5865f2",
  cyan: "#00b0f4",
  dim: "#8892c0",
  text: "#e2e8f0",
} as const;

const PRESETS = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NFLX", "TSLA"];
const TIMEFRAMES = ["1M", "3M", "6M", "1Y", "2Y", "5Y"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

const TF_DAYS: Record<Timeframe, number> = {
  "1M": 21,
  "3M": 63,
  "6M": 126,
  "1Y": 252,
  "2Y": 504,
  "5Y": 9999,
};

const TABS = ["Overview", "AI Analysis", "Technical", "Performance"] as const;
type Tab = (typeof TABS)[number];

// ── stat helpers ──────────────────────────────────────────────────────────────

function sliceBars(bars: StockBar[], tf: Timeframe): StockBar[] {
  return bars.slice(-Math.min(TF_DAYS[tf], bars.length));
}

function overviewStats(bars: StockBar[]) {
  if (bars.length === 0)
    return { high52: null, low52: null, tfReturn: null, avgVol20: null };
  const high52 = Math.max(...bars.map((b) => b.h));
  const low52 = Math.min(...bars.map((b) => b.l));
  const first = bars[0].c;
  const last = bars[bars.length - 1].c;
  const tfReturn = ((last - first) / first) * 100;
  const recent = bars.slice(-20);
  const avgVol20 = recent.reduce((s, b) => s + b.v, 0) / recent.length;
  return { high52, low52, tfReturn, avgVol20 };
}

function perfStats(bars: StockBar[]) {
  if (bars.length < 2)
    return { sharpe: null, vol: null, maxDD: null, totalReturn: null };
  const rets = bars
    .slice(1)
    .map((b, i) => (b.c - bars[i].c) / bars[i].c);
  const mean = rets.reduce((s, r) => s + r, 0) / rets.length;
  const variance =
    rets.reduce((s, r) => s + (r - mean) ** 2, 0) / rets.length;
  const annVol = Math.sqrt(variance * 252);
  const sharpe = annVol > 0 ? (mean * 252) / annVol : 0;
  let peak = bars[0].c;
  let maxDD = 0;
  for (const b of bars) {
    if (b.h > peak) peak = b.h;
    const dd = (peak - b.l) / peak;
    if (dd > maxDD) maxDD = dd;
  }
  const totalReturn = (bars[bars.length - 1].c / bars[0].c - 1) * 100;
  return {
    sharpe: +sharpe.toFixed(2),
    vol: +(annVol * 100).toFixed(1),
    maxDD: +(maxDD * 100).toFixed(1),
    totalReturn: +totalReturn.toFixed(1),
  };
}

// ── formatters ────────────────────────────────────────────────────────────────

const fmtNum = (n: number | null | undefined, decimals = 2) =>
  n == null ? "—" : n.toFixed(decimals);

const fmtMCap = (n: number | null) => {
  if (n == null) return "—";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  return `$${(n / 1e6).toFixed(0)}M`;
};

const fmtVol = (n: number | null) => {
  if (n == null) return "—";
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return String(n);
};

const fmtDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—";

const GRADE_COLOR: Record<string, string> = {
  S: "#fde047",
  A: C.green,
  B: "#94a3b8",
  C: "#f87171",
};

const OUTCOME_COLOR: Record<string, string> = {
  correct: C.green,
  incorrect: "#f87171",
  neutral: C.dim,
};

// ── small UI atoms ────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-1"
      style={{ background: C.panel, border: `1px solid ${C.border}` }}
    >
      <span className="text-xs uppercase tracking-wider" style={{ color: C.dim }}>
        {label}
      </span>
      <span
        className="text-2xl font-bold"
        style={{
          color: accent ?? C.text,
          fontFamily: "var(--font-space-grotesk, sans-serif)",
        }}
      >
        {value}
      </span>
      {sub && (
        <span className="text-xs" style={{ color: C.dim }}>
          {sub}
        </span>
      )}
    </div>
  );
}

function ChartPlaceholder({ label }: { label: string }) {
  return (
    <div
      className="rounded-xl flex items-center justify-center h-64"
      style={{ background: C.panel, border: `1px dashed ${C.border}` }}
    >
      <span className="text-sm" style={{ color: C.dim }}>
        {label} — charts in sub-task C
      </span>
    </div>
  );
}

// ── tab panels ────────────────────────────────────────────────────────────────

function OverviewPanel({
  bars,
  tf,
}: {
  bars: StockBar[];
  tf: Timeframe;
}) {
  const slice = sliceBars(bars, tf);
  const s = overviewStats(slice);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="52W High"
          value={s.high52 != null ? `$${fmtNum(s.high52)}` : "—"}
        />
        <StatCard
          label="52W Low"
          value={s.low52 != null ? `$${fmtNum(s.low52)}` : "—"}
        />
        <StatCard
          label={`${tf} Return`}
          value={s.tfReturn != null ? `${s.tfReturn.toFixed(1)}%` : "—"}
          accent={
            s.tfReturn == null ? undefined : s.tfReturn >= 0 ? C.green : "#f87171"
          }
        />
        <StatCard
          label="Avg Vol 20d"
          value={fmtVol(s.avgVol20)}
        />
      </div>
      <ChartPlaceholder label="Candlestick + Volume" />
    </div>
  );
}

function AIPanel({ analysis }: { analysis: StockAnalysis | null }) {
  if (!analysis?.has_analysis) {
    return (
      <div
        className="rounded-xl p-10 text-center space-y-2"
        style={{ background: C.panel, border: `1px solid ${C.border}` }}
      >
        <p className="text-lg font-semibold" style={{ color: C.dim }}>
          No analysis available
        </p>
        <p className="text-sm" style={{ color: C.dim }}>
          Run{" "}
          <code
            className="px-1 py-0.5 rounded text-xs"
            style={{ background: C.border, color: C.text }}
          >
            make financial
          </code>{" "}
          to generate composite scores for this ticker.
        </p>
      </div>
    );
  }

  const score = analysis.composite_score ?? 0;
  const grade = analysis.grade_short ?? "—";
  const gradeColor = GRADE_COLOR[grade] ?? C.dim;
  const breakdown = Object.entries(analysis.composite_breakdown ?? {}).sort(
    ([, a], [, b]) => b - a
  );
  const maxFactor = breakdown[0]?.[1] ?? 1;

  return (
    <div className="space-y-4">
      {/* Headline */}
      <div
        className="rounded-xl p-5 flex items-center justify-between"
        style={{ background: C.panel, border: `1px solid ${C.border}` }}
      >
        <div>
          <p className="text-sm uppercase tracking-wider mb-1" style={{ color: C.dim }}>
            Composite Score
          </p>
          <div className="flex items-baseline gap-3">
            <span
              className="text-5xl font-bold"
              style={{
                color: gradeColor,
                fontFamily: "var(--font-space-grotesk, sans-serif)",
              }}
            >
              {grade}
            </span>
            <span className="text-3xl font-semibold" style={{ color: C.text }}>
              {score.toFixed(1)}
              <span className="text-base" style={{ color: C.dim }}>
                {" "}
                / 100
              </span>
            </span>
          </div>
          <p className="text-sm mt-1 capitalize" style={{ color: C.dim }}>
            {analysis.signal_type} · {((analysis.confidence ?? 0) * 100).toFixed(0)}% confidence
          </p>
        </div>
        <div className="flex gap-3">
          {(["grade_short", "grade_mid", "grade_long"] as const).map((key, i) => {
            const g = analysis[key];
            const labels = ["Short", "Mid", "Long"];
            if (!g) return null;
            return (
              <div key={key} className="flex flex-col items-center gap-1">
                <span
                  className="text-2xl font-bold"
                  style={{ color: GRADE_COLOR[g] ?? C.dim }}
                >
                  {g}
                </span>
                <span className="text-[10px]" style={{ color: C.dim }}>
                  {labels[i]}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Factor breakdown */}
      {breakdown.length > 0 && (
        <div
          className="rounded-xl p-5 space-y-3"
          style={{ background: C.panel, border: `1px solid ${C.border}` }}
        >
          <p
            className="text-xs uppercase tracking-wider"
            style={{ color: C.dim }}
          >
            Factor Breakdown
          </p>
          {breakdown.map(([factor, val]) => (
            <div key={factor} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="capitalize" style={{ color: C.text }}>
                  {factor}
                </span>
                <span style={{ color: C.dim }}>{val.toFixed(1)}</span>
              </div>
              <div
                className="h-2 rounded-full overflow-hidden"
                style={{ background: C.border }}
              >
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${(val / maxFactor) * 100}%`,
                    background: C.blurple,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Rationale */}
      {analysis.rationale && (
        <div
          className="rounded-xl p-5"
          style={{ background: C.panel, border: `1px solid ${C.border}` }}
        >
          <p
            className="text-xs uppercase tracking-wider mb-2"
            style={{ color: C.dim }}
          >
            AI Insights
          </p>
          <p className="text-sm leading-relaxed" style={{ color: C.text }}>
            {analysis.rationale}
          </p>
          <p className="text-xs mt-2" style={{ color: C.dim }}>
            {analysis.source_agent?.replace(/_/g, " ")} ·{" "}
            {fmtDate(analysis.created_at)}
          </p>
        </div>
      )}

      {/* Model performance */}
      <div
        className="rounded-xl p-5 space-y-3"
        style={{ background: C.panel, border: `1px solid ${C.border}` }}
      >
        <div className="flex items-center justify-between">
          <p
            className="text-xs uppercase tracking-wider"
            style={{ color: C.dim }}
          >
            Signal Track Record
          </p>
          {analysis.accuracy_pct != null && (
            <span
              className="text-sm font-semibold"
              style={{ color: C.green }}
            >
              {analysis.accuracy_pct.toFixed(1)}% accuracy
            </span>
          )}
        </div>
        {analysis.outcomes.length === 0 ? (
          <p className="text-sm" style={{ color: C.dim }}>
            No evaluated outcomes yet.
          </p>
        ) : (
          <div className="space-y-2">
            {analysis.outcomes.slice(0, 5).map((o) => (
              <div
                key={o.id}
                className="flex items-center justify-between text-sm rounded-lg px-3 py-2"
                style={{ background: C.bg }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{
                      background:
                        OUTCOME_COLOR[o.outcome_5d ?? "neutral"] ?? C.dim,
                    }}
                  />
                  <span style={{ color: C.dim }}>{fmtDate(o.created_at)}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span style={{ color: C.dim }}>
                    ${o.price_at_signal?.toFixed(2) ?? "—"} → $
                    {o.price_5d?.toFixed(2) ?? "—"}
                  </span>
                  <span
                    style={{
                      color: OUTCOME_COLOR[o.outcome_5d ?? "neutral"] ?? C.dim,
                    }}
                  >
                    {o.change_pct_5d != null
                      ? `${o.change_pct_5d > 0 ? "+" : ""}${o.change_pct_5d.toFixed(2)}%`
                      : "—"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TechnicalPanel({ bars, tf }: { bars: StockBar[]; tf: Timeframe }) {
  const slice = sliceBars(bars, tf);
  const last = slice[slice.length - 1];
  const prev20 = slice.slice(-20);
  const sma20 =
    prev20.length > 0
      ? prev20.reduce((s, b) => s + b.c, 0) / prev20.length
      : null;
  const vsma = sma20 != null && last ? ((last.c - sma20) / sma20) * 100 : null;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Last Close"
          value={last ? `$${last.c.toFixed(2)}` : "—"}
        />
        <StatCard
          label="SMA 20"
          value={sma20 != null ? `$${sma20.toFixed(2)}` : "—"}
        />
        <StatCard
          label="vs SMA 20"
          value={vsma != null ? `${vsma.toFixed(2)}%` : "—"}
          accent={vsma == null ? undefined : vsma >= 0 ? C.green : "#f87171"}
        />
        <StatCard
          label="Volume (last)"
          value={last ? fmtVol(last.v) : "—"}
        />
      </div>
      <ChartPlaceholder label="Price + Bollinger + SMA overlay" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <ChartPlaceholder label="RSI (14)" />
        <ChartPlaceholder label="MACD" />
        <ChartPlaceholder label="Stochastic" />
      </div>
    </div>
  );
}

function PerformancePanel({ bars, tf }: { bars: StockBar[]; tf: Timeframe }) {
  const slice = sliceBars(bars, tf);
  const s = perfStats(slice);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Sharpe Ratio"
          value={s.sharpe != null ? fmtNum(s.sharpe) : "—"}
          accent={s.sharpe == null ? undefined : s.sharpe >= 1 ? C.green : s.sharpe < 0 ? "#f87171" : C.text}
        />
        <StatCard
          label={`${tf} Volatility`}
          value={s.vol != null ? `${fmtNum(s.vol, 1)}%` : "—"}
        />
        <StatCard
          label="Max Drawdown"
          value={s.maxDD != null ? `-${fmtNum(s.maxDD, 1)}%` : "—"}
          accent="#f87171"
        />
        <StatCard
          label={`${tf} Return`}
          value={s.totalReturn != null ? `${fmtNum(s.totalReturn, 1)}%` : "—"}
          accent={
            s.totalReturn == null
              ? undefined
              : s.totalReturn >= 0
              ? C.green
              : "#f87171"
          }
        />
      </div>
      <ChartPlaceholder label="Drawdown curve" />
      <ChartPlaceholder label="Cumulative return" />
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export default function StockTerminal({ ticker }: { ticker: string }) {
  const router = useRouter();
  const [history, setHistory] = useState<StockHistory | null>(null);
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [tf, setTf] = useState<Timeframe>("1Y");
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // key={ticker} on the page causes remount on ticker change, so loading
    // starts as true (useState default) and only transitions here on resolve.
    Promise.all([getStockHistory(ticker), getStockAnalysis(ticker)]).then(
      ([h, a]) => {
        setHistory(h);
        setAnalysis(a);
        setLoading(false);
      }
    );
  }, [ticker]);

  function handleAnalyze(e: FormEvent) {
    e.preventDefault();
    const sym = (inputRef.current?.value ?? "").trim().toUpperCase();
    if (sym && sym !== ticker) router.push(`/stock/${sym}`);
  }

  const meta = history?.meta;
  const bars = history?.bars ?? [];
  const isUp = (meta?.change ?? 0) >= 0;

  return (
    <div
      className="flex min-h-screen"
      style={{ fontFamily: "var(--font-inter, sans-serif)" }}
    >
      {/* ── sidebar ─────────────────────────────────────────────────────── */}
      <aside
        className="w-[280px] shrink-0 flex flex-col gap-6 p-5 overflow-y-auto"
        style={{
          background: C.panel,
          borderRight: `1px solid ${C.border}`,
          minHeight: "100vh",
        }}
      >
        {/* Logo */}
        <div>
          <h1
            className="text-base font-bold leading-tight"
            style={{
              color: C.text,
              fontFamily: "var(--font-space-grotesk, sans-serif)",
            }}
          >
            StockSense
          </h1>
          <p className="text-[11px]" style={{ color: C.dim }}>
            AI Market Terminal
          </p>
        </div>

        {/* Symbol input */}
        <form onSubmit={handleAnalyze} className="space-y-2">
          <label className="text-xs uppercase tracking-wider" style={{ color: C.dim }}>
            Symbol
          </label>
          <input
            ref={inputRef}
            type="text"
            defaultValue={ticker}
            onChange={(e) => {
              e.target.value = e.target.value.toUpperCase();
            }}
            placeholder="e.g. NVDA"
            className="w-full rounded-lg px-3 py-2 text-sm font-mono uppercase outline-none"
            style={{
              background: C.bg,
              border: `1px solid ${C.border}`,
              color: C.text,
            }}
          />
          <button
            type="submit"
            className="w-full rounded-lg py-2 text-sm font-semibold transition-opacity hover:opacity-80"
            style={{ background: C.blurple, color: "#fff" }}
          >
            Analyze
          </button>
        </form>

        {/* Popular tickers */}
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wider" style={{ color: C.dim }}>
            Popular
          </p>
          <div className="grid grid-cols-2 gap-1">
            {PRESETS.map((sym) => (
              <Link
                key={sym}
                href={`/stock/${sym}`}
                className="rounded-lg px-2 py-1.5 text-sm font-mono text-center transition-colors hover:opacity-80"
                style={{
                  background: sym === ticker ? C.blurple : C.bg,
                  color: sym === ticker ? "#fff" : C.dim,
                  border: `1px solid ${C.border}`,
                }}
              >
                {sym}
              </Link>
            ))}
          </div>
        </div>

        {/* Timeframe */}
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wider" style={{ color: C.dim }}>
            Timeframe
          </p>
          <div className="grid grid-cols-3 gap-1">
            {TIMEFRAMES.map((t) => (
              <button
                key={t}
                onClick={() => setTf(t)}
                className="rounded-lg py-1.5 text-xs font-mono transition-colors"
                style={{
                  background: tf === t ? C.blurple : C.bg,
                  color: tf === t ? "#fff" : C.dim,
                  border: `1px solid ${C.border}`,
                }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* LIVE badge */}
        <div className="mt-auto flex items-center gap-2">
          <span
            className="inline-block w-2 h-2 rounded-full animate-pulse"
            style={{ background: C.green }}
          />
          <span className="text-xs" style={{ color: C.dim }}>
            Delayed 15m
          </span>
        </div>

        {/* Back link */}
        <Link
          href="/"
          className="text-xs transition-opacity hover:opacity-80"
          style={{ color: C.dim }}
        >
          ← Dashboard
        </Link>
      </aside>

      {/* ── main ────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Hero */}
        <div
          className="p-6"
          style={{
            background: `linear-gradient(135deg, #1e2353 0%, #0a0d3a 60%)`,
            borderBottom: `1px solid ${C.border}`,
          }}
        >
          {loading ? (
            <div className="h-20 flex items-center" style={{ color: C.dim }}>
              Loading {ticker}…
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h2
                      className="text-4xl font-bold"
                      style={{
                        color: C.text,
                        fontFamily: "var(--font-space-grotesk, sans-serif)",
                      }}
                    >
                      {ticker}
                    </h2>
                    {analysis?.signal_type && (
                      <span
                        className="text-xs font-semibold px-2 py-0.5 rounded uppercase"
                        style={{
                          background:
                            analysis.signal_type === "bullish"
                              ? "rgba(53,237,126,0.15)"
                              : analysis.signal_type === "bearish"
                              ? "rgba(248,113,113,0.15)"
                              : "rgba(136,146,192,0.15)",
                          color:
                            analysis.signal_type === "bullish"
                              ? C.green
                              : analysis.signal_type === "bearish"
                              ? "#f87171"
                              : C.dim,
                          border: `1px solid ${
                            analysis.signal_type === "bullish"
                              ? "rgba(53,237,126,0.3)"
                              : analysis.signal_type === "bearish"
                              ? "rgba(248,113,113,0.3)"
                              : C.border
                          }`,
                        }}
                      >
                        {analysis.signal_type}
                      </span>
                    )}
                  </div>
                  {meta?.name && (
                    <p className="text-sm mt-0.5" style={{ color: C.dim }}>
                      {meta.name}
                    </p>
                  )}
                </div>

                {/* Price */}
                <div className="text-right">
                  <p
                    className="text-4xl font-bold"
                    style={{
                      color: C.text,
                      fontFamily: "var(--font-space-grotesk, sans-serif)",
                    }}
                  >
                    ${meta?.price?.toFixed(2) ?? "—"}
                  </p>
                  <p
                    className="text-base font-semibold"
                    style={{ color: isUp ? C.green : "#f87171" }}
                  >
                    {isUp ? "+" : ""}
                    {meta?.change?.toFixed(2) ?? "—"} (
                    {isUp ? "+" : ""}
                    {meta?.change_pct?.toFixed(2) ?? "—"}%)
                  </p>
                </div>
              </div>

              {/* Meta chips */}
              <div className="flex flex-wrap gap-4 mt-4">
                {[
                  { label: "Market Cap", value: fmtMCap(meta?.market_cap ?? null) },
                  { label: "P/E Ratio", value: meta?.pe != null ? meta.pe.toFixed(1) : "—" },
                  { label: "Volume", value: fmtVol(meta?.volume ?? null) },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <p className="text-[10px] uppercase tracking-wider" style={{ color: C.dim }}>
                      {label}
                    </p>
                    <p className="text-sm font-semibold" style={{ color: C.text }}>
                      {value}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Tab nav */}
        <div
          className="flex border-b px-6"
          style={{ background: C.bg, borderColor: C.border }}
        >
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="px-4 py-3 text-sm font-medium transition-colors"
              style={{
                color: activeTab === tab ? C.blurple : C.dim,
                borderBottom:
                  activeTab === tab ? `2px solid ${C.blurple}` : "2px solid transparent",
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab panels */}
        <div
          className="flex-1 overflow-y-auto p-6"
          style={{ background: C.bg }}
        >
          {loading ? (
            <div className="flex items-center justify-center h-40" style={{ color: C.dim }}>
              Loading…
            </div>
          ) : (
            <>
              {activeTab === "Overview" && (
                <OverviewPanel bars={bars} tf={tf} />
              )}
              {activeTab === "AI Analysis" && (
                <AIPanel analysis={analysis} />
              )}
              {activeTab === "Technical" && (
                <TechnicalPanel bars={bars} tf={tf} />
              )}
              {activeTab === "Performance" && (
                <PerformancePanel bars={bars} tf={tf} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
