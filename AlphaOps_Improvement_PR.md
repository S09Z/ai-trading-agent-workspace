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

---

## Phase 8 — Step-by-Step Implementation Guide

> ลำดับ build: **PR #5 → PR #6 → PR #7 → PR #3**  
> แต่ละ step มี: สิ่งที่เปลี่ยน + Before vs After impact

---

### PR #5 — Alpha Zoo (8 steps)

---

#### Step 1 — Add `scipy` dependency

**File:** `pyproject.toml`  
**Change:** Add `scipy>=1.13` to `dependencies`.

> ไม่ต้องใช้ `qlib` (หนักเกินไป) — `scipy` + `pandas` + `yfinance` ครอบคลุมทุก factor ที่ต้องการ

| Aspect | Before | After |
| --- | --- | --- |
| Factor math | ไม่มี | Spearman rank correlation สำหรับ IC calculation |
| Dependency | ไม่มี scipy | `scipy>=1.13` พร้อมใช้ |

---

#### Step 2 — Create `agents/factor_library.py`

**File:** `agents/factor_library.py` *(ไฟล์ใหม่)*  
**Change:** Module ที่คำนวณ 5 alpha factor buckets (momentum, value, quality, liquidity, volatility) สำหรับแต่ละ ticker จากนั้น score แต่ละ factor ด้วย IC (Information Coefficient) และ IR (Information Ratio) แล้ว classify เป็น `alive / reversed / dead`

| Aspect | Before | After |
| --- | --- | --- |
| FinancialAnalyst data | 17 static yfinance `.info` keys — ไม่มี predictive scoring | IC/IR-scored factors — ส่งเฉพาะ alive factors ต่อ |
| Signal basis | LLM อ่านตัวเลขดิบโดยไม่รู้ว่า metric ไหน predict ได้จริง | LLM เห็น "momentum IC=0.42 (alive), value IC=0.31 (alive)" |
| Factor quality | ไม่ทราบ — ใช้ metrics เดิมทุกครั้งไม่ว่าตลาดจะเป็นแบบไหน | Self-calibrating — dead factors หลุดออกอัตโนมัติ |

```python
# agents/factor_library.py
import asyncio
from datetime import UTC, datetime
import pandas as pd
from scipy.stats import spearmanr
import yfinance as yf

ALPHA_BUCKETS = {
    "momentum":   ["ret_1m", "ret_3m", "ret_6m", "ret_12m"],
    "value":      ["pe_ratio_z", "pb_ratio_z", "ps_ratio_z"],
    "quality":    ["roe", "roa", "gross_margin", "asset_turnover"],
    "liquidity":  ["turnover_ratio"],
    "volatility": ["realized_vol_20d", "realized_vol_60d"],
}

def compute_ic(factor_series: pd.Series, forward_return: pd.Series) -> float:
    corr, _ = spearmanr(factor_series.dropna(), forward_return.dropna())
    return float(corr) if not pd.isna(corr) else 0.0

def classify_factor(ic: float) -> str:
    if abs(ic) < 0.05:
        return "dead"
    return "alive" if ic > 0 else "reversed"

def compute_factor_ic(ticker: str, factor_name: str, prices: pd.DataFrame) -> float:
    fwd_return = prices["close"].pct_change(5).shift(-5)
    if factor_name.startswith("ret_"):
        days = int(factor_name.split("_")[1].replace("m", "")) * 21
        factor = prices["close"].pct_change(days)
    elif factor_name.startswith("realized_vol_"):
        days = int(factor_name.split("_")[2].replace("d", ""))
        factor = prices["close"].pct_change().rolling(days).std()
    else:
        return 0.0
    return compute_ic(factor.dropna(), fwd_return.dropna())

async def score_ticker_factors(ticker: str) -> list[dict]:
    prices = await asyncio.to_thread(
        lambda: yf.download(ticker, period="1y", interval="1d", progress=False)
    )
    if prices.empty or len(prices) < 60:
        return []
    prices.columns = [c.lower() for c in prices.columns]
    results = []
    for bucket, factors in ALPHA_BUCKETS.items():
        for factor_name in factors:
            ic = compute_factor_ic(ticker, factor_name, prices)
            results.append({
                "name": factor_name,
                "bucket": bucket,
                "ic": ic,
                "status": classify_factor(ic),
            })
    return results
```

