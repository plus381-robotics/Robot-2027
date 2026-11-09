# Pravi docs/esp32s3-pcb-skice.html (SVG skice + tabele) iz jednog izvora.
#   python3 docs/esp32s3-pcb-skice-gen.py /tmp/artifact.html docs/esp32s3-pcb-skice.html
# Prvi fajl je bez <html>/<head> (za objavljivanje kao artifact), drugi je pun HTML za otvaranje iz repoa.
# Tekst sa obrazloženjima: docs/esp32s3-pcb-istrazivanje.md.
import sys
from html import escape as E

# ---------------------------------------------------------------- pin mapa (Waveshare ESP32-S3-DEV-KIT = DevKitC-1)
J1 = [
    ("3V3", "3V3 izlaz · spolja ≤ ~250 mA", "pwr"),
    ("3V3", "", "pwr"),
    ("RST", "+ EN na EXP (reset ESP-a)", "aux"),
    ("IO4", "T1 · NAZAD (taster na ploči)", "btn"),
    ("IO5", "T2 · OK", "btn"),
    ("IO6", "T3 · STOP", "btn"),
    ("IO7", "E-STOP (PC817)", "estop"),
    ("IO15", "STM NRST · preko 2N7002", "stm"),
    ("IO16", "STM BOOT0 · 470 Ω", "stm"),
    ("IO17", "UART1 TX → PA10", "stm"),
    ("IO18", "UART1 RX ← PA9", "stm"),
    ("IO8", "I2C0 SDA · ekran", "i2c"),
    ("IO3", "× strapping", "no"),
    ("IO46", "× strapping", "no"),
    ("IO9", "I2C0 SCL · ekran", "i2c"),
    ("IO10", "+ VBAT · ADC1 (100k/18k)", "estop"),
    ("IO11", "ENC A (CLK)", "enc"),
    ("IO12", "ENC B (DT)", "enc"),
    ("IO13", "ENC SW", "enc"),
    ("IO14", "Buzzer · PWM", "buz"),
    ("5V", "5V ulaz · preko B5819W", "pwr"),
    ("G", "GND", "no"),
]
J3 = [
    ("G", "GND", "no"),
    ("IO43", "× UART0 · CH343", "no"),
    ("IO44", "× UART0 · CH343", "no"),
    ("IO1", "+ analog (ADC1) · EXP", "aux"),
    ("IO2", "+ analog (ADC1) · EXP", "aux"),
    ("IO42", "+ LIDAR MOTOCTL · PWM", "u2"),
    ("IO41", "+ I2C1 SDA · senzori", "i2c"),
    ("IO40", "+ I2C1 SCL · senzori", "i2c"),
    ("IO39", "+ INT / XSHUT senzora", "i2c"),
    ("IO38", "RGB LED na ESP ploči · status", "led"),
    ("IO37", "× octal PSRAM", "no"),
    ("IO36", "× octal PSRAM", "no"),
    ("IO35", "× octal PSRAM", "no"),
    ("IO0", "× BOOT taster · strapping", "no"),
    ("IO45", "× strapping (VDD_SPI)", "no"),
    ("IO48", "+ rezerva · EXP", "aux"),
    ("IO47", "UART2 TX → lidar RX", "u2"),
    ("IO21", "UART2 RX ← lidar TX (bilo 48)", "u2"),
    ("IO20", "× USB D+ (hub)", "no"),
    ("IO19", "× USB D− (hub)", "no"),
    ("G", "GND", "no"),
    ("G", "GND", "no"),
]


def pinmap():
    o = ['<svg viewBox="0 0 780 640" role="img" aria-labelledby="f1t">',
         '<title id="f1t">Raspored pinova ESP32-S3 ploče (Waveshare DEV-KIT, isto kao DevKitC-1) sa funkcijama</title>',
         '<rect x="300" y="30" width="160" height="580" rx="6" class="mask"/>',
         '<rect x="333" y="30" width="94" height="34" class="modpcb"/>',
         '<path d="M345,54 h5 v-14 h10 v14 h10 v-14 h10 v14 h10 v-14 h10 v14 h10 v-14 h10 v14 h5" class="ant"/>',
         '<rect x="333" y="64" width="94" height="136" rx="2" class="shield"/>',
         '<text x="380" y="124" class="t9 c-ink" text-anchor="middle">ESP32-S3</text>',
         '<text x="380" y="138" class="t9 c-ink" text-anchor="middle">WROOM-1</text>',
         '<text x="380" y="152" class="t9 c-ink" text-anchor="middle">N16R8</text>',
         '<text x="380" y="20" class="t10 c-muted" text-anchor="middle">antena</text>',
         '<text x="312" y="20" class="t11 c-ink b" text-anchor="middle">J1</text>',
         '<text x="448" y="20" class="t11 c-ink b" text-anchor="middle">J3</text>',
         '<circle cx="408" cy="270" r="6" class="rgbled"/>',
         '<text x="408" y="290" class="t9 c-silk" text-anchor="middle">RGB</text>',
         '<text x="380" y="420" class="t10 c-silk" text-anchor="middle">ESP32-S3-DEV-KIT</text>',
         '<text x="380" y="434" class="t9 c-silk" text-anchor="middle">pogled odozgo</text>',
         '<rect x="362" y="604" width="36" height="14" rx="3" class="metal"/>',
         '<text x="380" y="634" class="t10 c-muted" text-anchor="middle">1 × USB-C (hub: nativni USB + CH343)</text>']
    for i, ((l1, t1, g1), (l3, t3, g3)) in enumerate(zip(J1, J3)):
        y = 48 + i * 25
        o.append(f'<circle cx="312" cy="{y}" r="4.5" class="pad"/>')
        o.append(f'<circle cx="448" cy="{y}" r="4.5" class="pad"/>')
        o.append(f'<text x="294" y="{y + 4}" class="t10 c-muted" text-anchor="end">{E(l1)}</text>')
        o.append(f'<text x="466" y="{y + 4}" class="t10 c-muted">{E(l3)}</text>')
        if t1:
            cls = "hollow" if g1 == "no" else f"f-{g1}"
            o.append(f'<rect x="250" y="{y - 4.5}" width="9" height="9" rx="2" class="{cls} s-{g1}"/>')
            o.append(f'<text x="244" y="{y + 4}" class="t11 {"c-no" if g1 == "no" else "c-ink"}" text-anchor="end">{E(t1)}</text>')
        if t3:
            cls = "hollow" if g3 == "no" else f"f-{g3}"
            o.append(f'<rect x="501" y="{y - 4.5}" width="9" height="9" rx="2" class="{cls} s-{g3}"/>')
            o.append(f'<text x="516" y="{y + 4}" class="t11 {"c-no" if g3 == "no" else "c-ink"}">{E(t3)}</text>')
    o.append('</svg>')
    return "\n".join(o)


# ---------------------------------------------------------------- pomoćne funkcije za SVG
def res_h(x, y, label, lx=None):
    return (f'<rect x="{x}" y="{y - 7}" width="40" height="14" class="sym"/>'
            f'<text x="{x + 20}" y="{y - 12}" class="t10 c-ink" text-anchor="middle">{E(label)}</text>')


def res_v(x, y, label):
    return (f'<rect x="{x - 7}" y="{y}" width="14" height="34" class="sym"/>'
            f'<text x="{x + 14}" y="{y + 21}" class="t10 c-ink">{E(label)}</text>')


