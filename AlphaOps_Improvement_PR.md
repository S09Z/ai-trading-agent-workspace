# AlphaOps (Murff Alpha) — Comprehensive Improvement PR
> สรุปคำแนะนำจากการวิเคราะห์ 3 โปรเจค: **OpenAlice · Vibe-Trading · ML for Trading (Stefan Jansen)**  
> เรียงตาม Priority · Phase · Impact

---

## สารบัญ

1. [ภาพรวม Improvement Roadmap](#1-ภาพรวม-improvement-roadmap)
2. [PR #1 — Trading-as-Git: Staged Order Approval Pipeline](#pr-1--trading-as-git-staged-order-approval-pipeline)
3. [PR #2 — Guard Pipeline: Pre-execution Safety Checks](#pr-2--guard-pipeline-pre-execution-safety-checks)
4. [PR #3 — Smart Heartbeat: Notify Only When It Matters](#pr-3--smart-heartbeat-notify-only-when-it-matters)
5. [PR #4 — Account Snapshot + Equity Curve Dashboard](#pr-4--account-snapshot--equity-curve-dashboard)
6. [PR #5 — Alpha Zoo: 452 Pre-built Factors เข้า FinancialAnalyst](#pr-5--alpha-zoo-452-pre-built-factors-เข้า-financialanalyst)
7. [PR #6 — Multi-factor Composite Scoring](#pr-6--multi-factor-composite-scoring)
8. [PR #7 — Shadow Account: Behavioral Analysis จาก Trade History](#pr-7--shadow-account-behavioral-analysis-จาก-trade-history)
9. [PR #8 — SMC + Liquidity Zone Detection](#pr-8--smc--liquidity-zone-detection)
10. [PR #9 — YAML-configurable Swarm Presets](#pr-9--yaml-configurable-swarm-presets)
11. [PR #10 — EventLog via Redis Pub/Sub (Zero-poll WebSocket)](#pr-10--eventlog-via-redis-pubsub-zero-poll-websocket)
12. [PR #11 — AST Purity Gate: Lookahead Bias Prevention](#pr-11--ast-purity-gate-lookahead-bias-prevention)
13. [PR #12 — Walk-forward Backtesting (Zipline + pyfolio)](#pr-12--walk-forward-backtesting-zipline--pyfolio)

---

## 1. ภาพรวม Improvement Roadmap

### แหล่งที่มาของแต่ละ PR

| PR | แหล่งที่มา | Phase | Impact |
|----|-----------|-------|--------|
| #1 Trading-as-Git | OpenAlice | Phase 10 | 🔴 สูงมาก |
| #2 Guard Pipeline | OpenAlice | Phase 10 | 🔴 สูงมาก |
| #3 Smart Heartbeat | OpenAlice | Phase 8+ | 🟠 สูง |
| #4 Account Snapshot | OpenAlice | Phase 10 | 🟠 สูง |
| #5 Alpha Zoo | Vibe-Trading | Phase 8+ | 🔴 สูงมาก |
| #6 Composite Scoring | Vibe-Trading + ML4T | Phase 8+ | 🔴 สูงมาก |
| #7 Shadow Account | Vibe-Trading | Phase 8+ | 🟠 สูง |
| #8 SMC Detection | Vibe-Trading | Phase 9 | 🟡 กลาง |
| #9 YAML Swarm | Vibe-Trading | Phase 9 | 🟡 กลาง |
| #10 Redis EventLog | OpenAlice | Refactor | 🟢 เสริม |
| #11 AST Gate | Vibe-Trading | Phase 10 | 🟡 กลาง |
| #12 Walk-forward BT | ML4T (Jansen) | Phase 10 | 🔴 สูงมาก |

### ลำดับที่แนะนำ

```
ทำทันที (Phase 8+, ไม่รอ execution layer):
  PR #5 → PR #6 → PR #7 → PR #3

ทำคู่กับ Phase 10:
  PR #2 → PR #1 → PR #4 → PR #12 → PR #11

Refactor เมื่อ stable:
  PR #8 → PR #9 → PR #10
```

---

## PR #1 — Trading-as-Git: Staged Order Approval Pipeline

**แหล่งที่มา:** OpenAlice  
**Phase:** 10 (Execution layer prerequisite)  
**Impact:** 🔴 สูงมาก — ขาดไม่ได้ก่อน live trading  

### ปัญหาที่แก้

AlphaOps Phase 10 วางแผน Alpaca live execution แต่ยังไม่มี approval checkpoint ถ้าต่อ broker ตรงๆ AI อาจ execute trade โดยไม่มีคนเห็น OpenAlice แก้ด้วย Trading-as-Git workflow: ทุก trade ต้อง `stage → commit → push` โดยมี human approve ก่อน execute จริง

### Tasks

#### DB Model
- [ ] เพิ่ม `StagedOrder` model ใน `memory/database.py`
  - Fields: `ticker`, `side`, `qty`, `reason`, `grade`, `status` (pending/approved/rejected), `commit_hash`, `created_at`
- [ ] สร้าง Alembic migration สำหรับ `staged_orders` table

#### API Endpoints
- [ ] `POST /orders/stage` — agents เขียน staged order เข้า DB, return `order_id`
- [ ] `GET /orders/staged` — list orders ที่ `status = pending`
- [ ] `POST /orders/{id}/approve` — set status approved, generate `commit_hash = sha256(id+ts)[:8]`, ส่งต่อ Alpaca
- [ ] `POST /orders/{id}/reject` — set status rejected พร้อม reason

#### Alpaca Integration
- [ ] สร้าง `brokers/alpaca_broker.py` — wrap alpaca-py SDK, implement `submit_order(order)`
- [ ] เพิ่ม `ALPACA_API_KEY`, `ALPACA_SECRET`, `ALPACA_PAPER=true` ใน `.env.example`

#### Frontend
- [ ] เพิ่ม "Pending Orders" panel บน dashboard
  - แสดง grade, ticker, rationale, composite score
  - ปุ่ม Approve / Reject พร้อม confirmation dialog

#### Tests
- [ ] เขียน `tests/test_staged_orders.py` — test stage, approve, reject flow

### Code Reference

```python
# memory/database.py
class StagedOrder(Base):
    __tablename__ = "staged_orders"
    id = Column(UUID, primary_key=True, default=uuid4)
    ticker = Column(String, nullable=False)
    side = Column(String)           # 'buy' | 'sell'
    qty = Column(Integer)
    reason = Column(Text)
    grade = Column(String)          # S / A / B / C
    status = Column(String, default='pending')
    commit_hash = Column(String)    # sha256(id+ts)[:8]
    created_at = Column(DateTime, default=datetime.utcnow)

# brokers/alpaca_broker.py
def submit_order(order: StagedOrder) -> dict:
    import hashlib, datetime
    hash_input = f"{order.id}{datetime.datetime.utcnow().isoformat()}"
    order.commit_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
    # alpaca_client.submit_order(...)
```

**Total tasks: 9**

---

## PR #2 — Guard Pipeline: Pre-execution Safety Checks

**แหล่งที่มา:** OpenAlice  
**Phase:** 10 (ควรทำก่อน PR #1)  
**Impact:** 🔴 สูงมาก — safety layer ที่ขาดไม่ได้  

### ปัญหาที่แก้

RiskMonitor ของ AlphaOps มี circuit breaker ระดับ spike detection แต่ไม่มี per-order safety checks ถ้า execute จริงอาจเกิด oversized position, double trade, หรือ trade ในขณะ daily loss เกิน threshold OpenAlice ใช้ pluggable Guard pipeline ที่รันก่อนทุก push

### Tasks

#### Base Structure
- [ ] สร้าง `guards/base_guard.py` — `BaseGuard` abstract class พร้อม `check(order, portfolio) -> GuardResult`
- [ ] สร้าง `GuardResult` dataclass — `passed: bool`, `reason: str`, `guard_name: str`

#### Guard Implementations
- [ ] `guards/max_position_guard.py` — reject ถ้า order value > X% ของ portfolio equity (env config)
- [ ] `guards/cooldown_guard.py` — reject ถ้า trade ticker เดิมภายใน N นาที
- [ ] `guards/grade_threshold_guard.py` — reject ถ้า signal grade < B (configurable)
- [ ] `guards/daily_loss_guard.py` — halt trading ถ้า realized loss วันนี้ > threshold

#### Integration
- [ ] เรียก guard pipeline ใน `POST /orders/{id}/approve` ก่อน submit ไป Alpaca
  - ถ้า guard fail → auto-reject พร้อม reason, return 422
- [ ] เพิ่ม guard config ใน `config/settings.py`

#### Tests
- [ ] เขียน `tests/test_guards.py` — test ทุก guard ทั้ง pass และ fail cases

### Code Reference

```python
# guards/base_guard.py
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class GuardResult:
    passed: bool
    reason: str
    guard_name: str

class BaseGuard(ABC):
    @abstractmethod
    def check(self, order, portfolio) -> GuardResult: ...

# guards/max_position_guard.py
class MaxPositionGuard(BaseGuard):
    def __init__(self, max_pct: float = 0.05):  # 5% default
        self.max_pct = max_pct

    def check(self, order, portfolio) -> GuardResult:
        order_value = order.qty * get_current_price(order.ticker)
        limit = portfolio.equity * self.max_pct
        if order_value > limit:
            return GuardResult(False, f"Order ${order_value:.0f} > {self.max_pct*100}% limit ${limit:.0f}", "MaxPositionGuard")
        return GuardResult(True, "OK", "MaxPositionGuard")

# config/settings.py additions
MAX_POSITION_PCT: float = 0.05
TRADE_COOLDOWN_MINUTES: int = 60
MIN_SIGNAL_GRADE: str = "B"
MAX_DAILY_LOSS_PCT: float = 0.02
```

**Total tasks: 9**

---

## PR #3 — Smart Heartbeat: Notify Only When It Matters

**แหล่งที่มา:** OpenAlice  
**Phase:** 8+ (ทำได้ทันทีไม่รอ execution)  
**Impact:** 🟠 สูง — ลด Discord noise ทันที  

### ปัญหาที่แก้

Discord digest ส่งทุก 6h ตายตัว ถ้าไม่มีอะไรน่าสนใจก็ส่ง noise ถ้ามีเหตุการณ์ใหญ่ระหว่าง cycle ก็ไม่แจ้ง OpenAlice ใช้ Heartbeat ที่ review ภาวะตลาดก่อน แล้วแจ้งเตือนเฉพาะเมื่อมีบางอย่างสำคัญ

### Tasks

#### Summarizer
- [ ] เพิ่ม `should_notify(signals, risk_status) -> dict` ใน `intelligence/summarizer.py`
- [ ] เพิ่ม LLM prompt สำหรับตัดสิน notify: `{"notify": true/false, "reason": string, "urgency": "immediate"|"scheduled"}`

#### Immediate Triggers (นอกจาก 6h cron)
- [ ] Celery signal: emit `notify_discord` ทันทีเมื่อ SentimentAnalyst สร้าง grade A signal
- [ ] Celery signal: emit `notify_discord` ทันทีเมื่อ RiskMonitor fire circuit breaker
- [ ] Celery signal: emit `notify_discord` ถ้า portfolio P&L ติดลบเกิน threshold ในวันเดียว
- [ ] เพิ่ม suppression log ใน `AgentLog` — บันทึกทุกครั้งที่ digest ถูก skip พร้อม reason

#### Discord
- [ ] เพิ่ม label ใน Discord embed: `⚡ Immediate Alert` vs `📊 Scheduled Digest`

#### Tests
- [ ] เขียน test `should_notify` — mock LLM response, verify suppress/notify logic

### Code Reference

```python
# intelligence/summarizer.py — เพิ่ม method นี้
def should_notify(self, signals: list, risk_status: dict) -> dict:
    prompt = f"""
Given these market signals: {signals}
And risk status: {risk_status}

Is there anything requiring immediate human attention?
Consider: grade A signals, circuit breakers, unusual volatility.

Reply ONLY JSON: {{"notify": true/false, "reason": "...", "urgency": "immediate|scheduled"}}
"""
    response = self.llm.invoke(prompt)
    return json.loads(response.content)

# scheduler/tasks.py — trigger logic
@app.task
def run_heartbeat():
    signals = db.get_recent_signals(hours=1)
    risk = risk_monitor.get_status()
    decision = summarizer.should_notify(signals, risk)
    
    if decision['notify']:
        label = "⚡ Immediate Alert" if decision['urgency'] == 'immediate' else "📊 Scheduled Digest"
        discord.send_embed(signals, label=label, reason=decision['reason'])
    else:
        db.log_suppression(reason=decision['reason'])
```

**Total tasks: 7**

---

## PR #4 — Account Snapshot + Equity Curve Dashboard

**แหล่งที่มา:** OpenAlice  
**Phase:** 10 (ทำคู่กับ Alpaca integration)  
**Impact:** 🟠 สูง — จำเป็นสำหรับ P&L dashboard  

### ปัญหาที่แก้

AlphaOps มี SignalOutcome tracking แต่ไม่มี portfolio-level time-series snapshot ทำให้ไม่สามารถ plot equity curve หรือ track portfolio growth ได้

### Tasks

#### DB Model
- [ ] เพิ่ม `AccountSnapshot` model ใน `memory/database.py`
  - Fields: `timestamp`, `cash`, `equity`, `positions_json` (JSONB), `trigger` (scheduled/trade)
- [ ] สร้าง Alembic migration + TimescaleDB hypertable (partition by timestamp)

#### Scheduler
- [ ] เพิ่ม Celery Beat task `run_snapshot` ทุก 1h — query Alpaca portfolio → insert snapshot
- [ ] Trigger snapshot อัตโนมัติหลังทุก trade approve

#### API + Frontend
- [ ] `GET /portfolio/equity-curve?days=30` — return timeseries
- [ ] เพิ่ม equity curve chart บน dashboard (recharts `LineChart`) พร้อม date range selector
- [ ] เพิ่ม metric cards: current equity, cash, unrealized P&L, total return %

### Code Reference

```python
# memory/database.py
class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"
    id = Column(UUID, primary_key=True, default=uuid4)
    timestamp = Column(DateTime, nullable=False)
    cash = Column(Float)
    equity = Column(Float)
    positions_json = Column(JSONB)
    trigger = Column(String)  # 'scheduled' | 'trade'

# scheduler/tasks.py
@app.task
def run_snapshot(trigger: str = 'scheduled'):
    portfolio = alpaca_client.get_portfolio()
    snapshot = AccountSnapshot(
        timestamp=datetime.utcnow(),
        cash=portfolio.cash,
        equity=portfolio.equity,
        positions_json=portfolio.positions,
        trigger=trigger
    )
    db.save(snapshot)
```

**Total tasks: 7**

---

## PR #5 — Alpha Zoo: 452 Pre-built Factors เข้า FinancialAnalyst

**แหล่งที่มา:** Vibe-Trading + ML for Trading (Jansen Ch.4)  
**Phase:** 8+ (ทำได้ทันที — ไม่รอ execution)  
**Impact:** 🔴 สูงมาก — signal quality upgrade ที่ใหญ่ที่สุด  

### ปัญหาที่แก้

FinancialAnalyst ใช้แค่ 17 static metrics จาก yfinance Vibe-Trading มี Alpha Zoo 452 factors จาก 4 แหล่ง (Qlib 158 + Kakushadze 101 + GTJA 191 + FF5/Carhart) พร้อม IC + IR scoring และ alive/reversed/dead categorisation สามารถใช้แทน static metrics เพื่อให้ signal มีคณิตศาสตร์รองรับ

### Factor Categories ที่ใช้ได้ทันที

| Category | Factors | Source |
|----------|---------|--------|
| Momentum | Price momentum (1m, 3m, 6m, 12m), Volume-weighted momentum | Qlib / GTJA191 |
| Value | P/E, P/B, P/S, EV/EBITDA z-score vs universe | Kakushadze101 |
| Quality | ROE, ROA, Gross margin, Asset turnover, Accruals | FF5 + Carhart |
| Liquidity | Amihud illiquidity, turnover ratio, bid-ask spread proxy | GTJA191 |
| Volatility | Realized vol (20d, 60d), Idiosyncratic vol | Qlib |

### Tasks

- [ ] เพิ่ม `qlib` เป็น optional dependency ใน `pyproject.toml`
- [ ] สร้าง `agents/factor_library.py` — wrapper ดึง alpha factors ตาม ticker universe (35 tickers)
- [ ] คำนวณ IC (Spearman rank correlation กับ 5-day forward return) ทุก factor
- [ ] คำนวณ IR = `IC.mean() / IC.std()` และ classify: alive (IR > 0.3) / reversed (IR < -0.3) / dead
- [ ] สร้าง Celery Beat task `weekly_factor_scoring` ทุกจันทร์เช้า
- [ ] บันทึก `FactorScore` model ใน PostgreSQL
- [ ] ส่ง top-20 alive factors เข้า FinancialAnalyst prompt แทน 17 static metrics
- [ ] แสดง factor leaderboard บน dashboard — sort by IR, color-code status

### Code Reference

```python
# agents/factor_library.py
import pandas as pd
from scipy.stats import spearmanr

ALPHA_BUCKETS = {
    'momentum': ['ret_1m', 'ret_3m', 'ret_6m', 'ret_12m', 'vol_momentum'],
    'value':    ['pe_ratio_z', 'pb_ratio_z', 'ps_ratio_z', 'ev_ebitda_z'],
    'quality':  ['roe', 'roa', 'gross_margin', 'asset_turnover', 'accruals'],
    'liquidity':['amihud_illiq', 'turnover_ratio'],
    'volatility':['realized_vol_20d', 'idio_vol_60d'],
}

def compute_ic(factor_series: pd.Series, forward_return: pd.Series) -> float:
    corr, _ = spearmanr(factor_series.dropna(), forward_return.dropna())
    return corr

def classify_factor(ic_series: pd.Series) -> str:
    ir = ic_series.mean() / ic_series.std() if ic_series.std() > 0 else 0
    if abs(ir) < 0.3: return 'dead'
    return 'alive' if ir > 0 else 'reversed'

# Celery Beat — ทุกจันทร์ 06:00
@app.task
def weekly_factor_scoring():
    prices = fetch_universe_prices(tickers=WATCHLIST, lookback=252)
    fwd_return = prices.pct_change(5).shift(-5)  # 5-day forward return

    for bucket, factors in ALPHA_BUCKETS.items():
        for factor_name in factors:
            factor_vals = compute_factor(factor_name, prices)
            ic = compute_ic(factor_vals, fwd_return)
            db.upsert(FactorScore(
                name=factor_name, bucket=bucket,
                ic=ic, status=classify_factor(pd.Series([ic])),
                computed_at=datetime.utcnow()
            ))
```

**Total tasks: 8**

---

## PR #6 — Multi-factor Composite Scoring

**แหล่งที่มา:** Vibe-Trading + ML for Trading (Jansen Ch.8-12)  
**Phase:** 8+ (ต่อจาก PR #5)  
**Impact:** 🔴 สูงมาก — ทำให้ S/A/B/C grade มีความหมายจริง  

### ปัญหาที่แก้

Signal grade S/A/B/C ของ AlphaOps ขึ้นกับ LLM judgment ล้วนๆ ไม่มีคณิตศาสตร์รองรับ Vibe-Trading + Jansen ML4T ใช้ multi-factor composite score ที่ weight ตาม IC/IR ของแต่ละ factor ทำให้ grade มี quantitative basis และ reproducible

### Tasks

- [ ] สร้าง `intelligence/composite_scorer.py` — รวม 4 buckets: momentum, value, quality, sentiment
- [ ] Weight แต่ละ bucket ตาม IR จาก PR #5 (dynamic weighting — high IR → higher weight)
- [ ] Map composite score (0-100) → grade: top 20% = S, 20-40% = A, 40-60% = B, bottom = C/D
- [ ] แสดง score breakdown บน Staged Order card — human เห็น "composite 78: momentum 85, value 70, quality 80, sentiment 72"
- [ ] เพิ่ม grade ที่มี composite score ใน `Signal` model และ Discord notification

### Code Reference

```python
# intelligence/composite_scorer.py
class CompositeScorer:
    def __init__(self, factor_scores: list[FactorScore]):
        # Dynamic weights จาก IR ที่คำนวณได้
        self.weights = self._compute_weights(factor_scores)

    def _compute_weights(self, factor_scores) -> dict:
        ir_by_bucket = {}
        for fs in factor_scores:
            if fs.status == 'alive':
                ir_by_bucket.setdefault(fs.bucket, []).append(abs(fs.ir))
        total = sum(np.mean(v) for v in ir_by_bucket.values())
        return {k: np.mean(v)/total for k, v in ir_by_bucket.items()}

    def score(self, ticker: str, llm_sentiment: float) -> dict:
        components = {
            'momentum': self._momentum_score(ticker),   # 0-100
            'value':    self._value_score(ticker),
            'quality':  self._quality_score(ticker),
            'sentiment': llm_sentiment * 100,
        }
        composite = sum(components[k] * self.weights.get(k, 0.25) for k in components)
        grade = 'S' if composite >= 80 else 'A' if composite >= 60 else 'B' if composite >= 40 else 'C'
        return {'composite': composite, 'components': components, 'grade': grade}
```

**Total tasks: 5**

---

## PR #7 — Shadow Account: Behavioral Analysis จาก Trade History

**แหล่งที่มา:** Vibe-Trading  
**Phase:** 8+ (ทำได้ทันที — ใช้ SignalOutcome ที่มีอยู่แล้ว)  
**Impact:** 🟠 สูง — insight ที่ human traders ต้องการมากที่สุด  

### ปัญหาที่แก้

AlphaOps track SignalOutcome แต่ไม่เคย analyze ว่า human มี trading behavior pattern อะไร Vibe-Trading มี Shadow Account ที่ upload broker export แล้วให้ AI สรุป behavioral biases และ compare กับ rule-based recommendations

### Tasks

- [ ] สร้าง `POST /portfolio/upload-trades` — รับ CSV จาก Alpaca หรือ broker export
- [ ] สร้าง `agents/shadow_account.py` — LLM วิเคราะห์ trade history
- [ ] Compare human behavior กับ signal grades ที่ระบบแนะนำ — หา divergence
- [ ] สร้าง Shadow Report: behavioral biases, best patterns, worst decisions พร้อม P&L breakdown
- [ ] แสดงบน dashboard — "Your trading style vs. AlphaOps recommendations"

### Code Reference

```python
# agents/shadow_account.py
class ShadowAccountAgent:
    def analyze(self, trade_history: list, signal_outcomes: list) -> dict:
        prompt = f"""
Analyze these trades: {json.dumps(trade_history)}
Against these system recommendations: {json.dumps(signal_outcomes)}

Identify:
1. Dominant trading style (momentum/mean-reversion/breakout/value)
2. Top 3 behavioral biases (FOMO, loss aversion, sector concentration, overtrading)
3. Grade acceptance rate: which grades (S/A/B/C) does the human approve vs. reject?
4. Optimal holding period based on actual vs. expected returns
5. Divergence: when does human deviate from system and was it profitable?

Return JSON: {{
    "style": "...",
    "biases": [...],
    "grade_acceptance": {{"S": 0.9, "A": 0.7, "B": 0.4, "C": 0.1}},
    "optimal_hold_days": N,
    "best_pattern": "...",
    "worst_pattern": "...",
    "divergence_alpha": 0.02  // extra return when deviating from system
}}
"""
        return json.loads(self.llm.invoke(prompt).content)
```

**Total tasks: 5**

---

## PR #8 — SMC + Liquidity Zone Detection

**แหล่งที่มา:** Vibe-Trading  
**Phase:** 9  
**Impact:** 🟡 กลาง — เพิ่ม institutional flow context ให้ signals  

### ปัญหาที่แก้

MarketWatch ของ AlphaOps detect ≥3% spike เท่านั้น Vibe-Trading ใช้ SMC (Smart Money Concepts) ที่ detect Order Blocks, Fair Value Gaps (FVG) และ Liquidity Sweeps — บอกว่า institutional money กำลังทำอะไรอยู่ เหมาะมากกับ small-cap US equities ที่ AlphaOps focus

### Tasks

- [ ] สร้าง `skills/smc_detector.py` — detect Order Block, FVG, Liquidity Sweep, ChoCH
- [ ] เพิ่ม SMC output เป็น context ใน MarketWatch agent prompt
- [ ] ใช้ Liquidity Sweep เป็น signal confidence booster (spike ≥3% + sweep = higher grade)
- [ ] แสดง SMC zones บน dashboard candlestick chart

### Code Reference

```python
# skills/smc_detector.py
def detect_order_block(df: pd.DataFrame) -> list[dict]:
    """Last bearish candle before ≥3-candle bullish impulse"""
    obs = []
    for i in range(2, len(df) - 3):
        if (df['close'][i] < df['open'][i] and           # bearish candle
            all(df['close'][i+j] > df['open'][i+j]       # followed by 3 bullish
                for j in range(1, 4))):
            obs.append({'price': df['low'][i], 'type': 'bullish_ob', 'bar': i})
    return obs

def detect_fvg(df: pd.DataFrame) -> list[dict]:
    """Fair Value Gap: gap between candle[i].high and candle[i+2].low"""
    return [
        {'top': df['high'][i], 'bottom': df['low'][i+2], 'bar': i}
        for i in range(len(df) - 2)
        if df['low'][i+2] > df['high'][i]
    ]

def detect_liquidity_sweep(df: pd.DataFrame, lookback: int = 20) -> list[dict]:
    """Price ทะลุ swing high/low แล้วกลับภายใน candle เดียว"""
    sweeps = []
    for i in range(lookback, len(df)):
        swing_high = df['high'][i-lookback:i].max()
        if df['high'][i] > swing_high and df['close'][i] < swing_high:
            sweeps.append({'type': 'bearish_sweep', 'level': swing_high, 'bar': i})
    return sweeps
```

**Total tasks: 4**

---

## PR #9 — YAML-configurable Swarm Presets

**แหล่งที่มา:** Vibe-Trading  
**Phase:** 9  
**Impact:** 🟡 กลาง — extensibility สำหรับการ scale  

### ปัญหาที่แก้

AlphaOps hard-code 5 agents ใน Python ถ้าต้องการ agent team ใหม่ต้อง edit code + restart Vibe-Trading ใช้ YAML config ทำให้ define team ใหม่ได้ใน minutes

### Tasks

- [ ] สร้าง `config/swarm_presets/` directory
- [ ] สร้าง `agents/swarm_loader.py` — load YAML → instantiate agents → wire DAG dependencies
- [ ] เพิ่ม `GET /swarm/presets` และ `POST /swarm/run/{preset}` ใน cockpit API
- [ ] เพิ่ม preset selector บน dashboard

### YAML Schema Reference

```yaml
# config/swarm_presets/earnings_desk.yaml
name: Earnings Research Desk
description: "Deep dive ก่อน earnings announcement"
agents:
  - id: fundamental
    type: FinancialAnalyst
    skills: [composite-scoring, earnings-forecast]
    depends_on: []

  - id: sentiment
    type: SentimentAnalyst
    skills: [news-sentiment, sec-filing]
    depends_on: []

  - id: risk
    type: RiskMonitor
    skills: [circuit-breaker, daily-loss-guard]
    depends_on: [fundamental, sentiment]

  - id: strategist
    type: Orchestrator
    depends_on: [risk]
    output: final_signal
```

```yaml
# config/swarm_presets/quant_desk.yaml
name: Quant Strategy Desk
description: "Factor screening + backtest pipeline"
agents:
  - id: factor_screener
    type: FinancialAnalyst
    skills: [alpha-zoo, factor-ic-ir]
    depends_on: []

  - id: backtester
    type: ResearchAnalyst
    skills: [walk-forward-backtest]
    depends_on: [factor_screener]

  - id: risk_auditor
    type: RiskMonitor
    depends_on: [backtester]
    output: approved_strategy
```

**Total tasks: 4**

---

## PR #10 — EventLog via Redis Pub/Sub (Zero-poll WebSocket)

**แหล่งที่มา:** OpenAlice  
**Phase:** Refactor (เมื่อ Phase 10 stable)  
**Impact:** 🟢 เสริม — performance + latency improvement  

### ปัญหาที่แก้

WebSocket ใน cockpit poll DB ทุก 2s ทำให้มี unnecessary load Vibe-Trading ใช้ append-only EventLog ที่ทุก activity ผ่าน ทำให้ใช้ Redis pub/sub แทน poll ได้

### Tasks

- [ ] สร้าง `memory/event_bus.py` — `publish(channel, event_dict)` และ `subscribe(channel)` บน Redis pub/sub
- [ ] แก้ `BaseAgent.log()` — emit event ไป Redis channel `agent_events` พร้อมกับ write DB
- [ ] แก้ WebSocket `/logs/ws` — subscribe Redis แทน poll DB ทุก 2s
- [ ] ทดสอบ latency — ควรลดจาก ~2000ms → <100ms
- [ ] (Optional) Trigger Celery task จาก Redis event แทน cron — event-driven pipeline

### Code Reference

```python
# memory/event_bus.py
import redis, json

r = redis.Redis.from_url(settings.REDIS_URL)

def publish(channel: str, event: dict):
    r.publish(channel, json.dumps(event))

async def subscribe_ws(websocket):
    """FastAPI WebSocket that listens to Redis pub/sub"""
    pubsub = r.pubsub()
    pubsub.subscribe('agent_events')
    for message in pubsub.listen():
        if message['type'] == 'message':
            await websocket.send_text(message['data'])

# agents/base_agent.py — แก้ log method
def log(self, event_type: str, data: dict):
    event = {'type': event_type, 'agent': self.name, 'data': data, 'ts': datetime.utcnow().isoformat()}
    db.save(AgentLog(**event))      # persist
    publish('agent_events', event)  # real-time push
```

**Total tasks: 5**

---

## PR #11 — AST Purity Gate: Lookahead Bias Prevention

**แหล่งที่มา:** Vibe-Trading  
**Phase:** 10 (ก่อนเปิด strategy code generation)  
**Impact:** 🟡 กลาง — critical สำหรับ backtest integrity  

### ปัญหาที่แก้

เมื่อ AlphaOps เพิ่ม LLM-generated strategy code ต้องมี safety layer ป้องกัน lookahead bias Vibe-Trading ใช้ AST purity gate + 300-row lookahead sentinel test ที่ validate ก่อน backtest

### Tasks

- [ ] สร้าง `intelligence/ast_validator.py` — parse Python AST, flag future-indexed data access
- [ ] เพิ่ม lookahead sentinel test — synthetic data ที่ future return เป็น random noise, assert strategy ไม่ชนะอย่างมีนัยสำคัญ
- [ ] Block strategy ที่ไม่ผ่าน gate จาก backtest endpoint

### Code Reference

```python
# intelligence/ast_validator.py
import ast

class LookaheadDetector(ast.NodeVisitor):
    def __init__(self):
        self.issues = []

    def visit_Call(self, node):
        # detect shift(-n) — negative shift = lookahead
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'shift':
            if node.args and isinstance(node.args[0], ast.UnaryOp):
                if isinstance(node.args[0].op, ast.USub):
                    self.issues.append(f"Lookahead: shift(-n) at line {node.lineno}")
        self.generic_visit(node)

def validate_strategy(code: str) -> tuple[bool, list[str]]:
    try:
        tree = ast.parse(code)
        detector = LookaheadDetector()
        detector.visit(tree)
        return len(detector.issues) == 0, detector.issues
    except SyntaxError as e:
        return False, [f"Syntax error: {e}"]

def lookahead_sentinel_test(strategy_fn, n_rows: int = 300) -> bool:
    """ถ้า strategy ชนะบน random future data = มี lookahead"""
    import numpy as np
    random_prices = pd.DataFrame({'close': np.random.randn(n_rows).cumsum() + 100})
    result = strategy_fn(random_prices)
    return abs(result['sharpe']) < 1.5  # ถ้า Sharpe สูงมาก = lookahead
```

**Total tasks: 3**

---

## PR #12 — Walk-forward Backtesting (Zipline + pyfolio)

**แหล่งที่มา:** ML for Trading — Stefan Jansen (Ch. 5, 8)  
**Phase:** 10 (ก่อน live execution)  
**Impact:** 🔴 สูงมาก — ขาดไม่ได้ก่อน deploy real money  

### ปัญหาที่แก้

AlphaOps ยังไม่มี systematic backtesting เลย Jansen เน้นว่า ML algorithms ที่ train บน distorted historical data จะล้มเหลวใน live trading เสมอ Walk-forward validation (train on past, test on future, roll forward) เป็นมาตรฐานที่ขาดไม่ได้ก่อน Phase 10

### Walk-forward Schema

```
|--Train (252d)--|--Test (63d)--|
               |--Train (252d)--|--Test (63d)--|
                              |--Train (252d)--|--Test (63d)--|
```

### Tasks

- [ ] สร้าง `backtesting/walk_forward.py` — rolling window train/test split (252d train / 63d test)
- [ ] Integrate pyfolio สำหรับ risk-adjusted performance metrics: Sharpe, Sortino, Max Drawdown, Calmar
- [ ] เพิ่ม `POST /backtest/run` — รับ strategy + ticker + date range, return performance report
- [ ] บันทึก backtest results ลง PostgreSQL + ส่งรายงานผ่าน Discord
- [ ] เพิ่ม backtest results panel บน dashboard พร้อม equity curve ของ strategy

### Code Reference

```python
# backtesting/walk_forward.py
import pandas as pd
import numpy as np

class WalkForwardBacktester:
    def __init__(self, train_days: int = 252, test_days: int = 63):
        self.train_days = train_days
        self.test_days = test_days

    def run(self, strategy_fn, prices: pd.DataFrame) -> dict:
        results = []
        total = len(prices)
        start = self.train_days

        while start + self.test_days <= total:
            train = prices.iloc[start - self.train_days:start]
            test  = prices.iloc[start:start + self.test_days]

            # Train strategy on historical data
            params = strategy_fn.fit(train)

            # Test on out-of-sample data
            signals = strategy_fn.predict(test, params)
            returns = (signals.shift(1) * test['close'].pct_change()).dropna()

            results.append({
                'period_start': test.index[0],
                'period_end': test.index[-1],
                'sharpe': self._sharpe(returns),
                'max_drawdown': self._max_drawdown(returns),
                'total_return': returns.sum(),
                'win_rate': (returns > 0).mean(),
            })
            start += self.test_days

        return {
            'summary': pd.DataFrame(results).describe().to_dict(),
            'periods': results,
            'avg_sharpe': np.mean([r['sharpe'] for r in results]),
            'avg_drawdown': np.mean([r['max_drawdown'] for r in results]),
        }

    def _sharpe(self, returns: pd.Series, rf: float = 0.05) -> float:
        excess = returns - rf/252
        return excess.mean() / excess.std() * np.sqrt(252) if excess.std() > 0 else 0

    def _max_drawdown(self, returns: pd.Series) -> float:
        cum = (1 + returns).cumprod()
        return ((cum - cum.cummax()) / cum.cummax()).min()
```

**Total tasks: 5**

---

## สรุป Checklist รวม

| PR | Tasks | Priority | Phase |
|----|-------|----------|-------|
| #1 Trading-as-Git | 9 | 🔴 | 10 |
| #2 Guard Pipeline | 9 | 🔴 | 10 |
| #3 Smart Heartbeat | 7 | 🟠 | 8+ |
| #4 Account Snapshot | 7 | 🟠 | 10 |
| #5 Alpha Zoo | 8 | 🔴 | 8+ |
| #6 Composite Scoring | 5 | 🔴 | 8+ |
| #7 Shadow Account | 5 | 🟠 | 8+ |
| #8 SMC Detection | 4 | 🟡 | 9 |
| #9 YAML Swarm | 4 | 🟡 | 9 |
| #10 Redis EventLog | 5 | 🟢 | Refactor |
| #11 AST Gate | 3 | 🟡 | 10 |
| #12 Walk-forward BT | 5 | 🔴 | 10 |
| **รวม** | **71** | | |

---

## แนะนำลำดับการ implement

```
Sprint 1 (Phase 8+ — ทำได้เลยตอนนี้):
  PR #5 Alpha Zoo           → เพิ่ม factor quality
  PR #6 Composite Scoring   → grade มีความหมาย
  PR #7 Shadow Account      → behavioral insights
  PR #3 Smart Heartbeat     → ลด Discord noise

Sprint 2 (Phase 10 — execution layer):
  PR #2 Guard Pipeline      → safety first
  PR #1 Trading-as-Git      → approval workflow
  PR #4 Account Snapshot    → P&L tracking
  PR #12 Walk-forward BT    → validate before live
  PR #11 AST Gate           → strategy code safety

Sprint 3 (Refactor + extend):
  PR #8 SMC Detection       → richer signals
  PR #9 YAML Swarm          → extensibility
  PR #10 Redis EventLog     → performance
```

---

*Document compiled from analysis of: OpenAlice (TraderAlice), Vibe-Trading (HKUDS), Machine Learning for Trading (Stefan Jansen 2nd Ed.)*  
*Generated: June 2026*