---

#### Step 3 — Add `FactorScore` model to `memory/database.py`

**File:** `memory/database.py`  
**Change:** เพิ่ม `FactorScore` table + `ALTER TABLE` migration ใน `init_db()`

| Aspect | Before | After |
| --- | --- | --- |
| Factor history | ไม่ถูก persist — คำนวณแล้วทิ้ง | เก็บใน PostgreSQL, query ได้ตลอดเวลา |
| Dashboard data | ไม่มี factor data | Factor leaderboard endpoint พร้อม serve `GET /factors` |
| Trend visibility | ไม่มี | ติดตาม IC drift — เห็นเมื่อ factor เริ่ม degrade |

```python
# เพิ่มใน memory/database.py
class FactorScore(Base):
    __tablename__ = "factor_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(50))          # "ret_3m", "roe", etc.
    bucket: Mapped[str] = mapped_column(String(20))        # momentum | value | quality | liquidity | volatility
    ic: Mapped[float] = mapped_column(Float)               # Spearman IC vs 5d forward return
    status: Mapped[str] = mapped_column(String(10))        # alive | reversed | dead
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

# เพิ่มใน init_db() หลัง grade columns migration:
await conn.execute(text(
    "CREATE TABLE IF NOT EXISTS factor_scores ("
    "id SERIAL PRIMARY KEY, ticker VARCHAR(20), name VARCHAR(50), "
    "bucket VARCHAR(20), ic FLOAT, status VARCHAR(10), computed_at TIMESTAMPTZ"
    ")"
))
```

---

#### Step 4 — Add `weekly_factor_scoring` Celery Beat task

**File:** `scheduler/tasks.py`  
**Change:** เพิ่ม task `run_factor_scoring` + เพิ่มเข้า `beat_schedule` ทุกวันจันทร์ 06:00 UTC

| Aspect | Before | After |
| --- | --- | --- |
| Factor scoring | Manual / ไม่เคยทำ | รันทุกจันทร์, auto-update `factor_scores` table |
| FinancialAnalyst freshness | 17 metrics เดิมตลอด | Factor set refresh ทุกสัปดาห์ |
| Operational cost | N/A | ~1 yfinance call per ticker per week — negligible |

```python
# เพิ่มใน scheduler/tasks.py
@celery_app.task(name="scheduler.tasks.run_factor_scoring")
def run_factor_scoring() -> None:
    from agents.factor_library import score_ticker_factors
    from memory.database import AsyncSessionLocal, FactorScore

    async def _run() -> None:
        settings = get_settings()
        async with AsyncSessionLocal() as session:
            for ticker in settings.watchlist:
                scores = await score_ticker_factors(ticker)
                for s in scores:
                    session.add(FactorScore(ticker=ticker, **s))
        await session.commit()

    asyncio.run(_run())

# เพิ่มใน beat_schedule:
"factor-scoring": {
    "task": "scheduler.tasks.run_factor_scoring",
    "schedule": crontab(hour=6, minute=0, day_of_week=1),  # Monday 06:00 UTC
},
```

---

#### Step 5 — Inject alive factors into `FinancialAnalystAgent` prompt

**File:** `agents/financial_analyst.py`  
**Change:** ก่อน build prompt, query `FactorScore` สำหรับ alive factors ของ ticker นั้น แล้ว append เข้า prompt section ถ้าไม่มี factor scores เลย (first run) ให้ fallback ไปใช้ 17-metric block เดิม

