/* ui.js — detail panel, live activity feed, market ticker. */
(function () {
  const SYMBOLS = [
    ['AAPL', 214.62, 0.4], ['NVDA', 1182.0, 1.1], ['MSFT', 471.3, 0.2], ['TSLA', 248.9, -0.8],
    ['AMD', 168.4, 1.6], ['GOOGL', 178.2, 0.3], ['META', 512.7, -0.5], ['AMZN', 201.5, 0.7],
    ['SPY', 561.2, 0.25], ['BTC', 68420, 2.1], ['QQQ', 482.6, 0.4], ['JPM', 213.1, -0.2],
  ];

  function openPanel(o) {
    const p = document.getElementById('panel');
    p.classList.add('open');
    refreshPanel(o);
  }
  function closePanel() {
    document.getElementById('panel').classList.remove('open');
    window.OfficeApp.deselect();
  }

  function refreshPanel(o) {
    const a = o.agent;
    const p = document.getElementById('panel');
    p.style.setProperty('--c', a.color);
    document.getElementById('p-avatar').style.background = a.color;
    document.getElementById('p-avatar').textContent = a.short;
    document.getElementById('p-name').textContent = a.name;
    document.getElementById('p-role').textContent = a.role;
    var hb = document.getElementById('btn-handoff');
    hb.style.background = a.color;
    hb.style.color = '#fff';
    hb.style.borderColor = 'transparent';
    const stEl = document.getElementById('p-state');
    const st = o.paused ? 'paused' : o.state;
    stEl.textContent = st;
    stEl.className = 'state-chip ' + st;
    document.getElementById('p-blurb').textContent = a.blurb;
    document.getElementById('p-task').textContent = a.tasks[o.taskIndex % a.tasks.length];
    // bump task occasionally while working
    if (o.state === 'working') o.taskIndex++;
    // logs
    const log = document.getElementById('p-log');
    log.innerHTML = '';
    (o.logs.length ? o.logs : [{ t: '—', text: 'waiting for first run…', color: a.color }]).forEach((e) => {
      const row = document.createElement('div'); row.className = 'logrow';
      row.innerHTML = `<span class="lt">${e.t}</span><span class="lx">${escapeHtml(e.text)}</span>`;
      log.appendChild(row);
    });
    // pause button label
    document.getElementById('btn-pause').textContent = o.paused ? '► Resume agent' : '❚❚ Pause agent';
  }

  function feed(agent, line) {
    const f = document.getElementById('feed-list');
    const row = document.createElement('div');
    row.className = 'feed-row';
    row.innerHTML = `<span class="fdot" style="background:${agent.color}"></span>` +
      `<span class="fname" style="color:${agent.color}">${agent.short}</span>` +
      `<span class="ftext">${escapeHtml(line)}</span>`;
    f.prepend(row);
    while (f.children.length > 40) f.removeChild(f.lastChild);
  }

  function startTicker() {
    const t = document.getElementById('ticker-track');
    function render() {
      let html = '';
      SYMBOLS.forEach(([sym, price, chg]) => {
        const c = chg >= 0 ? '#3fae84' : '#d06f7a';
        const arrow = chg >= 0 ? '▲' : '▼';
        const pr = price > 1000 ? price.toLocaleString(undefined, { maximumFractionDigits: 0 }) : price.toFixed(2);
        html += `<span class="tk"><b>${sym}</b> ${pr} <span style="color:${c}">${arrow}${Math.abs(chg).toFixed(1)}%</span></span>`;
      });
      t.innerHTML = html + html; // duplicate for seamless scroll
    }
    render();
    setInterval(() => {
      SYMBOLS.forEach((row) => {
        const drift = (Math.random() - 0.48) * 0.4;
        row[2] = Math.max(-4, Math.min(4, row[2] + drift));
        row[1] = +(row[1] * (1 + drift / 100)).toFixed(2);
      });
      render();
    }, 2200);
  }

  function escapeHtml(s) { return String(s).replace(/[&<>]/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m])); }

  // wire static buttons after DOM ready
  function wire() {
    document.getElementById('p-close').addEventListener('click', closePanel);
    document.getElementById('btn-pause').addEventListener('click', () => {
      const id = currentId(); if (id) window.OfficeApp.togglePause(id);
    });
    document.getElementById('btn-handoff').addEventListener('click', () => {
      const id = currentId(); if (id) window.OfficeApp.manualHandoff(id);
    });
    document.getElementById('btn-reset').addEventListener('click', () => window.OfficeApp.resetView());
    // roster chips
    const roster = document.getElementById('roster');
    window.OfficeApp.AGENTS.forEach((a) => {
      const chip = document.createElement('button');
      chip.className = 'rchip'; chip.style.setProperty('--c', a.color);
      chip.innerHTML = `<span class="rdot"></span>${a.name}`;
      chip.addEventListener('click', () => window.OfficeApp.selectAgent(a.id));
      roster.appendChild(chip);
    });
  }
  function currentId() {
    const name = document.getElementById('p-name').textContent;
    const a = window.OfficeApp.AGENTS.find((x) => x.name === name);
    return a ? a.id : null;
  }

  window.OfficeUI = { openPanel, closePanel, refreshPanel, feed, startTicker, wire };
})();