def gnd(x, y):
    return (f'<path d="M{x - 9},{y} h18 M{x - 5.5},{y + 4} h11 M{x - 2},{y + 8} h4" class="wire"/>')


def wire(d):
    return f'<path d="{d}" class="wire"/>'


def dot(x, y):
    return f'<circle cx="{x}" cy="{y}" r="3" class="dot"/>'


def conn(x, y, w, h, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" class="conn"/>{extra}'


def block(x, y, w, h, lines):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" class="blk"/>'
    n = len(lines)
    for k, t in enumerate(lines):
        ty = y + h / 2 + 3.5 + (k - (n - 1) / 2) * 11
        s += f'<text x="{x + w / 2}" y="{ty:.1f}" class="t9 c-silk" text-anchor="middle">{E(t)}</text>'
    return s


def air(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1:.1f}" x2="{x2}" y2="{y2:.1f}" class="air"/>'


def hole(x, y):
    return f'<circle cx="{x}" cy="{y}" r="13" class="ring"/><circle cx="{x}" cy="{y}" r="7.5" class="drill"/>'




def cap_v(x, y, label):
    """Kondenzator uspravno: žica od y do ploča, ploče, žica do GND."""
    return (wire(f"M{x},{y} V{y + 12}") + f'<path d="M{x - 12},{y + 12} h24 M{x - 12},{y + 18} h24" class="wire"/>'
            + wire(f"M{x},{y + 18} V{y + 30}") + gnd(x, y + 30)
            + f'<text x="{x + 16}" y="{y + 19}" class="t10 c-ink">{E(label)}</text>')


def schematic():
    o = ['<svg viewBox="0 0 760 500" role="img" aria-labelledby="f2t">',
         '<title id="f2t">Šema: NRST preko 2N7002, BOOT0 sa pull-down-om, UART sa rednim otpornicima, dva odvojena konektora sa GND u sredini</title>',
         '<text x="40" y="30" class="t11 c-muted b">ESP32-S3</text>',
         '<text x="584" y="30" class="t11 c-muted b" text-anchor="middle">J_CTRL · XH-3</text>',
         '<text x="640" y="30" class="t11 c-muted b">→ Nucleo</text>']
    o.append('<rect x="560" y="42" width="48" height="108" rx="3" class="conn"/>')
    for yy, n in ((60, "1 NRST"), (95, "2 GND"), (130, "3 BOOT0")):
        o.append(f'<circle cx="560" cy="{yy}" r="3" class="pad"/>')
        o.append(f'<text x="567" y="{yy + 4}" class="t9 c-conn">{n}</text>')
    o.append('<text x="622" y="64" class="t10 c-ink">CN7-14 NRST (CN6-3)</text>')
    o.append('<text x="622" y="99" class="t10 c-ink">CN7-8 GND</text>')
    o.append('<text x="622" y="134" class="t10 c-ink">CN7-7 BOOT0</text>')
    o.append(wire("M560,95 H535 V101") + gnd(535, 101))
    o.append('<text x="40" y="137" class="t11 c-stm b">GPIO15</text>')
    o.append(wire("M100,133 H170") + res_h(170, 133, "R1 1 kΩ") + wire("M210,133 H380"))
    o.append(dot(300, 133) + wire("M300,133 V150") + res_v(300, 150, "R2 100 kΩ") + wire("M300,184 V196") + gnd(300, 196))
    o.append('<rect x="380" y="105" width="56" height="56" rx="4" class="sym"/>')
    o.append('<text x="408" y="129" class="t10 c-ink b" text-anchor="middle">Q1</text>')
    o.append('<text x="408" y="143" class="t9 c-ink" text-anchor="middle">2N7002</text>')
    o.append('<text x="372" y="128" class="t9 c-muted" text-anchor="end">G</text>')
    o.append('<text x="426" y="100" class="t9 c-muted">D</text><text x="426" y="174" class="t9 c-muted">S</text>')
    o.append(wire("M420,105 V60 H560") + wire("M420,161 V180") + gnd(420, 180))
    o.append('<text x="40" y="160" class="t9 c-muted">1 = reset (obrnuta logika)</text>')
    o.append('<text x="40" y="244" class="t11 c-stm b">GPIO16</text>')
    o.append(wire("M100,240 H170") + res_h(170, 240, "R3 470 Ω") + wire("M210,240 H520 V130 H560"))
    o.append(dot(470, 240) + wire("M470,240 V252") + res_v(470, 252, "R4 10 kΩ") + wire("M470,286 V296") + gnd(470, 296))
    o.append(dot(380, 240) + wire("M380,240 V250") + '<text x="386" y="260" class="t9 c-muted">→ LED BOOT0</text>')
    o.append('<text x="40" y="267" class="t9 c-muted">1 = bootloader (samo za flešovanje)</text>')
    o.append('<text x="40" y="284" class="t9 c-muted">Nucleo ima svoj ~10 kΩ → ≈ 3,0 V na BOOT0</text>')
    o.append('<line x1="40" y1="318" x2="720" y2="318" class="sep"/>')
    o.append('<text x="584" y="340" class="t11 c-muted b" text-anchor="middle">J_UART · XH-3</text>')
    o.append('<rect x="560" y="352" width="48" height="108" rx="3" class="conn"/>')
    for yy, n in ((370, "1 TX"), (405, "2 GND"), (440, "3 RX")):
        o.append(f'<circle cx="560" cy="{yy}" r="3" class="pad"/>')
        o.append(f'<text x="567" y="{yy + 4}" class="t9 c-conn">{n}</text>')
    o.append('<text x="622" y="374" class="t10 c-ink">RX · PA10 (D2)</text>')
    o.append('<text x="622" y="409" class="t10 c-ink">GND</text>')
    o.append('<text x="622" y="444" class="t10 c-ink">TX · PA9 (D8)</text>')
    o.append(wire("M560,405 H542 V411") + gnd(542, 411))
    o.append('<text x="40" y="374" class="t11 c-stm b">GPIO17 TX</text>')
    o.append(wire("M118,370 H170") + res_h(170, 370, "R5 470 Ω") + wire("M210,370 H560"))
    o.append('<text x="40" y="444" class="t11 c-stm b">GPIO18 RX</text>')
    o.append(wire("M118,440 H170") + res_h(170, 440, "R6 470 Ω") + wire("M210,440 H560"))
    o.append('<rect x="488" y="355" width="30" height="100" rx="3" class="esd"/>')
    o.append('<text x="503" y="470" class="t9 c-esd" text-anchor="middle">U_ESD1</text>')
    o.append('<path d="M440,364 l10,6 l-10,6" class="wire"/>')
    o.append('<path d="M450,434 l-10,6 l10,6" class="wire"/>')
    o.append('<text x="40" y="490" class="t9 c-muted">ESD (TPD4E1U06, isti čip štiti i NRST i BOOT0) odmah uz konektore, pre rednih otpornika.</text>')
    o.append('</svg>')
    return "\n".join(o)


def schematic2():
    o = ['<svg viewBox="0 0 760 300" role="img" aria-labelledby="f3t">',
         '<title id="f3t">Šema: konektor baterije, delitelj za VBAT, E-STOP preko Zener-a i PC817</title>',
         '<text x="40" y="26" class="t11 c-muted b">BAT · stezaljka 3,5 mm</text>',
         '<rect x="30" y="38" width="320" height="182" rx="6" class="zone"/>',
         '<text x="190" y="214" class="t9 c-estop" text-anchor="middle">zona baterije · ≥ 2 mm do ostalog bakra</text>',
         '<rect x="40" y="46" width="48" height="110" rx="3" class="conn"/>']
    for yy, n in ((60, "1 GND"), (100, "2 VBAT"), (140, "3 VMOT")):
        o.append(f'<circle cx="88" cy="{yy}" r="3" class="pad"/>')
        o.append(f'<text x="45" y="{yy + 4}" class="t9 c-conn">{n}</text>')
    o.append(wire("M88,60 H110 V66") + gnd(110, 66))
    # VBAT -> ADC
    o.append(wire("M88,100 H120") + res_h(120, 100, "100 kΩ") + wire("M160,100 H600"))
    o.append(dot(500, 100) + wire("M500,100 V112") + res_v(500, 112, "18 kΩ") + wire("M500,146 V156") + gnd(500, 156))
    o.append(dot(560, 100) + cap_v(560, 100, "100 nF"))
    o.append('<text x="606" y="104" class="t11 c-estop b">GPIO10 · VBAT</text>')
    o.append('<text x="445" y="92" class="t9 c-muted" text-anchor="middle">16,8 V → 2,56 V · 12 V → 1,83 V</text>')
    # VMOT -> Zener -> 1k5 -> PC817
    o.append(wire("M88,140 H130"))
    o.append('<path d="M150,132 L150,148 L136,140 Z M136,132 V148 M136,132 h-4 M136,148 h4" class="wire"/>')
    o.append('<text x="143" y="126" class="t9 c-ink" text-anchor="middle">BZT52C8V2</text>')
    o.append(wire("M150,140 H200") + res_h(200, 140, "1,5 kΩ 1206") + wire("M240,140 H300"))
    o.append(dot(285, 140) + dot(285, 175) + wire("M285,140 V147") + '<rect x="279" y="147" width="12" height="21" class="sym"/>' + wire("M285,168 V175"))
    o.append('<text x="273" y="164" class="t9 c-ink" text-anchor="end">1N4148W</text>')
    o.append(wire("M285,175 H300") + wire("M285,175 V190") + gnd(285, 190))
    o.append('<rect x="300" y="120" width="80" height="70" rx="4" class="sym"/>')
    o.append('<line x1="340" y1="124" x2="340" y2="186" class="sep"/>')
    o.append('<text x="340" y="203" class="t10 c-ink b" text-anchor="middle">PC817</text>')
    o.append('<path d="M314,148 L330,148 L322,162 Z M314,162 h16" class="wire"/>')
    o.append('<path d="M356,140 V175 M356,152 L370,140 M356,164 L370,175" class="wire"/>')
    # izlaz -> GPIO7
    o.append(wire("M380,140 H420 V250 H600") + wire("M380,175 H395 V188") + gnd(395, 188))
    o.append(dot(460, 250) + wire("M460,250 V238") + '<rect x="453" y="204" width="14" height="34" class="sym"/>' + wire("M460,204 V194"))
    o.append('<text x="460" y="188" class="t9 c-ink" text-anchor="middle">3V3</text><text x="474" y="225" class="t10 c-ink">10 kΩ</text>')
    o.append(dot(530, 250) + cap_v(530, 250, "100 nF"))
    o.append('<text x="606" y="254" class="t11 c-estop b">GPIO7 · E-STOP</text>')
    o.append('<text x="606" y="270" class="t9 c-muted">0 = motori pod naponom</text><text x="606" y="282" class="t9 c-muted">1 = E-STOP ili prekinut kabl</text>')
    o.append('</svg>')
    return "\n".join(o)




# ---------------------------------------------------------------- stil
CSS = r"""
:root{
  /* Inženjerski izveštaj: papir sa zelenkastim tonom, skice kao pogled na ploču (zelena maska, bela štampa, bakar) */
  --paper:#f3f4f1; --paper-2:#e8ece6; --ink:#17211d; --muted:#56635c; --rule:#d2d9d2;
  --accent:#a3461f; --accent-ink:#ffffff;
  --mask:#245a42; --mask-edge:#173d2c; --silk:#f4f1e6; --cu:#c8823f; --pad:#d9a441; --hdr:#22272a;
  --shield:#c4c8cb; --modpcb:#2c3b4b; --conn:#ece3c8; --conn-edge:#9c8f6c; --conn-ink:#3c3527; --metal:#9aa1a6;
  --oled:#1b2532; --oledscr:#05080c; --oledtx:#7fd3ff;
  --g-stm:#2f6db0; --g-estop:#c2362b; --g-btn:#2b8452; --g-i2c:#7a4bc0; --g-enc:#10827a; --g-buz:#c06f17;
  --g-neo:#c03c8c; --g-u2:#4050b0; --g-pwr:#8e3022; --g-aux:#6d7a2e; --g-no:#8d948f;
  --warn:#a3321f; --warn-bg:#f8e9e3; --prep:#7a5a12; --prep-bg:#f5eed9; --opc:#4a5a52; --opc-bg:#e6ebe7;
  --f-display:"Barlow Semi Condensed","Arial Narrow",system-ui,sans-serif;
  --f-body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --paper:#111613; --paper-2:#18201b; --ink:#e3e8e4; --muted:#9caaa2; --rule:#2a332e;
  --accent:#e2895a; --accent-ink:#1a0d06;
  --mask:#1f4d39; --mask-edge:#0f2a1e; --silk:#efeadb; --cu:#d8955a; --pad:#e0b052; --hdr:#0b0d0e;
  --shield:#a5abaf; --modpcb:#22313f; --conn:#d9cfb2; --conn-edge:#857a5c; --conn-ink:#2e281c; --metal:#7d858a;
  --oled:#1b2532; --oledscr:#05080c; --oledtx:#7fd3ff;
  --g-stm:#6aa3e6; --g-estop:#ef6b5e; --g-btn:#5cc28a; --g-i2c:#ab86ec; --g-enc:#3fc0b5; --g-buz:#eda24d;
  --g-neo:#ee75bd; --g-u2:#8a96ee; --g-pwr:#e07a63; --g-aux:#b2c25e; --g-no:#78817c;
  --warn:#f28c76; --warn-bg:#2b1915; --prep:#e3c06a; --prep-bg:#2a2414; --opc:#a9b8b0; --opc-bg:#1c2420;
  color-scheme:dark; } }
:root[data-theme="dark"]{
  --paper:#111613; --paper-2:#18201b; --ink:#e3e8e4; --muted:#9caaa2; --rule:#2a332e;
  --accent:#e2895a; --accent-ink:#1a0d06;
  --mask:#1f4d39; --mask-edge:#0f2a1e; --silk:#efeadb; --cu:#d8955a; --pad:#e0b052; --hdr:#0b0d0e;
  --shield:#a5abaf; --modpcb:#22313f; --conn:#d9cfb2; --conn-edge:#857a5c; --conn-ink:#2e281c; --metal:#7d858a;
  --oled:#1b2532; --oledscr:#05080c; --oledtx:#7fd3ff;
  --g-stm:#6aa3e6; --g-estop:#ef6b5e; --g-btn:#5cc28a; --g-i2c:#ab86ec; --g-enc:#3fc0b5; --g-buz:#eda24d;
  --g-neo:#ee75bd; --g-u2:#8a96ee; --g-pwr:#e07a63; --g-aux:#b2c25e; --g-no:#78817c;
  --warn:#f28c76; --warn-bg:#2b1915; --prep:#e3c06a; --prep-bg:#2a2414; --opc:#a9b8b0; --opc-bg:#1c2420;
  color-scheme:dark;
}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:var(--f-body);font-size:16px;line-height:1.55;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.wrap{max-width:1060px;margin:0 auto;padding-block:40px 64px;display:flex;flex-direction:column;gap:56px}
header{display:flex;flex-direction:column;gap:14px;border-bottom:2px solid var(--ink);padding-bottom:28px}
.eyebrow{font-family:var(--f-mono);font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1,h2,h3{font-family:var(--f-display);text-wrap:balance;margin:0;line-height:1.1}
h1{font-size:clamp(2rem,5vw,3rem);font-weight:700;letter-spacing:-.01em}
h2{font-size:1.75rem;font-weight:700;display:flex;gap:12px;align-items:baseline}
h2 .sec{font-family:var(--f-mono);font-size:.85rem;font-weight:500;color:var(--accent);letter-spacing:.04em}
h3{font-size:1.2rem;font-weight:600}
p{margin:0;max-width:68ch}
.lede{font-size:1.08rem;color:var(--ink);max-width:72ch}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
code,.mono{font-family:var(--f-mono);font-size:.88em}
section{display:flex;flex-direction:column;gap:18px}
nav.toc{display:flex;flex-wrap:wrap;gap:6px 18px;font-family:var(--f-mono);font-size:.82rem}
nav.toc a{color:var(--muted);text-decoration:none}
nav.toc a:hover{color:var(--accent);text-decoration:underline}
.verdict{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.verdict > div{border:1px solid var(--rule);background:var(--paper-2);border-radius:6px;padding:14px 16px;display:flex;flex-direction:column;gap:6px;min-width:0}
.verdict .k{font-family:var(--f-mono);font-size:.74rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.verdict .v{font-family:var(--f-display);font-size:1.3rem;font-weight:600;line-height:1.2}
.tbl{overflow-x:auto;border-top:1px solid var(--ink)}
table{border-collapse:collapse;width:100%;font-size:.92rem;font-variant-numeric:tabular-nums}
th{font-family:var(--f-mono);font-size:.72rem;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);text-align:left;padding:10px 12px 8px 0;border-bottom:1px solid var(--rule);white-space:nowrap}
td{padding:9px 12px 9px 0;border-bottom:1px solid var(--rule);vertical-align:top}
td:first-child{white-space:nowrap}
.chip{display:inline-block;font-family:var(--f-mono);font-size:.7rem;font-weight:500;letter-spacing:.05em;padding:2px 7px;border-radius:3px;white-space:nowrap}
.chip.mora{color:var(--warn);background:var(--warn-bg)}
.chip.prep{color:var(--prep);background:var(--prep-bg)}
.chip.opc{color:var(--opc);background:var(--opc-bg)}
figure{margin:0;display:flex;flex-direction:column;gap:10px}
.fig{overflow-x:auto;background:var(--paper-2);border:1px solid var(--rule);border-radius:6px;padding:14px}
.fig svg{display:block;width:100%;min-width:640px;height:auto}
figcaption,.cap{font-size:.88rem;color:var(--muted);max-width:80ch}
.cap b{color:var(--ink);font-weight:600}
figcaption b{color:var(--ink);font-weight:600}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:.84rem}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:10px;height:10px;border-radius:2px;display:inline-block}
.two{display:flex;flex-direction:column;gap:44px}
.row{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:24px;align-items:start}
.row > *{min-width:0}
.row .fig svg{min-width:460px}
.side{display:flex;flex-direction:column;gap:12px}
@media (max-width:820px){ .row{grid-template-columns:1fr} }
.opt{display:flex;flex-direction:column;gap:12px;min-width:0}
.opt .tag{font-family:var(--f-mono);font-size:.75rem;color:var(--accent);letter-spacing:.05em;text-transform:uppercase}
.pc{display:grid;grid-template-columns:1fr 1fr;gap:14px;font-size:.9rem}
.pc > div{min-width:0}
.pc h4{margin:0 0 4px;font-family:var(--f-mono);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:500}
.pc ul{margin:0;padding-left:1.1em;display:flex;flex-direction:column;gap:3px}
ul.list,ol.list{margin:0;padding-left:1.25em;display:flex;flex-direction:column;gap:6px;max-width:80ch}
.callout{border-left:3px solid var(--accent);background:var(--paper-2);padding:12px 16px;border-radius:0 6px 6px 0;max-width:80ch}
.callout.warn{border-left-color:var(--warn);background:var(--warn-bg)}
pre.code{font-family:var(--f-mono);font-size:.82rem;line-height:1.45;background:var(--paper-2);border:1px solid var(--rule);border-radius:6px;padding:12px 14px;overflow-x:auto;margin:0}
footer{font-size:.84rem;color:var(--muted);border-top:1px solid var(--rule);padding-top:18px;display:flex;flex-direction:column;gap:8px}
footer ul{margin:0;padding-left:1.1em;display:flex;flex-direction:column;gap:4px}
@media (max-width:560px){ .pc{grid-template-columns:1fr} h2{flex-direction:column;gap:2px} }
/* SVG */
svg text{font-family:var(--f-mono)}
.t9{font-size:9px}.t10{font-size:10px}.t11{font-size:11px}.b{font-weight:600}
.c-ink{fill:var(--ink)}.c-muted{fill:var(--muted)}.c-silk{fill:var(--silk)}.c-no{fill:var(--g-no)}
.c-conn{fill:var(--conn-ink)}.c-stm{fill:var(--g-stm)}.c-estop{fill:var(--g-estop)}.c-oled{fill:var(--oledtx)}
.mask{fill:var(--mask);stroke:var(--mask-edge);stroke-width:1.5}
.modpcb{fill:var(--modpcb)}
.ant{fill:none;stroke:var(--cu);stroke-width:2}
.shield{fill:var(--shield)}
.pad{fill:var(--pad);stroke:var(--mask-edge);stroke-width:1}
.padf{fill:var(--pad)}
.metal{fill:var(--metal)}
.hdr{fill:var(--hdr)}
.conn{fill:var(--conn);stroke:var(--conn-edge);stroke-width:1}
.screw{fill:var(--metal);stroke:var(--conn-edge)}
.blk{fill:none;stroke:var(--silk);stroke-width:.9;stroke-dasharray:3 2;opacity:.9}
.air{stroke:var(--silk);stroke-width:.7;stroke-dasharray:2 3;opacity:.55}
.bus{fill:none;stroke:var(--cu);stroke-width:6;stroke-linecap:round;stroke-linejoin:round;opacity:.55}
.trace{fill:none;stroke:var(--cu);stroke-width:2.2}
.ring{fill:var(--cu);opacity:.75}
.drill{fill:var(--paper)}
.cut{fill:var(--paper-2);stroke:var(--silk);stroke-width:1;stroke-dasharray:4 3}
.keepout{fill:var(--silk);opacity:.13}
.devkit{fill:var(--ink);fill-opacity:.16;stroke:var(--silk);stroke-width:1;stroke-dasharray:6 3}
.zone{fill:none;stroke:var(--g-estop);stroke-width:1.4;stroke-dasharray:5 3}
.lead{stroke:var(--muted);stroke-width:1}
.dim{fill:none;stroke:var(--muted);stroke-width:1}
.sym{fill:var(--paper-2);stroke:var(--ink);stroke-width:1.4}
.wire{fill:none;stroke:var(--ink);stroke-width:1.4}
.dot{fill:var(--ink)}
.sep{stroke:var(--rule);stroke-width:1;stroke-dasharray:4 4}
.ribbon{fill:none;stroke:var(--metal);stroke-width:12;opacity:.75}
.back{fill:none;stroke:var(--silk);stroke-width:1;stroke-dasharray:4 3}
.oled{fill:var(--oled)}.oledscr{fill:var(--oledscr)}
.knob{fill:var(--hdr)}.knob2{fill:var(--metal)}.knobmark{stroke:var(--hdr);stroke-width:3;stroke-linecap:round}
.buzz{fill:var(--hdr)}
.nucleo{fill:var(--paper);fill-opacity:.92;stroke:var(--silk);stroke-width:1}
.hollow{fill:none}
.f-stm{fill:var(--g-stm)}.f-estop{fill:var(--g-estop)}.f-btn{fill:var(--g-btn)}.f-i2c{fill:var(--g-i2c)}
.f-enc{fill:var(--g-enc)}.f-buz{fill:var(--g-buz)}.f-neo{fill:var(--g-neo)}.f-u2{fill:var(--g-u2)}
.f-pwr{fill:var(--g-pwr)}.f-aux{fill:var(--g-aux)}
.s-no{stroke:var(--g-no);stroke-width:1.2}
@media (prefers-reduced-motion: reduce){*{scroll-behavior:auto}}
"""


CSS += r"""
:root{ --g-yel:#c99a12; --g-led:#c03c8c; --led-g:#2fbf5f; --led-y:#e6b422; --on-cap:#ffffff; --esd:#2f6db0; }
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){ --g-yel:#e8c04a; --g-led:#ee75bd; --esd:#6aa3e6; } }
:root[data-theme="dark"]{ --g-yel:#e8c04a; --g-led:#ee75bd; --esd:#6aa3e6; }
.f-yel{fill:var(--g-yel)}.f-led{fill:var(--g-led)}.c-cap{fill:var(--on-cap)}
.ledg{fill:var(--led-g)}.ledy{fill:var(--led-y)}
.rgbled{fill:var(--paper);stroke:var(--g-led);stroke-width:2}
.reserve{fill:none;stroke:var(--silk);stroke-width:1;stroke-dasharray:4 3;opacity:.7}
.lane{fill:var(--silk);opacity:.08}
.glass{fill:var(--oledscr)}.oledpcb{fill:var(--modpcb)}
.btnbody{fill:var(--hdr)}
.esd{fill:none;stroke:var(--esd);stroke-width:1.4;stroke-dasharray:4 2}.c-esd{fill:var(--esd)}
.ledsym{fill:var(--led-g);stroke:var(--ink);stroke-width:1.2}
.new{color:var(--accent);font-weight:600}
"""

LEGEND = "".join(
    f'<span><i style="background:var(--g-{g})"></i>{t}</span>' for g, t in [
        ("stm", "STM32 (UART, NRST, BOOT0)"), ("estop", "E-STOP, VBAT"), ("btn", "tasteri"), ("i2c", "I2C, senzori"),
        ("enc", "enkoder"), ("buz", "buzzer"), ("u2", "UART2 / lidar"), ("led", "RGB LED na ESP ploči"),
        ("pwr", "napajanje"), ("aux", "rezerva, analog")]) + \
    '<span><i style="border:1.2px solid var(--g-no)"></i>ne koristiti</span>'


def page():
    return f"""<title>ESP32-S3 PCB istraživanje</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@600;700&amp;family=IBM+Plex+Mono:wght@400;500;600&amp;family=IBM+Plex+Sans:wght@400;500;600&amp;display=swap">
<style>{CSS}</style>
<div class="wrap">
<header>
  <div class="eyebrow">Robot-2027 · ESP32 · verzija 3 · 9. 11. 2026</div>
  <h1>ESP32-S3 ploča: pinovi, konektori i raspored</h1>
  <p class="lede">Ploča manja od 100 × 100 mm sa ekranom, tasterima i enkoderom, ESP ploča Waveshare
  ESP32-S3-DEV-KIT-N16R8 na letvicama, veza sa Nucleo-om, lidar RPLIDAR A2M8-R4, E-STOP i baterija 4S. Verzija 3:
  bez LED-ova na TX/RX, XH 3 ka Nucleo-u, raspored ploče čeka mehaničke podatke.
  Ceo tekst sa obrazloženjima je u <code>docs/esp32s3-pcb-istrazivanje.md</code>.</p>
  <nav class="toc" aria-label="Sadržaj">
    <a href="#odluke">Odluke</a><a href="#kupovina">Kupovina</a><a href="#pinovi">Pinovi</a><a href="#nrst">NRST i UART</a>
    <a href="#estop">E-STOP i VBAT</a><a href="#buzzer">Buzzer</a><a href="#esd">ESD</a><a href="#napajanje">Napajanje</a>
    <a href="#konektori">Konektori</a><a href="#raspored">Raspored</a><a href="#delovi">Delovi</a><a href="#pitanja">Pitanja</a>
  </nav>
</header>

<section id="odluke">
  <h2><span class="sec">01</span>Odluke</h2>
  <div class="verdict">
    <div><span class="k">ESP ploča</span><span class="v">Waveshare DEV-KIT-N16R8</span>
      <span>Isti raspored pinova kao DevKitC-1; RGB LED na GPIO38; jedan USB-C.</span></div>
    <div><span class="k">Korisnički interfejs</span><span class="v">Na ploči</span>
      <span>Tasteri i enkoder zalemljeni, ekran u ženskom header-u.</span></div>
    <div><span class="k">Baterija</span><span class="v">4S, zajednički GND</span>
      <span>INA3221 na powerboard-u; ADC na GPIO10 kao rezerva.</span></div>
    <div><span class="k">Ploča</span><span class="v">100 × 100 mm, 2 sloja</span>
      <span>PCBWay, ručno lemljenje, delovi sa DigiKey-a.</span></div>
  </div>
  <div class="tbl"><table>
    <thead><tr><th>Tema</th><th>Odluka</th></tr></thead>
    <tbody>
      <tr><td>NeoPixel</td><td>izbačen; status pokazuje RGB LED na ESP ploči (GPIO38, samo softver)</td></tr>
      <tr><td>Lidar</td><td>RPLIDAR A2M8-R4 na UART2 (TX GPIO47, RX GPIO21), MOTOCTL GPIO42; XH 5 kao na adapteru: PWM, GND, TX, RX, 5V</td></tr>
      <tr><td>LED-ovi</td><td>bez LED-ova na TX/RX; ostaju 5V, 3V3 i BOOT0</td></tr>
      <tr><td>Ekran</td><td>0,96" SSD1306, testiran, radi sa sadašnjim kodom</td></tr>
      <tr><td>Buzzer</td><td>pasivni, Same Sky CEM-1206S, PWM 2,4 kHz</td></tr>
      <tr><td>USB</td><td>samo za hitno flešovanje; prolaz za utikač bez visokih delova</td></tr>
      <tr><td>Nucleo</td><td>posebna ploča, kabl &lt; 0,5 m; JST XH 3 i za UART i za NRST/BOOT0; J_UART 1 TX, 2 GND, 3 RX (kabl 1:1 do „RX, GND, TX")</td></tr>
      <tr><td>DC-DC</td><td>SiC417 na powerboard-u, izlaz podesiti na <b>5,2 V</b> (lidar traži ≥ 4,9 V)</td></tr>
      <tr><td>STOP taster</td><td>ostaje samo na ESP-u</td></tr>
    </tbody></table></div>
</section>

<section id="kupovina">
  <h2><span class="sec">02</span>Šta kupiti sutra (malina314)</h2>
  <p>Malina314 prodaje Waveshare ploče. U Waveshare šemi ESP32-S3-DEV-KIT su letvice raspoređene isto kao kod
  Espressif DevKitC-1, RGB LED (WS2812B) je na GPIO38, a USB-C ide preko hub-a CH334F na nativni USB i CH343.
  5 V sa USB-a prolazi kroz Schottky B5819WS, pa spoljnih 5 V ne ide nazad u računar.</p>
  <div class="tbl"><table>
    <thead><tr><th>Ploča</th><th>Cena</th><th>Za nas</th></tr></thead>
    <tbody>
      <tr><td><b>ESP32-S3-DEV-KIT-N16R8</b> (WROOM-1, 16 MB / 8 MB octal)</td><td>1.390 RSD</td><td><span class="chip opc">KUPITI 2</span> robot + razvoj/rezerva</td></tr>
      <tr><td>ESP32-S3-DEV-KIT-N8R8</td><td>1.290 RSD</td><td><span class="chip opc">OK</span> isto radi, manje fleša</td></tr>
      <tr><td>ESP32-S3-DEV-KIT-N16R8-U (SMA, štap 155 mm)</td><td>1.490 RSD</td><td><span class="chip prep">AKO</span> ploča završi u metalu</td></tr>
      <tr><td>ESP32-S3 WROOM-2 N32R16V</td><td>1.890 RSD</td><td><span class="chip mora">NE</span> memorija 1,8 V, GPIO47/48 na 1,8 V</td></tr>
      <tr><td>ESP32-S3-Nano, ESP32-S3-Pico</td><td>1.190 / 1.290</td><td><span class="chip mora">NE</span> drugi raspored pinova</td></tr>
      <tr><td>ESP32-P4, ESP32-C5, RGB LCD/Matrix ploče</td><td></td><td><span class="chip mora">NE</span> drugi čip ili zauzeti pinovi</td></tr>
    </tbody></table></div>
  <div class="callout"><p><b>Pre narudžbe PCB-a</b> izmeriti ESP ploču kad stigne (razmak redova letvica, dužinu, mesto
  USB-C i antene) i po tome napraviti footprint. Pinovi stižu nezalemljeni (4 × 20): na ESP ploču muški 20 + 2 po
  strani, na našu ploču ženski 1 × 22.</p></div>
</section>

<section id="pinovi">
  <h2><span class="sec">03</span>Pinovi</h2>
  <p>U odnosu na sliku: UART2 RX ide sa GPIO48 na GPIO21 (NeoPixel je izbačen), dodati su VBAT (10), MOTOCTL (42),
  I2C1 (41, 40) i INT (39). GPIO38 i 48 se ne koriste ni za šta bitno, pa plan radi i na Espressif pločama
  (LED na 38 ili 48).</p>
  <figure>
    <div class="fig">{pinmap()}</div>
    <div class="legend">{LEGEND}</div>
    <figcaption><b>Slika 1.</b> J1 i J3 od antene ka USB-u. Sa „+" su novi pinovi, sa „×" oni koji se ne koriste.</figcaption>
  </figure>
</section>

<section id="nrst">
  <h2><span class="sec">04</span>NRST, BOOT0 i UART ka Nucleo-u</h2>
  <figure>
    <div class="fig">{schematic()}</div>
    <figcaption><b>Slika 2.</b> Dva XH-3 konektora sa GND u sredini: obrnut ili zamenjen utikač ne kvari ništa.
    GPIO15 = 1 → reset; kad se ESP restartuje ili nema napajanje, R2 drži Q1 ugašen i STM32 radi.</figcaption>
  </figure>
  <ul class="list">
    <li>Impuls od ~60 µs na GPIO15 pri uključenju ESP-a kroz MOSFET ne prolazi (u nulu je, a nula gasi Q1).</li>
    <li>Kabl &lt; 0,5 m na 921600 baud-a: 470 Ω × ~40 pF ≈ 20 ns, bit traje 1,08 µs.</li>
    <li>J_UART, J_CTRL i LIDAR su iste serije (XH): utikač XH 3 može da se gurne u XH 5 sa strane i dovede 5 V lidara na liniju ka Nucleo-u. Postaviti ih daleko jedan od drugog i obeležiti.</li>
  </ul>
</section>

<section id="estop">
  <h2><span class="sec">05</span>E-STOP i VBAT</h2>
  <figure>
    <div class="fig">{schematic2()}</div>
    <figcaption><b>Slika 3.</b> Gore: konektor baterije (VBAT posle glavnog prekidača, VMOT posle E-STOP-a). Zener od 8,2 V
    gasi optokapler čim napon motora padne ispod ~9,4 V.</figcaption>
  </figure>
  <div class="tbl"><table>
    <thead><tr><th>Napon baterije</th><th>VBAT na GPIO10</th><th>Struja LED-a u PC817</th></tr></thead>
    <tbody>
      <tr><td>16,8 V (puna)</td><td>2,56 V</td><td>≈ 4,9 mA</td></tr>
      <tr><td>14,8 V (nominalno)</td><td>2,26 V</td><td>≈ 3,6 mA</td></tr>
      <tr><td>12,0 V (prazna)</td><td>1,83 V</td><td>≈ 1,7 mA (dovoljno: pull-up traži 0,33 mA)</td></tr>
    </tbody></table></div>
</section>

<section id="buzzer">
  <h2><span class="sec">06</span>Buzzer: vrste</h2>
  <div class="tbl"><table>
    <thead><tr><th>Vrsta</th><th>Kako radi</th><th>Upravljanje</th><th>DigiKey primer</th></tr></thead>
    <tbody>
      <tr><td><b>Aktivni</b></td><td>ima svoj oscilator; na 5 V sam zvoni jednim tonom</td><td>uključi/isključi</td><td>Same Sky CMI-1275-05TH · 5 V, 110 mA, 2,7 kHz, 85 dB</td></tr>
      <tr><td><b>Pasivni</b></td><td>samo membrana; zvuči na frekvenciji koju mu pošalješ</td><td>PWM, više tonova</td><td>Same Sky CEM-1206S · 5 V, 45 mA, 2,4 kHz, 85 dB</td></tr>
      <tr><td>Magnetni</td><td>kalem i membrana; glasan na 5 V</td><td colspan="2">treba tranzistor i diodu preko buzzera</td></tr>
      <tr><td>Piezo</td><td>kristal; skoro bez struje, tiši na 5 V</td><td colspan="2">bez diode, otpornik paralelno</td></tr>
    </tbody></table></div>
  <p><b>Odluka:</b> pasivni magnetni (CEM-1206S), PWM 2,4 kHz: potvrda, upozorenje i greška različitim tonom.
  Kolo: AO3400A, 100 Ω u gejtu, 100 kΩ gejt-GND, 1N4148W preko buzzera.</p>
</section>

<section id="esd">
  <h2><span class="sec">07</span>ESD: gde tačno</h2>
  <p>Deo: <b>TI TPD4E1U06DBVR</b> (4 kanala, SOT-23-6, 0,8 pF, ±15 kV), na DigiKey-u oko 0,60 $ za 1 i 0,37 $ od 10 komada
  (proveriti). Postavlja se ≤ 5 mm od pinova konektora, redom konektor → ESD → redni otpornik → ESP, GND pin vijom
  direktno na GND sloj.</p>
  <div class="tbl"><table>
    <thead><tr><th>Oznaka</th><th>Gde</th><th>Linije</th></tr></thead>
    <tbody>
      <tr><td>U_ESD1</td><td>između J_UART i J_CTRL</td><td>UART1 TX, RX, NRST, BOOT0</td></tr>
      <tr><td>U_ESD2</td><td>kod LIDAR konektora</td><td>UART2 TX, RX, MOTOCTL</td></tr>
      <tr><td>U_ESD3</td><td>između SENS1 i SENS2</td><td>SDA1, SCL1, INT</td></tr>
      <tr><td>U_ESD4</td><td>kod konektora za proširenje</td><td>GPIO1, GPIO2, GPIO48, EN</td></tr>
      <tr><td>U_ESD5</td><td>kod konektora za proširenje</td><td>SDA1, SCL1, UART2 TX, RX</td></tr>
    </tbody></table></div>
  <ul class="list">
    <li><b>Tasteri i enkoder</b> ne trebaju ESD niz: kućišta (držači) na GND, 1 kΩ redno i 100 nF (tasteri), 10 kΩ i 10 nF (enkoder).</li>
    <li><b>Ekran</b> je u header-u na ploči, bez kabla. <b>BAT</b> ima 100 kΩ i 1,5 kΩ + Zener redno. <b>5 V ulaz</b> ima TVS SMBJ6.0A. <b>USB</b> je na ESP ploči.</li>
  </ul>
</section>

<section id="napajanje">
  <h2><span class="sec">08</span>Napajanje</h2>
  <figure>
<pre class="mermaid">
flowchart LR
  BAT["Baterija 4S"] --> SW["glavni prekidač i osigurač"]
  SW --> ES["E-STOP"] --> MOT["Motori i aktuatori"]
  SW --> DCDC["DC-DC SiC417, 5,2 V"]
  SW -. "VBAT" .-> ADC["100k/18k → GPIO10"]
  ES -. "VMOT" .-> OPT["Zener + PC817 → GPIO7"]
  DCDC --> IN["PWR_IN: AO3401A, PTC 2 A, SMBJ6.0A, 100 µF"]
  IN --> D1["B5819W"] --> DK["ESP ploča 5V → LDO 3V3"]
  DK --> L3["ESP32-S3, OLED, enkoder, tasteri, senzori"]
  IN --> P1["PTC 1,1 A"] --> LID["Lidar 5 V"]
  IN --> P2["PTC 0,5 A"] --> EXP["Proširenje 5 V"]
  IN --> BZ["Buzzer"]
</pre>
    <figcaption><b>Slika 4.</b> P-MOSFET umesto Schottky diode na ulazu: Schottky bi oduzeo 0,4 V i lidar bi dobio manje od 4,9 V.</figcaption>
  </figure>
  <div class="tbl"><table>
    <thead><tr><th>Potrošač</th><th>Tipično</th><th>Najviše</th></tr></thead>
    <tbody>
      <tr><td>ESP32-S3 + PSRAM</td><td>120 mA</td><td>500 mA</td></tr>
      <tr><td>OLED</td><td>20 mA</td><td>40 mA</td></tr>
      <tr><td>RPLIDAR A2</td><td>~450 mA</td><td>~600 mA + start</td></tr>
      <tr><td>Buzzer</td><td>30 mA</td><td>60 mA</td></tr>
      <tr><td>Senzori I2C</td><td>50 mA</td><td>100 mA</td></tr>
      <tr><td>Proširenje</td><td>-</td><td>500 mA (PTC)</td></tr>
      <tr><td><b>Ukupno</b></td><td><b>~0,7 A</b></td><td><b>~1,8 A</b></td></tr>
    </tbody></table></div>
</section>

<section id="konektori">
  <h2><span class="sec">09</span>Konektori</h2>
  <div class="tbl"><table>
    <thead><tr><th>Konektor</th><th>Tip (MPN)</th><th>Pinovi</th></tr></thead>
    <tbody>
      <tr><td>PWR_IN</td><td>JST VH 2 (B2P-VH)</td><td>1 +5V · 2 GND</td></tr>
      <tr><td>BAT</td><td>stezaljka 3,5 mm, 3 pina</td><td>1 GND · 2 VBAT · 3 VMOT</td></tr>
      <tr><td>J_UART</td><td>JST XH 3 (B3B-XH-A)</td><td>1 TX→PA10 · 2 GND · 3 RX←PA9</td></tr>
      <tr><td>J_CTRL</td><td>JST XH 3 (B3B-XH-A)</td><td>1 NRST · 2 GND · 3 BOOT0</td></tr>
      <tr><td>LIDAR</td><td>JST XH 5 (B5B-XH-A)</td><td>kao adapter A2M8-R4: 1 PWM · 2 GND · 3 TX lidara (→ GPIO21) · 4 RX lidara (← GPIO47) · 5 5V; ista orijentacija kao na adapteru</td></tr>
      <tr><td>SENS1, SENS2</td><td>JST PH 5 (B5B-PH-K-S)</td><td>1 GND · 2 3V3 · 3 SCL1 · 4 SDA1 · 5 INT</td></tr>
      <tr><td>EXP</td><td>kutijasti 2×8 (302-S161)</td><td>vidi ispod</td></tr>
      <tr><td>OLED 0,96"</td><td>ženski 1×4 (PPTC041LFBN-RC)</td><td>redosled i rupe M2 sa testiranog modula</td></tr>
      <tr><td>ESP ploča</td><td>ženski 1×22 ×2 (PPTC221LFBN-RC)</td><td></td></tr>
    </tbody></table></div>
  <pre class="code"> EXP 2×8
 1 GND            2 GND
 3 3V3            4 5V (PTC 0,5 A)
 5 SDA1 (41)      6 SCL1 (40)
 7 GPIO1 (ADC1)   8 GPIO2 (ADC1)
 9 GPIO39 (INT)  10 GPIO48
11 UART2 TX (47) 12 UART2 RX (21)   ← deli se sa lidarom
13 EN (reset)    14 GND
15 GND           16 GND</pre>
</section>

<section id="raspored">
  <h2><span class="sec">10</span>Raspored ploče</h2>
  <div class="callout"><p>Skica iz verzije 2 je odbačena. Novi raspored se crta kad budu poznati mehanički podaci
  (pitanja u bloku 13). Do tada važe samo ograničenja koja ne zavise od mehanike.</p></div>
  <ul class="list">
    <li><b>Antena ESP-a na ivici ploče</b>, bez bakra i vodova ~10 mm oko nje, izrez između letvica, ništa metalno iznad ni pored.</li>
    <li><b>USB-C ESP-a dostupan</b> za hitno flešovanje: na ivici ili sa prolazom bez visokih delova.</li>
    <li><b>Ekran, tasteri i enkoder</b> na strani ka korisniku; dugme enkodera (Ø ~20 mm) ne sme da udara u ESP ploču ni ekran.</li>
    <li><b>ESD ≤ 5 mm od konektora</b>, redni otpornici odmah iza.</li>
    <li><b>Zona baterije</b> u jednom uglu, ≥ 2 mm do ostalog bakra.</li>
    <li><b>J_UART i J_CTRL daleko od LIDAR konektora</b> (ista serija XH).</li>
    <li>Pinovi za tastere, E-STOP, STM32, ekran, enkoder i buzzer su na J1, za lidar, senzore i proširenje na J3: konektore staviti na odgovarajuću stranu ESP ploče.</li>
    <li>Manje od 100 × 100 mm, 2 sloja, donji sloj ceo GND, 5 V ≥ 1,5 mm, rupe gde traži šasija.</li>
  </ul>
</section>

<section id="softver">
  <h2><span class="sec">11</span>Softver kad ploča stigne</h2>
  <ol class="list">
    <li><code>board_s3.py</code>: pinovi sa slike 1, <code>UART2_TX=47</code>, <code>UART2_RX=21</code>, <code>LIDAR_MOTOCTL=42</code>, <code>I2C1</code> 41/40, <code>SENS_INT=39</code>, <code>VBAT_ADC=10</code>, <code>RGB_LED=38</code>, <code>STM_NRST_ACTIVE=1</code>, <code>ESTOP_ACTIVE=1</code>.</li>
    <li>NRST sa obrnutom logikom u <code>match.StmReset</code> i <code>stmflash</code>; bootloader STM32 uvek na 115200.</li>
    <li>E-STOP i VBAT na stranicama PROVERA/ROBOT; RGB LED kao status (K-1); buzzer PWM 2,4 kHz (K-2); lidar (L-1..L-3).</li>
    <li>Host test: svi pinovi postoje, bez duplikata i bez zabranjenih pinova.</li>
  </ol>
</section>

<section id="delovi">
  <h2><span class="sec">12</span>Delovi (DigiKey)</h2>
  <div class="tbl"><table>
    <thead><tr><th>Deo</th><th>MPN</th><th>Kom</th></tr></thead>
    <tbody>
      <tr><td>ESD 4 kanala</td><td>TI TPD4E1U06DBVR</td><td>5</td></tr>
      <tr><td>N-MOSFET</td><td>onsemi 2N7002LT1G · AOS AO3400A</td><td>2 · 1</td></tr>
      <tr><td>P-MOSFET</td><td>AOS AO3401A</td><td>1</td></tr>
      <tr><td>Optokapler</td><td>Sharp PC817X1NSZ1B</td><td>1</td></tr>
      <tr><td>Zener, diode</td><td>BZT52C8V2 · 1N4148W ×2 · B5819W</td><td></td></tr>
      <tr><td>TVS, PTC</td><td>Littelfuse SMBJ6.0A · Bourns MF-MSMF200-2, -110-2, -050-2</td><td></td></tr>
      <tr><td>Buzzer</td><td>Same Sky CEM-1206S</td><td>1</td></tr>
      <tr><td>Enkoder, tasteri</td><td>Bourns PEC11R-4220F-S0024 · Omron B3F-4055 + kapice B32</td><td>1 · 3</td></tr>
      <tr><td>Konektori</td><td>B2P-VH · B3B-XH-A ×2 · B5B-PH-K-S ×2 · B5B-XH-A · 302-S161 · stezaljka 3,5 mm 3 pina</td><td></td></tr>
      <tr><td>Header-i</td><td>Sullins PPTC221LFBN-RC ×2 · PPTC041LFBN-RC</td><td></td></tr>
    </tbody></table></div>
  <p>Otpornici, kondenzatori i LED-ovi (5V, 3V3, BOOT0) u 0805. Cene proveriti na DigiKey-u.</p>
</section>

<section id="pitanja">
  <h2><span class="sec">13</span>Pitanja za raspored ploče</h2>
  <ol class="list">
    <li>Gde je ploča na robotu i kako je okrenuta? Koja strana gleda ka korisniku?</li>
    <li>Gde treba da budu ekran, tasteri i enkoder, i gde su rupe za šasiju?</li>
    <li>Sa koje strane dolaze kablovi za Nucleo, powerboard (5 V, baterija, E-STOP), lidar i senzore?</li>
    <li>Šta je iznad i oko ploče (lidar, nosač bikona, metal), zbog antene?</li>
    <li>Najveća dozvoljena visina delova (ESP na letvicama ~20 mm, ekran ~12 mm, dugme enkodera ~25 mm)?</li>
    <li>Ako postoji crtež ili model mesta (Onshape), raspored se crta po njemu.</li>
  </ol>
</section>

<footer>
  <span>Izvori</span>
  <ul>
    <li><a href="https://files.waveshare.com/wiki/ESP32-S3-DEV-KIT-N8R8/ESP32-S3-DEV-KIT-N8R8-schematic.pdf">Waveshare ESP32-S3-DEV-KIT šema</a>, <a href="https://docs.waveshare.com/ESP32-S3-DEV-KIT-N8R8">Waveshare dokumentacija</a></li>
    <li><a href="https://malina314.com/kategorija-proizvoda/esp32-esp-32/mikrokontroler/">malina314: ESP32 ploče</a></li>
    <li><a href="https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html">ESP32-S3-DevKitC-1 v1.1</a>, <a href="https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html">ESP32-S3 Schematic Checklist</a></li>
    <li><a href="https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf">UM1724 Nucleo-64</a></li>
    <li><a href="https://cdn.robotshop.com/media/R/Rpk/RB-Rpk-27/pdf/rplidar-a2m8-360-laser-scanner-open-box-dimensional-drawing.pdf">RPLIDAR A2M8 crtež sa utikačem</a></li>
    <li>DigiKey: <a href="https://www.digikey.com/en/products/detail/texas-instruments/TPD4E1U06DBVR/3929533">TPD4E1U06DBVR</a>, <a href="https://www.digikey.ca/en/products/detail/same-sky-formerly-cui-devices/CEM-1206S/412414">CEM-1206S</a></li>
    <li><a href="https://datasheet.chipsmall.com/SIC417CD-T1-E3/131889.pdf">SiC417 datasheet</a></li>
  </ul>
</footer>
</div>
"""


body = page()
# 1) artifact: bez sopstvenog skeleta (dodaje ga objavljivanje)
open(sys.argv[1], "w", encoding="utf-8").write(body)
# 2) repo: pun HTML za otvaranje iz fajla (mermaid sa CDN-a)
if len(sys.argv) > 2:
    full = ('<!doctype html>\n<html lang="sr-Latn">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<!-- Generisano iz docs/esp32s3-pcb-skice-gen.py; tekst: docs/esp32s3-pcb-istrazivanje.md -->\n'
            '</head>\n<body>\n' + body +
            '\n<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>\n'
            '<script>mermaid.initialize({startOnLoad:true,theme:matchMedia("(prefers-color-scheme: dark)").matches?"dark":"neutral"});</script>\n'
            '</body>\n</html>\n')
    open(sys.argv[2], "w", encoding="utf-8").write(full)
print("ok")