| Aspect | Before | After |
| --- | --- | --- |
| Prompt content | "Revenue Growth: 18%, P/E: 32.1…" — static numbers | + "Alive factors (IC): ret_3m IC=0.38, roe IC=0.31…" |
| LLM reasoning | LLM เดาเองว่า metric ไหนสำคัญ | LLM รู้ว่า metric ไหน historically predict returns ได้ |
| Signal quality | Baseline | คาดว่า directional accuracy สูงขึ้นตาม IC-weighted context |

```python
# เพิ่มใน financial_analyst.py — helper function
async def _fetch_alive_factors(ticker: str) -> str:
    from memory.database import AsyncSessionLocal, FactorScore
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(FactorScore)
            .where(FactorScore.ticker == ticker, FactorScore.status == "alive")
            .order_by(FactorScore.ic.desc())
            .limit(10)
        )).scalars().all()
    if not rows:
        return ""
    lines = [f"  {r.name} [{r.bucket}] IC={r.ic:.3f}" for r in rows]
    return "Alive Alpha Factors (IC vs 5d forward return):\n" + "\n".join(lines)

# แก้ใน FinancialAnalystAgent.run() — เพิ่มหลัง _fmt_metrics():
factor_section = await _fetch_alive_factors(symbol)
prompt = (
    f"Ticker: {symbol}\n\nFinancial Metrics:\n{formatted}\n\n"
    + (f"{factor_section}\n\n" if factor_section else "")
    + "Assess this company's financial health and investment outlook.\n\n"
    + "Respond EXACTLY in this format:\n"
    + "SIGNAL: <bullish|bearish|watchlist>\n"
    + "CONFIDENCE: <0.0-1.0>\n"
    + "SHORT: <S|A|B|C>\n"
    + "MID: <S|A|B|C>\n"
    + "LONG: <S|A|B|C>\n"
    + "RATIONALE: <2-3 sentence assessment>\n\n"
    + "Grades: S=Strong Buy, A=Buy, B=Hold, C=Sell"
)
```

---

### PR #6 — Multi-factor Composite Scoring (5 steps)

---

#### Step 6 — Create `intelligence/composite_scorer.py`

**File:** `intelligence/composite_scorer.py` *(ไฟล์ใหม่)*  
**Change:** `CompositeScorer` class โหลด alive `FactorScore` records, weight 4 buckets ตาม mean IC, คำนวณ composite score 0–100 ต่อ ticker, map เป็น S/A/B/C

| Aspect | Before | After |
| --- | --- | --- |
| Grade source | LLM judgment ล้วนๆ — "feels like an A" | `composite = Σ(bucket_score × IC_weight)` — math-backed |
| Grade consistency | Ticker เดียวกันอาจได้ A วันนี้, B พรุ่งนี้ ด้วย data เดิม | Deterministic: input เดิม → grade เดิมเสมอ |
| Grade meaning | Relative opinion | Top 20% universe = S, 20–40% = A, 40–60% = B, rest = C |
| Transparency | Black box | Breakdown: "composite 78: momentum 85, value 70, quality 80" |

```python
# intelligence/composite_scorer.py
from __future__ import annotations
import numpy as np

class CompositeScorer:
    def __init__(self, factor_scores: list):
        self.weights = self._compute_weights(factor_scores)

    def _compute_weights(self, factor_scores) -> dict[str, float]:
        ic_by_bucket: dict[str, list[float]] = {}
        for fs in factor_scores:
            if fs.status == "alive":
                ic_by_bucket.setdefault(fs.bucket, []).append(abs(fs.ic))
        if not ic_by_bucket:
            return {"momentum": 0.25, "value": 0.25, "quality": 0.25, "sentiment": 0.25}
        total = sum(np.mean(v) for v in ic_by_bucket.values())
        weights = {k: np.mean(v) / total for k, v in ic_by_bucket.items()}
        weights.setdefault("sentiment", 0.1)  # always include sentiment
        return weights

    def score(self, bucket_scores: dict[str, float]) -> dict:
        """bucket_scores: {"momentum": 0-100, "value": 0-100, "quality": 0-100, "sentiment": 0-100}"""
        composite = sum(
            bucket_scores.get(k, 50) * self.weights.get(k, 0.25)
            for k in ["momentum", "value", "quality", "sentiment"]
        )
        grade = "S" if composite >= 80 else "A" if composite >= 60 else "B" if composite >= 40 else "C"
        return {
            "composite": round(composite, 1),
            "components": bucket_scores,
            "grade": grade,
        }

async def build_composite_scorer(ticker: str) -> CompositeScorer:
    from memory.database import AsyncSessionLocal, FactorScore
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(FactorScore).where(FactorScore.ticker == ticker)
        )).scalars().all()
    return CompositeScorer(rows)
```

