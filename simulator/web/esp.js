// ESP panel: the robot's real OLED (128x64, drawn by ESP32/lib/ui.py + pages.py in the simulator) and
// virtual buttons wired to the real inputs.py through fake pins: encoder (turn / click), BACK, OK, STOP.
// Holding a button works like on the robot (long BACK = menu, hold OK = confirm).
export class EspPanel {
  constructor(root, send) {
    this.send = send;
    this.canvas = root.querySelector('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.img = this.ctx.createImageData(128, 64);
    this.enabled = false;
    this.last = null;
    this.hint = root.querySelector('.esp-hint');
    for (const b of root.querySelectorAll('[data-btn]')) {
      const name = b.dataset.btn;
      const down = e => { e.preventDefault(); if (!this.enabled) return; b.classList.add('down'); this.send(['btn', name, 1]); };
      const up = () => { if (!b.classList.contains('down')) return; b.classList.remove('down'); this.send(['btn', name, 0]); };
      b.addEventListener('pointerdown', down);
      b.addEventListener('pointerup', up);
      b.addEventListener('pointerleave', up);
    }
    for (const b of root.querySelectorAll('[data-rot]')) {
      b.addEventListener('click', () => this.enabled && this.send(['rot', +b.dataset.rot]));
    }
    this.canvas.addEventListener('wheel', e => {
      if (!this.enabled) return;
      e.preventDefault();
      this.send(['rot', e.deltaY > 0 ? 1 : -1]);
    }, { passive: false });
    this.setScreen(null);
  }

  setEnabled(on) {
    this.enabled = on;
    this.canvas.parentElement.parentElement.classList.toggle('live', on);
    this.hint.textContent = on ? 'buttons are live · mouse wheel on the screen = encoder' :
      'recorded screen · buttons work in Live mode';
  }

  setScreen(s) {                       // s = {b: base64 1024 B, on, flip} or null
    if (s === this.last) return;
    this.last = s;
    const d = this.img.data;
    const bytes = s && s.on !== false ? atob(s.b) : null;
    for (let y = 0; y < 64; y++) {
      for (let x = 0; x < 128; x++) {
        const sx = s && s.flip ? 127 - x : x, sy = s && s.flip ? 63 - y : y;
        const on = bytes ? (bytes.charCodeAt(sy * 16 + (sx >> 3)) >> (7 - (sx & 7))) & 1 : 0;
        const i = (y * 128 + x) * 4;
        if (on) { d[i] = 170; d[i + 1] = 225; d[i + 2] = 255; } else { d[i] = 6; d[i + 1] = 9; d[i + 2] = 14; }
        d[i + 3] = 255;
      }
    }
    this.ctx.putImageData(this.img, 0, 0);
  }
}
