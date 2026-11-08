// Time charts (uPlot): speed, turn rate, wheels. A vertical line shows the current time;
// clicking a chart seeks there.
const DEFS = [
  { title: 'Speed [m/s]', series: [['v', 'v', '#ffffff'], ['v_ref', 'v ref', '#4aa3ff']] },
  { title: 'Turn rate [rad/s]', series: [['w', 'ω', '#ffffff'], ['w_ref', 'ω ref', '#4aa3ff']] },
  { title: 'Wheels [m/s]', series: [['vl', 'left', '#3ecf8e'], ['vr', 'right', '#ff9f43']] },
];

export class Charts {
  constructor(el, onSeek) {
    this.el = el; this.onSeek = onSeek; this.plots = []; this.lines = [];
    new ResizeObserver(() => this.resize()).observe(el);
  }

  setRun(run) {
    this.el.innerHTML = '';
    this.plots = []; this.lines = [];
    const c = run.cols;
    const t = c.t.map(v => v / 1000);
    for (const d of DEFS) {
      const div = document.createElement('div');
      this.el.appendChild(div);
      const opts = {
        title: d.title, width: 300, height: 140,
        cursor: { sync: { key: 'eurosim' }, drag: { x: false, y: false } },
        legend: { show: true, live: true },
        scales: { x: { time: false }, y: { range: (u, lo, hi) => {
          if (lo == null || hi == null) return [-1, 1];
          if (hi - lo < 0.2) { const m = (hi + lo) / 2; return [m - 0.5, m + 0.5]; }
          const pad = (hi - lo) * 0.08; return [lo - pad, hi + pad];
        } } },
        axes: [
          { stroke: '#8a96a5', grid: { stroke: '#2e3642', width: 1 }, ticks: { stroke: '#2e3642' }, size: 26 },
          { stroke: '#8a96a5', grid: { stroke: '#2e3642', width: 1 }, ticks: { stroke: '#2e3642' }, size: 40 },
        ],
        series: [{ label: 't [s]', value: (u, v) => v == null ? '-' : v.toFixed(2) },
          ...d.series.map(([, label, color]) => ({ label, stroke: color, width: 1.5,
            value: (u, v) => v == null ? '-' : v.toFixed(3) }))],
      };
      const data = [t, ...d.series.map(([k]) => c[k] || t.map(() => null))];
      const u = new uPlot(opts, data, div);
      u.over.addEventListener('click', e => {
        const x = u.posToVal(e.offsetX, 'x');
        this.onSeek(x * 1000);
      });
      const line = document.createElement('div');
      Object.assign(line.style, { position: 'absolute', top: 0, bottom: 0, width: '1px', background: '#ffb547', pointerEvents: 'none' });
      u.over.appendChild(line);
      this.plots.push(u); this.lines.push(line);
    }
    this.resize();
  }

  update(run) {                      // live: new data in existing charts
    if (!this.plots.length) return this.setRun(run);
    const c = run.cols, t = c.t.map(v => v / 1000);
    DEFS.forEach((d, i) => this.plots[i].setData([t, ...d.series.map(([k]) => c[k] || t.map(() => null))]));
    this._placeSteps();
  }

  // Početak svakog koraka: tanka linija u boji koraka sa brojem (u svakom grafiku), da se vidi koji deo
  // brzine pripada kom koraku.
  setSteps(steps) {
    this.steps = steps || [];
    this.stepEls = this.plots.map(u => {
      for (const e of u.over.querySelectorAll('.cstep')) e.remove();
      return this.steps.map(s => {
        const d = document.createElement('div'); d.className = 'cstep' + (s.fail ? ' fail' : '');
        d.style.setProperty('--c', s.color); d.dataset.idx = s.idx;
        d.innerHTML = `<span>${s.idx}</span>`;
        u.over.appendChild(d); return d;
      });
    });
    this._placeSteps();
  }

  _placeSteps() {
    (this.stepEls || []).forEach((els, i) => {
      const u = this.plots[i];
      els.forEach((d, k) => { d.style.left = u.valToPos(this.steps[k].t / 1000, 'x') + 'px'; });
    });
  }

  setTime(tms) {
    this.plots.forEach((u, i) => {
      const x = u.valToPos(tms / 1000, 'x');
      this.lines[i].style.left = x + 'px';
    });
    this._placeSteps();                            // uPlot dobije veličinu tek posle prvog crtanja
  }

  resize() {
    const n = this.plots.length || 1;
    const w = Math.max(200, Math.floor((this.el.clientWidth - 6 * (n - 1)) / n));
    const h = Math.max(100, this.el.clientHeight - 30);
    for (const u of this.plots) u.setSize({ width: w, height: h });
    this._placeSteps();
  }
}