---

#### Step 7 — Add `composite_score` + `composite_breakdown` to `Signal` model

**File:** `memory/database.py`  
**Change:** เพิ่ม 2 columns ใน `Signal` + `ALTER TABLE IF NOT EXISTS` ใน `init_db()`

| Aspect | Before | After |
| --- | --- | --- |
| Signal record | grade_short/mid/long เท่านั้น | + composite_score (0–100) + composite_breakdown JSON |
| API payload | ไม่มี composite data | `GET /signals` return composite score ให้ frontend แสดง |
| Outcome correlation | ไม่สามารถ correlate score กับ outcome | `SignalOutcome` join ดูได้ว่า composite สูง → outcome ดีกว่าไหม |

```python
# เพิ่มใน Signal model:
composite_score: Mapped[float | None] = mapped_column(Float)
composite_breakdown: Mapped[dict | None] = mapped_column(JSON)

# เพิ่มใน init_db() migrations:
for col, typ in [("composite_score", "FLOAT"), ("composite_breakdown", "JSONB")]:
    await conn.execute(text(
        f"ALTER TABLE signals ADD COLUMN IF NOT EXISTS {col} {typ}"
    ))
```

---

#### Step 8 — Wire `CompositeScorer` into `FinancialAnalystAgent`

**File:** `agents/financial_analyst.py`  
**Change:** หลัง LLM response, สร้าง `CompositeScorer`, คำนวณ bucket scores จาก metrics, เรียก `.score()`, บันทึก `composite_score` และ `composite_breakdown` ใน `Signal` record

| Aspect | Before | After |
| --- | --- | --- |
| Grade assignment | LLM output → grade (ไม่มี cross-check) | LLM grade + composite grade → final grade (composite wins ถ้า conflict) |
| Signal record | `{signal_type, confidence, grade_short/mid/long, rationale}` | + `{composite_score: 78, composite_breakdown: {...}}` |

```python
# เพิ่มใน FinancialAnalystAgent.run() — หลัง _parse_response():
from intelligence.composite_scorer import build_composite_scorer

scorer = await build_composite_scorer(symbol)
roe = metrics.get("returnOnEquity", 0) or 0
pe = metrics.get("trailingPE", 30) or 30
rev_growth = metrics.get("revenueGrowth", 0) or 0
sentiment_val = 70.0 if signal_type == "bullish" else 30.0 if signal_type == "bearish" else 50.0

bucket_scores = {
    "momentum": min(100, max(0, 50 + rev_growth * 100)),
    "value":    min(100, max(0, 100 - pe)),
    "quality":  min(100, max(0, roe * 100)),
    "sentiment": sentiment_val,
}
composite = scorer.score(bucket_scores)

# บันทึกลง Signal:
session.add(Signal(
    ticker=symbol,
    signal_type=signal_type,
    confidence=confidence,
    source_agent=self.name,
    rationale=rationale,
    grade_short=composite["grade"],   # composite grade overrides LLM grade
    grade_mid=gm,
    grade_long=gl,
    composite_score=composite["composite"],
    composite_breakdown=composite["components"],
    meta={"metrics_count": len(metrics)},
))
```

---

#### Step 9 — Add composite score to Discord digest

**File:** `intelligence/discord_notifier.py`  
**Change:** ใน signal embed block เพิ่ม line: `Composite: 78 · momentum↑ · value↑ · quality↑`

