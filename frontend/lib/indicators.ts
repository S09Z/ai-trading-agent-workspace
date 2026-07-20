import type { StockBar } from "./types";

// ── simple moving average ─────────────────────────────────────────────────────

export function sma(values: number[], period: number): (number | null)[] {
  return values.map((_, i) => {
    if (i < period - 1) return null;
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += values[j];
    return sum / period;
  });
}

// ── exponential moving average ────────────────────────────────────────────────

export function ema(values: number[], period: number): (number | null)[] {
  const k = 2 / (period + 1);
  const result: (number | null)[] = new Array(values.length).fill(null);
  // seed with SMA of first `period` values
  let sum = 0;
  for (let i = 0; i < period && i < values.length; i++) sum += values[i];
  if (values.length < period) return result;
  result[period - 1] = sum / period;
  for (let i = period; i < values.length; i++) {
    result[i] = values[i] * k + (result[i - 1] as number) * (1 - k);
  }
  return result;
}

// ── RSI (Wilder smoothing) ────────────────────────────────────────────────────

export function rsi(closes: number[], period = 14): (number | null)[] {
  const result: (number | null)[] = new Array(closes.length).fill(null);
  if (closes.length <= period) return result;

  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const delta = closes[i] - closes[i - 1];
    if (delta > 0) avgGain += delta;
    else avgLoss -= delta;
  }
  avgGain /= period;
  avgLoss /= period;

  const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  result[period] = 100 - 100 / (1 + rs);

  for (let i = period + 1; i < closes.length; i++) {
    const delta = closes[i] - closes[i - 1];
    const gain = delta > 0 ? delta : 0;
    const loss = delta < 0 ? -delta : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    const r = avgLoss === 0 ? 100 : avgGain / avgLoss;
    result[i] = 100 - 100 / (1 + r);
  }
  return result;
}

// ── MACD ──────────────────────────────────────────────────────────────────────

export function macd(
  closes: number[],
  fast = 12,
  slow = 26,
  signalPeriod = 9
): { macd: (number | null)[]; signal: (number | null)[]; histogram: (number | null)[] } {
  const fastEma = ema(closes, fast);
  const slowEma = ema(closes, slow);
  const macdLine: (number | null)[] = closes.map((_, i) => {
    const f = fastEma[i];
    const s = slowEma[i];
    return f != null && s != null ? f - s : null;
  });

  // signal = EMA(slow-1) of MACD line values (skipping nulls)
  const macdValues = macdLine.map((v) => v ?? 0);
  const rawSignal = ema(macdValues, signalPeriod);
  const signalLine: (number | null)[] = rawSignal.map((v, i) =>
    macdLine[i] != null ? v : null
  );

  const histLine: (number | null)[] = macdLine.map((m, i) => {
    const s = signalLine[i];
    return m != null && s != null ? m - s : null;
  });

  return { macd: macdLine, signal: signalLine, histogram: histLine };
}

// ── Bollinger Bands ───────────────────────────────────────────────────────────

export function bollinger(
  closes: number[],
  period = 20,
  mult = 2
): { upper: (number | null)[]; middle: (number | null)[]; lower: (number | null)[] } {
  const middle = sma(closes, period);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];

  for (let i = 0; i < closes.length; i++) {
    const m = middle[i];
    if (m == null) {
      upper.push(null);
      lower.push(null);
      continue;
    }
    let variance = 0;
    for (let j = i - period + 1; j <= i; j++) variance += (closes[j] - m) ** 2;
    const sd = Math.sqrt(variance / period);
    upper.push(m + mult * sd);
    lower.push(m - mult * sd);
  }
  return { upper, middle, lower };
}

// ── Stochastic ────────────────────────────────────────────────────────────────

export function stochastic(
  bars: StockBar[],
  kPeriod = 14,
  dPeriod = 3
): { k: (number | null)[]; d: (number | null)[] } {
  const k: (number | null)[] = bars.map((_, i) => {
    if (i < kPeriod - 1) return null;
    let lo = Infinity;
    let hi = -Infinity;
    for (let j = i - kPeriod + 1; j <= i; j++) {
      if (bars[j].l < lo) lo = bars[j].l;
      if (bars[j].h > hi) hi = bars[j].h;
    }
    return hi === lo ? 50 : ((bars[i].c - lo) / (hi - lo)) * 100;
  });

  const kValues = k.map((v) => v ?? 0);
  const rawD = sma(kValues, dPeriod);
  const d: (number | null)[] = rawD.map((v, i) => (k[i] != null ? v : null));

  return { k, d };
}

// ── Performance series ────────────────────────────────────────────────────────

export function drawdownPct(bars: StockBar[]): number[] {
  let peak = -Infinity;
  return bars.map((b) => {
    if (b.h > peak) peak = b.h;
    return peak > 0 ? ((b.c - peak) / peak) * 100 : 0;
  });
}

export function cumulativeReturnPct(bars: StockBar[]): number[] {
  if (bars.length === 0) return [];
  const base = bars[0].c;
  return bars.map((b) => ((b.c - base) / base) * 100);
}

// ── helpers: convert bars → lightweight-charts time series ───────────────────

export function toBars(
  bars: StockBar[],
  values: (number | null)[]
): { time: string; value: number }[] {
  return bars
    .map((b, i) => ({ time: b.t, value: values[i] }))
    .filter((d): d is { time: string; value: number } => d.value != null);
}

export function toVolumeBars(
  bars: StockBar[],
  upColor: string,
  downColor: string
): { time: string; value: number; color: string }[] {
  return bars.map((b, i) => ({
    time: b.t,
    value: b.v,
    color: i === 0 || b.c >= bars[i > 0 ? i - 1 : 0].c ? upColor : downColor,
  }));
}
