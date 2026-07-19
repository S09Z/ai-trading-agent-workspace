import type { StockHistory, StockAnalysis } from "@/lib/types";

// Deterministic pseudo-random from index
function r(n: number): number {
  const x = Math.sin(n * 127.1 + 1.5) * 10000;
  return x - Math.floor(x);
}

function makeBars(
  n: number,
  startPrice: number,
  seed = 0
): StockHistory["bars"] {
  const bars: StockHistory["bars"] = [];
  let price = startPrice;
  // Start roughly n trading days ago (1.4 calendar days per trading day)
  const origin = new Date("2025-07-15");
  origin.setDate(origin.getDate() - Math.round(n * 1.4));

  for (let i = 0; i < n; i++) {
    const d = new Date(origin);
    d.setDate(d.getDate() + Math.round(i * 1.4));
    const pct = (r(i + seed) - 0.47) * 0.025;
    const o = +price.toFixed(2);
    price = Math.max(price * (1 + pct), 1);
    const c = +price.toFixed(2);
    const h = +(Math.max(o, c) * (1 + r(i * 3 + seed) * 0.008)).toFixed(2);
    const l = +(Math.min(o, c) * (1 - r(i * 7 + seed) * 0.008)).toFixed(2);
    bars.push({
      t: d.toISOString().slice(0, 10),
      o,
      h,
      l,
      c,
      v: Math.floor(15_000_000 + r(i * 11 + seed) * 25_000_000),
    });
  }
  return bars;
}

const NVDA_BARS = makeBars(260, 420, 0);
const AAPL_BARS = makeBars(260, 175, 42);
const MSFT_BARS = makeBars(260, 380, 99);

function metaFrom(
  ticker: string,
  name: string,
  bars: StockHistory["bars"],
  marketCap: number,
  pe: number
): StockHistory["meta"] {
  const last = bars[bars.length - 1];
  const prev = bars[bars.length - 2];
  return {
    ticker,
    name,
    market_cap: marketCap,
    pe,
    price: last.c,
    change: +(last.c - prev.c).toFixed(2),
    change_pct: +((last.c - prev.c) / prev.c * 100).toFixed(2),
    volume: last.v,
  };
}

export const MOCK_STOCK_HISTORY: Record<string, StockHistory> = {
  NVDA: {
    meta: metaFrom("NVDA", "NVIDIA Corporation", NVDA_BARS, 3.2e12, 42.1),
    bars: NVDA_BARS,
  },
  AAPL: {
    meta: metaFrom("AAPL", "Apple Inc.", AAPL_BARS, 3.1e12, 31.5),
    bars: AAPL_BARS,
  },
  MSFT: {
    meta: metaFrom("MSFT", "Microsoft Corporation", MSFT_BARS, 2.9e12, 36.8),
    bars: MSFT_BARS,
  },
};

const ago = (days: number) =>
  new Date(Date.now() - days * 86_400_000).toISOString();

export const MOCK_STOCK_ANALYSIS: Record<string, StockAnalysis> = {
  NVDA: {
    ticker: "NVDA",
    has_analysis: true,
    composite_score: 78.5,
    composite_breakdown: {
      momentum: 22.0,
      quality: 19.5,
      liquidity: 18.0,
      volatility: 19.0,
    },
    signal_type: "bullish",
    confidence: 0.87,
    grade_short: "S",
    grade_mid: "A",
    grade_long: "A",
    rationale:
      "Strong AI inference demand cycle. Data center revenue +122% YoY. Blackwell ramp ahead of schedule. Institutional accumulation visible in options flow.",
    source_agent: "financial_analyst",
    created_at: ago(0),
    outcomes: [
      {
        id: 1,
        signal_id: 1,
        ticker: "NVDA",
        signal_type: "bullish",
        source_agent: "financial_analyst",
        price_at_signal: 410.0,
        price_5d: 425.5,
        outcome_5d: "correct",
        change_pct_5d: 3.78,
        created_at: ago(7),
        evaluated_at: ago(2),
      },
      {
        id: 2,
        signal_id: 2,
        ticker: "NVDA",
        signal_type: "bullish",
        source_agent: "financial_analyst",
        price_at_signal: 390.0,
        price_5d: 385.0,
        outcome_5d: "incorrect",
        change_pct_5d: -1.28,
        created_at: ago(30),
        evaluated_at: ago(25),
      },
      {
        id: 3,
        signal_id: 3,
        ticker: "NVDA",
        signal_type: "bullish",
        source_agent: "financial_analyst",
        price_at_signal: 375.0,
        price_5d: 395.0,
        outcome_5d: "correct",
        change_pct_5d: 5.33,
        created_at: ago(60),
        evaluated_at: ago(55),
      },
    ],
    accuracy_pct: 66.7,
  },
  AAPL: {
    ticker: "AAPL",
    has_analysis: true,
    composite_score: 61.2,
    composite_breakdown: {
      momentum: 14.0,
      quality: 18.2,
      liquidity: 15.5,
      volatility: 13.5,
    },
    signal_type: "watchlist",
    confidence: 0.61,
    grade_short: "B",
    grade_mid: "A",
    grade_long: "A",
    rationale:
      "iPhone cycle stable. Apple Intelligence rollout gaining traction. Services revenue accelerating in Q3.",
    source_agent: "financial_analyst",
    created_at: ago(0),
    outcomes: [],
    accuracy_pct: null,
  },
  MSFT: {
    ticker: "MSFT",
    has_analysis: false,
    composite_score: null,
    composite_breakdown: {},
    signal_type: null,
    confidence: null,
    grade_short: null,
    grade_mid: null,
    grade_long: null,
    rationale: null,
    source_agent: null,
    created_at: null,
    outcomes: [],
    accuracy_pct: null,
  },
};