| Aspect | Before | After |
| --- | --- | --- |
| Discord signal card | "AAPL — BULLISH — A/A/B — confidence 0.82" | + "Composite: 78 · momentum 85 · value 70 · quality 80" |
| Human readability | Grade ไม่มีคำอธิบาย | Grade มี quantitative backing ให้เห็นทันที |

```python
# แก้ใน discord_notifier.py — signal embed field:
composite_score = sig.get("composite_score")
breakdown = sig.get("composite_breakdown") or {}
if composite_score is not None:
    parts = " · ".join(f"{k} {v:.0f}" for k, v in breakdown.items())
    embed_fields.append({"name": "Composite", "value": f"{composite_score:.0f} ({parts})", "inline": False})
```

---

#### Step 10 — Write tests for PR #5 + PR #6

**File:** `tests/test_factor_library.py`, `tests/test_composite_scorer.py` *(ไฟล์ใหม่)*

| Aspect | Before | After |
| --- | --- | --- |
| Test coverage | FinancialAnalyst tested | + factor IC/IR logic + CompositeScorer grade mapping |
| Regression safety | ไม่มี | Grade mapping และ weight calculation ถูก pin ไว้ |

```python
# tests/test_factor_library.py
def test_classify_factor():
    from agents.factor_library import classify_factor
    assert classify_factor(0.40) == "alive"
    assert classify_factor(-0.40) == "reversed"
    assert classify_factor(0.02) == "dead"

def test_compute_ic_perfect():
    from agents.factor_library import compute_ic
    import pandas as pd
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert compute_ic(s, s) == pytest.approx(1.0)

# tests/test_composite_scorer.py
def test_grade_mapping():
    from intelligence.composite_scorer import CompositeScorer
    scorer = CompositeScorer([])  # no factor scores → equal weights
    assert scorer.score({"momentum":90,"value":90,"quality":90,"sentiment":90})["grade"] == "S"
    assert scorer.score({"momentum":30,"value":30,"quality":30,"sentiment":30})["grade"] == "C"
```

---

### PR #7 — Shadow Account (5 steps)

---

#### Step 11 — Add `POST /portfolio/upload-trades` endpoint

**File:** `cockpit/routers/portfolio.py` *(ไฟล์ใหม่)*, register ใน `cockpit/app.py`  
**Change:** รับ CSV upload (Alpaca broker export format), parse rows เป็น list of trade dicts

| Aspect | Before | After |
| --- | --- | --- |
| Human trade data | ไม่ถูก ingest — ไม่มี visibility ว่า human ทำอะไร | CSV upload → เปรียบเทียบกับ system signals ได้ |
| Behavioral loop | System fire signals ออกไปแล้วไม่รู้ผล | System เห็นได้ว่า human approve/reject/ignore signal ไหน |

```python
# cockpit/routers/portfolio.py
from fastapi import APIRouter, UploadFile, File
import csv, io

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.post("/upload-trades")
async def upload_trades(file: UploadFile = File(...)):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode()))
    trades = [row for row in reader]
    return {"trades_parsed": len(trades), "trades": trades}
```

---

#### Step 12 — Create `agents/shadow_account.py`

**File:** `agents/shadow_account.py` *(ไฟล์ใหม่)*  
**Change:** `ShadowAccountAgent` รับ `trade_history` (CSV rows) + `signal_outcomes` (จาก `SignalOutcome` table) แล้วให้ LLM identify: trading style, top 3 biases, grade acceptance rate, optimal hold period, divergence alpha

| Aspect | Before | After |
| --- | --- | --- |
| Self-awareness | System track signal accuracy แต่ไม่รู้ human behavior | System รู้: "Human approve 90% S grades, 40% B grades" |
| Bias detection | ไม่มี | "Loss aversion — human ถือ loser นาน 3× กว่า winner" |
| Divergence tracking | ไม่มี | "เมื่อ human deviate จาก system: +2% extra return เฉลี่ย" |

