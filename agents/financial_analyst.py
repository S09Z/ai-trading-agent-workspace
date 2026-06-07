import asyncio
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from agents.base import BaseAgent
from config.settings import get_settings
from memory.database import AsyncSessionLocal, Signal

_settings = get_settings()

_SYSTEM = "You are a fundamental financial analyst. Be concise, structured, and direct."

_VALID_GRADES = {"S", "A", "B", "C"}

# Metrics to pull from yfinance .info
_METRIC_KEYS = (
    "revenueGrowth", "earningsGrowth", "profitMargins", "grossMargins",
    "operatingMargins", "returnOnEquity", "debtToEquity", "currentRatio",
    "freeCashflow", "trailingPE", "forwardPE", "priceToSalesTrailing12Months",
    "totalCash", "totalDebt", "marketCap", "trailingEps", "forwardEps",
)

_LABELS = {
    "revenueGrowth":               "Revenue Growth (YoY)",
    "earningsGrowth":              "Earnings Growth (YoY)",
    "profitMargins":               "Net Profit Margin",
    "grossMargins":                "Gross Margin",
    "operatingMargins":            "Operating Margin",
    "returnOnEquity":              "Return on Equity",
    "debtToEquity":                "Debt / Equity",
    "currentRatio":                "Current Ratio",
    "freeCashflow":                "Free Cash Flow",
    "trailingPE":                  "P/E (trailing)",
    "forwardPE":                   "P/E (forward)",
    "priceToSalesTrailing12Months":"P/S Ratio",
    "totalCash":                   "Cash & Equivalents",
    "totalDebt":                   "Total Debt",
    "marketCap":                   "Market Cap",
    "trailingEps":                 "EPS (trailing)",
    "forwardEps":                  "EPS (forward)",
}

_PCT_KEYS  = {"revenueGrowth", "earningsGrowth", "profitMargins", "grossMargins",
              "operatingMargins", "returnOnEquity"}
_CASH_KEYS = {"freeCashflow", "totalCash", "totalDebt", "marketCap"}

# Re-analyze at most once per week
_REANALYZE_DAYS = 7


def _fmt_metrics(metrics: dict) -> str:
    lines = []
    for key in _METRIC_KEYS:
        val = metrics.get(key)
        if val is None:
            continue
        label = _LABELS.get(key, key)
        if key in _PCT_KEYS:
            lines.append(f"  {label}: {val:.1%}")
        elif key in _CASH_KEYS:
            lines.append(f"  {label}: ${val / 1e9:.2f}B")
        else:
            lines.append(f"  {label}: {val:.2f}" if isinstance(val, float) else f"  {label}: {val}")
    return "\n".join(lines)


def _parse_response(text: str) -> tuple[str, float, str | None, str | None, str | None, str]:
    """Parse structured LLM response → (signal_type, confidence, gs, gm, gl, rationale)."""

    def _grade(label: str) -> str | None:
        m = re.search(rf"{label}[:\s]+([SABC])", text, re.IGNORECASE)
        return m.group(1).upper() if m and m.group(1).upper() in _VALID_GRADES else None

    sm = re.search(r"SIGNAL[:\s]+(bullish|bearish|watchlist)", text, re.IGNORECASE)
    signal_type = sm.group(1).lower() if sm else "watchlist"

    cm = re.search(r"CONFIDENCE[:\s]+(0\.\d+|1\.0+)", text)
    confidence = float(cm.group(1)) if cm else 0.5

    rm = re.search(r"RATIONALE[:\s]+(.+)", text, re.IGNORECASE | re.DOTALL)
    rationale = rm.group(1).strip()[:500] if rm else text[:500]

    return signal_type, confidence, _grade("SHORT"), _grade("MID"), _grade("LONG"), rationale


def _fetch_metrics(ticker_symbol: str) -> dict:
    """Synchronous — call via asyncio.to_thread."""
    import yfinance as yf
    info = yf.Ticker(ticker_symbol).info or {}
    return {k: info[k] for k in _METRIC_KEYS if info.get(k) is not None}


class FinancialAnalystAgent(BaseAgent):
    name = "financial_analyst"

    async def run(self, ticker: str | None = None) -> None:
        targets = [ticker] if ticker else _settings.watchlist
        analyzed = 0

        for symbol in targets:
            if await self._recently_analyzed(symbol):
                continue

            metrics = await asyncio.to_thread(_fetch_metrics, symbol)
            if len(metrics) < 5:
                await self.log("skip", f"{symbol}: insufficient financial data ({len(metrics)} metrics)")
                continue

            formatted = _fmt_metrics(metrics)
            prompt = (
                f"Ticker: {symbol}\n\nFinancial Metrics:\n{formatted}\n\n"
                "Assess this company's financial health and investment outlook.\n\n"
                "Respond EXACTLY in this format:\n"
                "SIGNAL: <bullish|bearish|watchlist>\n"
                "CONFIDENCE: <0.0-1.0>\n"
                "SHORT: <S|A|B|C>\n"
                "MID: <S|A|B|C>\n"
                "LONG: <S|A|B|C>\n"
                "RATIONALE: <2-3 sentence assessment>\n\n"
                "Grades: S=Strong Buy, A=Buy, B=Hold, C=Sell"
            )

            if _settings.use_local_llm:
                from intelligence.local_client import chat_local
                response = await chat_local(prompt, system=_SYSTEM, max_tokens=200)
            else:
                from intelligence.claude_client import analyze
                response = await analyze(prompt, max_tokens=200)

            signal_type, confidence, gs, gm, gl, rationale = _parse_response(response)

            async with AsyncSessionLocal() as session:
                session.add(Signal(
                    ticker=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    source_agent=self.name,
                    rationale=rationale,
                    grade_short=gs,
                    grade_mid=gm,
                    grade_long=gl,
                    meta={"metrics_count": len(metrics)},
                ))
                await session.commit()

            await self.log(
                "analyze",
                f"{symbol}: {signal_type} (confidence={confidence:.2f}) grades={gs}/{gm}/{gl}",
                meta={"ticker": symbol, "signal_type": signal_type, "confidence": confidence},
            )
            analyzed += 1

        await self.log("run", f"Financial analysis complete — {analyzed} ticker(s) analyzed")

    async def _recently_analyzed(self, ticker: str) -> bool:
        cutoff = datetime.now(UTC) - timedelta(days=_REANALYZE_DAYS)
        async with AsyncSessionLocal() as session:
            row = (await session.execute(
                select(Signal.id)
                .where(
                    Signal.ticker == ticker,
                    Signal.source_agent == self.name,
                    Signal.created_at >= cutoff,
                )
                .limit(1)
            )).first()
        return row is not None
