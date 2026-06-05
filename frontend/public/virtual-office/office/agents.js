/* agents.js — the 6 investment-desk agents, their look, the live pipeline sim, and screen art. */
(function () {
  const T = window.THREE;

  // pipeline order: Market Data -> (Technical, Fundamentals, Sentiment) -> Risk -> Portfolio
  const AGENTS = [
    {
      id: 'market', name: 'Market Data', role: 'Live Feeds & Prices', short: 'MKT',
      color: '#2fb4a8', screen: '#0d3b3a',
      desk: [-4.6, -1.2], face: 0.35,
      char: { skin: 0xf2c9a0, hair: 0x2a2330, hairStyle: 'short', shirt: 0x2fb4a8, pants: 0x2a3d4a, accent: 0x14e0c0, accessory: 'headset', chair: 0x3d5560 },
      blurb: 'Streams real-time quotes, order-book depth and volume across the watchlist. The source of truth every other desk pulls from.',
      tasks: ['Polling NYSE/NASDAQ tape', 'Normalizing OHLCV bars', 'Backfilling 1m candles', 'Broadcasting tick deltas'],
      logs: ['AAPL 214.62 ▲0.4%  vol 41.2M', 'NVDA 1182.0 ▲1.1%  vol 33.8M', 'feed latency 38ms — healthy', 'snapshot pushed → 5 subscribers', 'TSLA halted? no · resumed', 'order-book depth synced'],
    },
    {
      id: 'technical', name: 'Technical Analyst', role: 'Indicators & Patterns', short: 'TA',
      color: '#4f8bd6', screen: '#10294a',
      desk: [-1.7, -1.7], face: 0.12,
      char: { skin: 0xe8b58c, hair: 0x4a3a2a, hairStyle: 'side', shirt: 0x4f8bd6, pants: 0x2a3550, accent: 0x9ec7ff, accessory: 'glasses', chair: 0x3c4a66 },
      blurb: 'Reads momentum, trend and chart structure — RSI, MACD, moving-average crosses, support/resistance.',
      tasks: ['Computing RSI(14) + MACD', 'Scanning MA-50/200 cross', 'Tagging support/resistance', 'Scoring momentum regime'],
      logs: ['RSI(14) AAPL 61 — neutral-bull', 'MACD NVDA bullish cross ▲', 'golden cross watch: MSFT', 'breakout: AMD > 168 resist', 'ATR rising — vol expanding', 'signal: LONG bias 3/5'],
    },
    {
      id: 'fundamentals', name: 'Fundamentals', role: 'Valuation & Financials', short: 'FND',
      color: '#5aa860', screen: '#103a1e',
      desk: [1.2, -1.2], face: -0.1,
      char: { skin: 0xf0c098, hair: 0x6a4a2a, hairStyle: 'bun', shirt: 0x5aa860, pants: 0x3a4a2a, accent: 0xbfe6b0, accessory: 'tie', chair: 0x3e5740 },
      blurb: 'Values companies on earnings, growth, margins and balance-sheet health. The patient, long-horizon voice.',
      tasks: ['Parsing 10-Q filings', 'Modeling DCF fair value', 'Checking FCF & margins', 'Comparing sector multiples'],
      logs: ['AAPL P/E 28.4 vs sector 24', 'NVDA rev +122% YoY', 'FCF margin healthy 31%', 'MSFT moat: wide', 'fair-value AAPL ≈ $231', 'rating: ACCUMULATE'],
    },
    {
      id: 'sentiment', name: 'Sentiment', role: 'News & Social Mood', short: 'SNT',
      color: '#d56fa0', screen: '#3a1230',
      desk: [-4.0, 2.4], face: 0.5,
      char: { skin: 0xf2c9a0, hair: 0xc0506f, hairStyle: 'long', shirt: 0xd56fa0, pants: 0x4a2a3a, accent: 0xffb0d0, accessory: 'headphones', chair: 0x5a3c50 },
      blurb: 'Tracks the crowd — headlines, social chatter and analyst tone — distilled into a mood score per ticker.',
      tasks: ['Scoring 2.4k headlines', 'Reading X / Reddit chatter', 'Weighing analyst tone', 'Flagging news spikes'],
      logs: ['NVDA mood +0.62 (bullish)', 'AAPL chatter calm · neutral', '⚠ TSLA negative news spike', 'upgrade: GS → AMD buy', 'fear/greed index: 68 greed', 'social vol +18% on NVDA'],
    },
    {
      id: 'risk', name: 'Risk Manager', role: 'Exposure & Limits', short: 'RSK',
      color: '#e0913f', screen: '#3a2410',
      desk: [-1.2, 2.9], face: 0.0,
      char: { skin: 0xe0a87a, hair: 0x3a2a1a, hairStyle: 'short', shirt: 0xe0913f, pants: 0x4a3520, accent: 0xffd089, accessory: 'hardhat', chair: 0x6a4a33 },
      blurb: 'The guardrail. Sizes positions, enforces drawdown limits and vetoes anything that breaches the risk budget.',
      tasks: ['Computing position sizing', 'Checking portfolio VaR', 'Enforcing 2% per-name cap', 'Stress-testing drawdown'],
      logs: ['portfolio VaR(95%) 1.8% ok', 'NVDA weight 6.1% < cap 8%', 'beta-adj exposure 0.92', '⚠ correlation cluster: semis', 'max position: 420 sh NVDA', 'risk budget: 74% used'],
    },
    {
      id: 'portfolio', name: 'Portfolio Manager', role: 'Allocation & Decisions', short: 'PM',
      color: '#8a6fd0', screen: '#241445',
      desk: [1.8, 2.6], face: -0.3,
      char: { skin: 0xf0c098, hair: 0x2a2330, hairStyle: 'spiky', shirt: 0x8a6fd0, pants: 0x33294a, accent: 0xc4b0ff, accessory: 'glasses', chair: 0x4a3a64 },
      blurb: 'The decider. Weighs every desk’s view against risk limits and commits the final orders for the book.',
      tasks: ['Aggregating desk signals', 'Optimizing allocation', 'Drafting order tickets', 'Rebalancing the book'],
      logs: ['consensus NVDA: STRONG BUY', 'allocating +1.5% to AMD', 'trim AAPL 0.5% → cash', 'order: BUY 420 NVDA @ mkt', 'book net-long 0.71', 'rebalance committed ✓'],
    },
  ];

  // -------- monitor screen art (per role) --------
  function drawScreen(mon, t, state, agent) {
    const ctx = mon.userData.ctx, c = mon.userData.canvas;
    const W = c.width, H = c.height;
    ctx.fillStyle = mon.userData.color; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(255,255,255,0.06)'; ctx.fillRect(0, 0, W, 18);
    ctx.fillStyle = agent.color; ctx.font = 'bold 11px monospace';
    ctx.fillText(agent.short, 6, 13);
    ctx.fillStyle = state === 'thinking' ? '#f2b35e' : (state === 'working' ? '#6fcf9a' : '#888');
    ctx.fillText('● ' + state, W - 70, 13);
    const dim = state === 'idle' ? 0.4 : 1;
    ctx.globalAlpha = dim;
    const id = agent.id;
    if (id === 'market' || id === 'technical') {
      // candlestick + line
      ctx.strokeStyle = agent.color; ctx.lineWidth = 1.5; ctx.beginPath();
      for (let i = 0; i < 40; i++) {
        const y = 90 + Math.sin(i * 0.4 + t * (state === 'working' ? 2 : 0.4)) * 30 + Math.sin(i * 1.3) * 8;
        const x = 8 + i * 6; if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
      for (let i = 0; i < 14; i++) {
        const up = Math.sin(i * 1.1 + t) > 0;
        ctx.fillStyle = up ? '#3fd0a0' : '#e06f8a';
        const bx = 12 + i * 17, bh = 8 + Math.abs(Math.sin(i * 0.9 + t * 0.5)) * 30;
        ctx.fillRect(bx, 135 - bh, 8, bh);
      }
    } else if (id === 'fundamentals') {
      const labels = ['REV', 'EPS', 'FCF', 'ROE', 'P/E'];
      labels.forEach((l, i) => {
        const v = 0.4 + Math.abs(Math.sin(i * 1.3 + t * 0.5)) * 0.55;
        ctx.fillStyle = 'rgba(255,255,255,0.2)'; ctx.fillRect(40, 30 + i * 22, 180, 12);
        ctx.fillStyle = agent.color; ctx.fillRect(40, 30 + i * 22, 180 * v, 12);
        ctx.fillStyle = '#cfe8c8'; ctx.font = '9px monospace'; ctx.fillText(l, 8, 40 + i * 22);
      });
    } else if (id === 'sentiment') {
      // gauge
      ctx.strokeStyle = 'rgba(255,255,255,0.2)'; ctx.lineWidth = 10;
      ctx.beginPath(); ctx.arc(W / 2, 110, 55, Math.PI, 0); ctx.stroke();
      const val = 0.5 + Math.sin(t * 0.8) * 0.4;
      ctx.strokeStyle = agent.color; ctx.beginPath(); ctx.arc(W / 2, 110, 55, Math.PI, Math.PI + Math.PI * val); ctx.stroke();
      ctx.fillStyle = '#ffd0e8'; ctx.font = 'bold 22px monospace'; ctx.textAlign = 'center';
      ctx.fillText((val * 100 | 0) + '%', W / 2, 95); ctx.textAlign = 'left';
      ctx.font = '9px monospace'; ctx.fillText('BEARISH', 20, 130); ctx.fillText('BULLISH', 190, 130);
    } else if (id === 'risk') {
      // radial risk bars
      for (let i = 0; i < 6; i++) {
        const v = 0.3 + Math.abs(Math.sin(i * 0.9 + t * 0.6)) * 0.6;
        ctx.fillStyle = v > 0.8 ? '#e06f6f' : agent.color;
        ctx.fillRect(20 + i * 36, 130 - v * 90, 22, v * 90);
        ctx.fillStyle = '#ffd089'; ctx.font = '8px monospace'; ctx.fillText('R' + (i + 1), 22 + i * 36, 145);
      }
      ctx.strokeStyle = '#e06f6f'; ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.moveTo(10, 50); ctx.lineTo(246, 50); ctx.stroke(); ctx.setLineDash([]);
    } else if (id === 'portfolio') {
      // pie allocation
      const segs = [[0.32, '#4f8bd6'], [0.24, '#5aa860'], [0.18, '#d56fa0'], [0.14, '#e0913f'], [0.12, '#2fb4a8']];
      let a0 = -Math.PI / 2 + t * (state === 'working' ? 0.6 : 0.1);
      segs.forEach(([f, col]) => {
        ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(80, 90);
        ctx.arc(80, 90, 50, a0, a0 + f * Math.PI * 2); ctx.closePath(); ctx.fill(); a0 += f * Math.PI * 2;
      });
      ctx.fillStyle = mon.userData.color; ctx.beginPath(); ctx.arc(80, 90, 22, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#c4b0ff'; ctx.font = '9px monospace';
      ['ORDERS', 'NVDA  +420', 'AMD   +180', 'AAPL  -60'].forEach((l, i) => ctx.fillText(l, 150, 40 + i * 22));
    }
    ctx.globalAlpha = 1;
    mon.userData.tex.needsUpdate = true;
  }

  window.OfficeAgents = { AGENTS, drawScreen };
})();