```python
# agents/shadow_account.py
import json
from agents.base import BaseAgent
from intelligence.llm import analyze

class ShadowAccountAgent(BaseAgent):
    name = "shadow_account"

    async def analyze(self, trade_history: list[dict], signal_outcomes: list[dict]) -> dict:
        prompt = f"""
Analyze these human trades: {json.dumps(trade_history[:50])}
Against these system signal outcomes: {json.dumps(signal_outcomes[:50])}

Identify:
1. Dominant trading style (momentum/mean-reversion/breakout/value)
2. Top 3 behavioral biases (FOMO, loss aversion, sector concentration, overtrading)
3. Grade acceptance rate: which grades (S/A/B/C) does the human approve vs. reject?
4. Optimal holding period based on actual vs. expected returns
5. Divergence: when does human deviate from system and was it profitable?

Reply ONLY JSON:
{{
  "style": "...",
  "biases": ["...", "...", "..."],
  "grade_acceptance": {{"S": 0.9, "A": 0.7, "B": 0.4, "C": 0.1}},
  "optimal_hold_days": 5,
  "best_pattern": "...",
  "worst_pattern": "...",
  "divergence_alpha": 0.02
}}
"""
        response = await analyze(prompt, system="You are a behavioral finance analyst.", max_tokens=400)
        try:
            result = json.loads(response)
        except Exception:
            result = {"error": "parse_failed", "raw": response}
        await self.log("analyze", f"Shadow report generated — style: {result.get('style', 'unknown')}")
        return result
```

---

#### Step 13 — Add `POST /portfolio/shadow-report` endpoint + connect to frontend

**File:** `cockpit/routers/portfolio.py`, `frontend/app/page.tsx`  
**Change:** เพิ่ม endpoint ที่รับ `trade_history` JSON แล้วเรียก `ShadowAccountAgent.analyze()` return Shadow Report. เพิ่ม panel "Your Trading Style" ใน dashboard

| Aspect | Before | After |
| --- | --- | --- |
| Dashboard | Signal cards + agent status + activity log | + Shadow Report: style, biases, grade acceptance, divergence |
| Actionable insight | ไม่มีนอกจาก signal confidence | "คุณมักจะ override B signals — historically -1.5% avg return" |

```python
# เพิ่มใน cockpit/routers/portfolio.py
@router.post("/shadow-report")
async def shadow_report(trades: list[dict], session: AsyncSession = Depends(get_session)):
    from agents.shadow_account import ShadowAccountAgent
    from memory.database import SignalOutcome
    from sqlalchemy import select
    outcomes = (await session.execute(
        select(SignalOutcome).order_by(SignalOutcome.created_at.desc()).limit(100)
    )).scalars().all()
    outcomes_data = [
        {"ticker": o.ticker, "signal_type": o.signal_type, "outcome_5d": o.outcome_5d}
        for o in outcomes
    ]
    report = await ShadowAccountAgent().analyze(trades, outcomes_data)
    return report
```

---

#### Step 14 — Write tests for PR #7

**File:** `tests/test_shadow_account.py` *(ไฟล์ใหม่)*

```python
# tests/test_shadow_account.py
import json
from unittest.mock import AsyncMock, patch

async def test_shadow_account_parse():
    from agents.shadow_account import ShadowAccountAgent
    mock_response = json.dumps({
        "style": "momentum",
        "biases": ["FOMO", "loss_aversion"],
        "grade_acceptance": {"S": 0.9, "A": 0.7, "B": 0.3, "C": 0.1},
        "optimal_hold_days": 5,
        "best_pattern": "early momentum",
        "worst_pattern": "holding losers",
        "divergence_alpha": 0.015,
    })
    with patch("agents.shadow_account.analyze", new_callable=AsyncMock, return_value=mock_response):
        agent = ShadowAccountAgent()
        result = await agent.analyze(
            trade_history=[{"ticker": "AAPL", "side": "buy", "qty": 10}],
            signal_outcomes=[{"ticker": "AAPL", "signal_type": "bullish", "outcome_5d": "correct"}],
        )
    assert result["style"] == "momentum"
    assert result["divergence_alpha"] == pytest.approx(0.015)
```

---

### PR #3 — Smart Heartbeat (4 steps)

---

#### Step 15 — Add `should_notify()` to `intelligence/summarizer.py`

**File:** `intelligence/summarizer.py`  
**Change:** เพิ่ม method `should_notify(signals, risk_status) -> dict` เรียก LLM ด้วย compact prompt return `{"notify": bool, "reason": str, "urgency": "immediate"|"scheduled"}`

| Aspect | Before | After |
| --- | --- | --- |
| Digest trigger | ทุก 6h — fixed cron, ไม่ตรวจ content | Post เฉพาะเมื่อ LLM ตัดสินว่ามีอะไรน่า action |
| Discord frequency | 4× ต่อวันเสมอ | 0–4× ต่อวัน ตามสภาพตลาด |
| Noise level | สูง — digest ว่างๆ บ่อย | ลดลง — AgentLog บันทึก suppress ทุกครั้งพร้อม reason |

```python
# เพิ่มใน intelligence/summarizer.py
import json as _json

async def should_notify(self, signals: list, risk_status: dict) -> dict:
    prompt = f"""
Given these recent market signals: {_json.dumps(signals[:10])}
And risk status: {_json.dumps(risk_status)}

Is there anything requiring immediate human attention?
Consider: grade S or A signals, circuit breakers, unusual volatility.

Reply ONLY JSON: {{"notify": true, "reason": "...", "urgency": "immediate|scheduled"}}
"""
    from intelligence.llm import analyze
    response = await analyze(prompt, system="You are a market monitoring system.", max_tokens=100)
    try:
        return _json.loads(response)
    except Exception:
        return {"notify": True, "reason": "parse error — defaulting to notify", "urgency": "scheduled"}
```

---

#### Step 16 — Add immediate Celery triggers in `scheduler/tasks.py`

**File:** `scheduler/tasks.py`  
**Change:** ใน `run_sentiment_analyst` และ `run_risk_monitor` — หลัง agent run, ตรวจว่ามี grade-A/S signal หรือ circuit breaker ถ้าใช่ call `run_digest.apply_async()` ทันที

| Aspect | Before | After |
| --- | --- | --- |
| Grade A signal → Discord | รอสูงสุด 6h | Post ภายในไม่กี่วินาทีหลัง detect |
| Circuit breaker → Discord | รอสูงสุด 6h | Post ทันที |
| Response model | Fixed-interval เท่านั้น | Event-driven สำหรับ high-urgency |

```python
# แก้ run_sentiment_analyst task:
@celery_app.task(name="scheduler.tasks.run_sentiment_analyst")
def run_sentiment_analyst() -> None:
    from agents.sentiment_analyst import SentimentAnalystAgent
    asyncio.run(SentimentAnalystAgent().run())
    # check for grade A/S signals in last 10 min → immediate digest
    _maybe_trigger_digest(grade_threshold={"S", "A"})

def _maybe_trigger_digest(grade_threshold: set[str]) -> None:
    import asyncio as _asyncio
    from memory.database import AsyncSessionLocal, Signal
    from sqlalchemy import select
    from datetime import datetime, UTC, timedelta

    async def _check() -> bool:
        cutoff = datetime.now(UTC) - timedelta(minutes=10)
        async with AsyncSessionLocal() as session:
            row = (await session.execute(
                select(Signal.id)
                .where(
                    Signal.grade_short.in_(grade_threshold),
                    Signal.created_at >= cutoff,
                )
                .limit(1)
            )).first()
        return row is not None

    if _asyncio.run(_check()):
        run_digest.apply_async()
```

---

#### Step 17 — Add urgency label + suppression log

**Files:** `intelligence/discord_notifier.py`, `scheduler/tasks.py`  
**Change:** Discord embed ได้รับ label field: `⚡ Immediate Alert` หรือ `📊 Scheduled Digest`. Digest ที่ถูก skip เรียก `AgentLog` บันทึก reason

| Aspect | Before | After |
| --- | --- | --- |
| Discord message | Uniform — ไม่มีความแตกต่างด้านความเร่งด่วน | Visual label บอก type ของ alert ทันที |
| Suppression visibility | Silent — ไม่รู้ว่า digest ถูก skip | Cockpit log แสดง: "Digest suppressed — 0 grade-A signals (reason: slow market)" |

```python
# แก้ run_digest task — เพิ่ม should_notify check:
@celery_app.task(name="scheduler.tasks.run_digest")
def run_digest(urgency: str = "scheduled") -> None:
    from intelligence.discord_notifier import send_digest_embed
    from intelligence.summarizer import build_digest

    async def _run() -> None:
        from intelligence.discord_notifier import send_message
        digest, count, signals, risk = await build_digest(hours=6)
        if count == 0:
            await send_message("📭 No articles in the last 6h.")
            return
        label = "⚡ Immediate Alert" if urgency == "immediate" else "📊 Scheduled Digest"
        await send_digest_embed(digest, article_count=count, hours=6, signals=signals, risk=risk, label=label)

    asyncio.run(_run())

# แก้ใน send_digest_embed signature — รับ label parameter:
async def send_digest_embed(..., label: str = "📊 Scheduled Digest") -> None:
    # เพิ่ม label เป็น embed footer หรือ title prefix
```

---

#### Step 18 — Write tests for PR #3

**File:** `tests/test_smart_heartbeat.py` *(ไฟล์ใหม่)*

```python
# tests/test_smart_heartbeat.py
import json
from unittest.mock import AsyncMock, patch

async def test_should_notify_true():
    from intelligence.summarizer import MarketSummarizer
    mock_resp = json.dumps({"notify": True, "reason": "Grade A signal on NVDA", "urgency": "immediate"})
    with patch("intelligence.summarizer.analyze", new_callable=AsyncMock, return_value=mock_resp):
        summarizer = MarketSummarizer()
        result = await summarizer.should_notify(
            signals=[{"ticker": "NVDA", "grade_short": "A"}],
            risk_status={"circuit_breaker": False}
        )
    assert result["notify"] is True
    assert result["urgency"] == "immediate"

async def test_should_notify_suppress():
    from intelligence.summarizer import MarketSummarizer
    mock_resp = json.dumps({"notify": False, "reason": "No significant moves", "urgency": "scheduled"})
    with patch("intelligence.summarizer.analyze", new_callable=AsyncMock, return_value=mock_resp):
        summarizer = MarketSummarizer()
        result = await summarizer.should_notify(signals=[], risk_status={"circuit_breaker": False})
    assert result["notify"] is False
```

---

### Final Step — `make check`

**ก่อน declare Phase 8 done** ต้อง run:

```bash
make check   # lint + full test suite
```

Phase 8 เพิ่ม 3 agents ใหม่, 1 DB model ใหม่, 2 intelligence modules — test suite ต้อง pass clean ก่อน merge

**Expected test count:** 197 (ปัจจุบัน) + ~20 tests ใหม่ = ~217 tests passing

---

### สรุป Before vs After รวม (Phase 8)

| Dimension | Before Phase 8 | After Phase 8 |
| --- | --- | --- |
| Signal basis | 17 static metrics + LLM opinion | IC/IR-scored alive factors + math-backed composite |
| Grade meaning | Subjective A/B/C | Top 20% = S, verified by IC vs forward return |
| Grade consistency | Variable per LLM call | Deterministic composite score |
| Discord frequency | 4× day fixed | Event-driven, suppressed when quiet |
| Human behavior insight | None | Shadow Report: biases, style, divergence alpha |
| Factor freshness | Static forever | Auto-refreshed weekly via Celery Beat |
| Test coverage | 197 tests | ~217 tests |
