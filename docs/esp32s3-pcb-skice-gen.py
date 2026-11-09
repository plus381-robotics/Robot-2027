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
         '<text x="584" y="30" class="t11 c-muted b" text-anchor="middle">J_CTRL · PH-3</text>',
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
    o.append('<text x="584" y="340" class="t11 c-muted b" text-anchor="middle">J_UART · PH-3</text>')
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
    o.append(dot(140, 370) + dot(140, 440) + wire("M140,370 V386") + wire("M140,440 V456"))
    o.append('<text x="146" y="392" class="t9 c-muted">→ LED TX</text><text x="146" y="462" class="t9 c-muted">→ LED RX</text>')
    o.append('<rect x="488" y="355" width="30" height="100" rx="3" class="esd"/>')
    o.append('<text x="503" y="470" class="t9 c-esd" text-anchor="middle">U_ESD1</text>')
    o.append('<path d="M440,364 l10,6 l-10,6" class="wire"/>')
    o.append('<path d="M450,434 l-10,6 l10,6" class="wire"/>')
    o.append('<text x="40" y="490" class="t9 c-muted">ESD (TPD4E1U06, sa NRST i BOOT0) odmah uz konektore; LED-ovi se uzimaju sa ESP strane otpornika (slika 3).</text>')
    o.append('</svg>')
    return "\n".join(o)


def schematic2():
    o = ['<svg viewBox="0 0 760 470" role="img" aria-labelledby="f3t">',
         '<title id="f3t">Šema: konektor baterije, delitelj za VBAT, E-STOP preko Zener-a i PC817, LED za TX/RX sa produživačem impulsa</title>',
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
    # LED produživač
    o.append('<line x1="40" y1="300" x2="720" y2="300" class="sep"/>')
    o.append('<text x="40" y="322" class="t11 c-muted b">LED za TX ili RX (SN74LVC14, drugi kanal isti)</text>')
    o.append('<text x="40" y="364" class="t10 c-stm b">linija UART</text><text x="40" y="377" class="t9 c-muted">(ESP strana R)</text>')
    o.append(wire("M118,360 H170"))
    o.append('<path d="M170,344 L170,376 L198,360 Z" class="sym"/><circle cx="202" cy="360" r="4" class="sym"/>')
    o.append('<text x="184" y="338" class="t9 c-ink" text-anchor="middle">LVC14 A</text>')
    o.append(wire("M206,360 H240"))
    o.append('<path d="M240,350 L240,370 L258,360 Z M258,350 V370" class="wire"/>')
    o.append('<text x="249" y="344" class="t9 c-ink" text-anchor="middle">1N4148W</text>')
    o.append(wire("M258,360 H420"))
    o.append(dot(310, 360) + cap_v(310, 360, "220 nF"))
    o.append(dot(380, 360) + wire("M380,360 V372") + res_v(380, 372, "220 kΩ") + wire("M380,406 V414") + gnd(380, 414))
    o.append('<path d="M420,344 L420,376 L448,360 Z" class="sym"/><circle cx="452" cy="360" r="4" class="sym"/>')
    o.append('<text x="434" y="338" class="t9 c-ink" text-anchor="middle">LVC14 B</text>')
    o.append(wire("M456,360 H500"))
    o.append('<path d="M520,350 L520,370 L500,360 Z M500,350 V370" class="ledsym"/>')
    o.append('<path d="M512,346 l6,-8 M518,348 l6,-8" class="wire"/>')
    o.append(wire("M520,360 H560") + res_h(560, 360, "680 Ω") + wire("M600,360 H630"))
    o.append('<text x="636" y="364" class="t10 c-ink">3V3</text>')
    o.append('<text x="40" y="446" class="t9 c-muted">0 na liniji → A = 1 → C se puni → B = 0 → LED svetli; posle poslednjeg bajta</text>')
    o.append('<text x="40" y="458" class="t9 c-muted">gasi se za ~50 ms (220 kΩ · 220 nF). Ulaz A: ~4 pF, &lt; 1 µA, liniju ne oseća.</text>')
    o.append('</svg>')
    return "\n".join(o)


def layout():
    X = lambda mm: 110 + 5 * mm
    Y = lambda mm: 50 + 5 * mm
    o = ['<svg viewBox="0 0 760 620" role="img" aria-labelledby="fat">',
         '<title id="fat">Raspored ploče 100 × 100 mm: ESP ploča desno sa antenom na gornjoj ivici, ekran, tasteri i enkoder levo, konektori na donjoj ivici</title>',
         '<defs>',
         '<pattern id="hdrL" x="473" y="67.05" width="12.7" height="12.7" patternUnits="userSpaceOnUse"><circle cx="6.35" cy="6.35" r="2.4" class="padf"/></pattern>',
         '<pattern id="hdrR" x="587.3" y="67.05" width="12.7" height="12.7" patternUnits="userSpaceOnUse"><circle cx="6.35" cy="6.35" r="2.4" class="padf"/></pattern>',
         '<pattern id="exp2" x="110" y="379.2" width="45" height="12.7" patternUnits="userSpaceOnUse"><rect x="13" y="4" width="5" height="5" class="padf"/><rect x="26" y="4" width="5" height="5" class="padf"/></pattern>',
         '</defs>',
         '<rect x="110" y="50" width="500" height="500" rx="10" class="mask"/>',
         f'<rect x="{X(65)}" y="50" width="{5 * 35}" height="80" class="keepout"/>',
         f'<rect x="{X(78)}" y="{Y(63)}" width="75" height="{550 - Y(63)}" class="lane"/>',
         f'<text x="{X(85.5)}" y="{Y(84)}" class="t9 c-silk" text-anchor="middle">prolaz</text><text x="{X(85.5)}" y="{Y(86.5)}" class="t9 c-silk" text-anchor="middle">za USB</text>',
         f'<rect x="{X(75.5)}" y="46" width="98" height="44" class="cut"/>',
         hole(X(4), Y(4)), hole(X(4), Y(96)), hole(X(96), Y(96)), hole(X(96), Y(70))]
    # 5 V sabirnica
    o.append('<path d="M330,465 H462 V327 H479 M440,465 V470 M235,450 V401" class="bus"/>')
    # ekran
    o.append(f'<rect x="{X(6)}" y="{Y(4)}" width="180" height="170" rx="4" class="reserve"/>')
    o.append(f'<text x="{X(7)}" y="{Y(37)}" class="t9 c-silk">mesto za 1,3"</text>')
    o.append(f'<rect x="{X(8)}" y="{Y(5)}" width="136.5" height="139" rx="3" class="oledpcb"/>')
    o.append(f'<rect x="{X(9)}" y="{Y(11)}" width="126" height="76" rx="2" class="glass"/>')
    o.append(f'<text x="{X(21.6)}" y="{Y(19)}" class="t11 c-oled" text-anchor="middle">OLED 0,96"</text><text x="{X(21.6)}" y="{Y(22.5)}" class="t9 c-oled" text-anchor="middle">u ženskom header-u</text>')
    o.append(f'<rect x="{X(16.6)}" y="{Y(5.6)}" width="51" height="13" class="hdr"/>')
    for k in range(4):
        o.append(f'<circle cx="{X(17.87) + k * 12.7:.1f}" cy="{Y(6.9):.1f}" r="2.4" class="padf"/>')
    for (a, b) in ((10, 7), (33.3, 7), (10, 30.8), (33.3, 30.8)):
        o.append(f'<circle cx="{X(a):.1f}" cy="{Y(b):.1f}" r="5.5" class="drill"/>')
    o.append(f'<text x="{X(21.6)}" y="{Y(34)}" class="t9 c-silk" text-anchor="middle">SJ1/SJ2: GND↔3V3</text>')
    # STM konektori i blok
    o.append(conn(X(44), 50, 40, 30) + conn(X(54), 50, 40, 30))
    o.append(block(X(43), Y(8), 105, 22, ["U_ESD1 · 470Ω ×3"]))
    o.append(block(X(43), Y(13.4), 105, 22, ["2N7002 · 10k · 1k"]))
    o.append(block(X(43), Y(18.8), 105, 22, ["SN74LVC14 · RC"]))
    for k, (cls, t) in enumerate((("ledg", "TX"), ("ledg", "RX"), ("ledy", "B0"))):
        x = X(45 + 5 * k)
        o.append(f'<rect x="{x}" y="{Y(24.6)}" width="10" height="6" rx="1" class="{cls}"/>')
        o.append(f'<text x="{x + 5}" y="{Y(28.2)}" class="t9 c-silk" text-anchor="middle">{t}</text>')
    o.append(block(X(43), Y(31), 118, 22, ["I2C0 2k2 · GPIO7 10k"]))
    # tasteri i enkoder
    for k, (cls, t) in enumerate((("f-estop", "STOP"), ("f-yel", "NAZAD"), ("f-btn", "OK"))):
        x = X(3 + 15 * k)
        o.append(f'<rect x="{x}" y="{Y(43)}" width="60" height="60" rx="3" class="btnbody"/>')
        o.append(f'<circle cx="{x + 30}" cy="{Y(49)}" r="23" class="{cls}"/>')
        o.append(f'<text x="{x + 30}" y="{Y(49) + 4}" class="t10 c-cap b" text-anchor="middle">{t}</text>')
    o.append(f'<rect x="{X(51.8)}" y="{Y(42.3)}" width="62" height="67" rx="3" class="btnbody"/>')
    o.append(f'<circle cx="{X(58)}" cy="{Y(49)}" r="50" class="knob"/><circle cx="{X(58)}" cy="{Y(49)}" r="34" class="knob2"/>')
    o.append(f'<line x1="{X(58)}" y1="{Y(49) - 30}" x2="{X(58)}" y2="{Y(49) - 16}" class="knobmark"/>')
    o.append(f'<text x="{X(58)}" y="{Y(49) + 4}" class="t10 c-ink b" text-anchor="middle">ENK.</text>')
    o.append(block(X(3), Y(58.5), 210, 20, ["1k · 10k · 100nF ×3 · kućišta na GND"]))
    o.append(block(X(49), Y(58.5), 90, 20, ["10k · 10nF ×2"]))
    # dole levo
    o.append(conn(110, Y(62), 45, 140, '<rect x="110" y="379.2" width="45" height="101.6" fill="url(#exp2)"/>'))
    o.append(block(X(11), Y(63), 75, 36, ["U_ESD4/5", "PTC 0,5A"]))
    o.append(f'<circle cx="{X(34)}" cy="{Y(72)}" r="30" class="buzz"/><circle cx="{X(34)}" cy="{Y(72)}" r="5" class="drill"/>')
    o.append(f'<text x="{X(34)}" y="{Y(72) - 12}" class="t9 c-silk" text-anchor="middle">BUZZER</text>')
    o.append(block(X(42), Y(68), 70, 30, ["AO3400A", "1N4148W"]))
    # zona baterije, napajanje, konektori dole
    o.append('<rect x="158" y="438" width="64" height="110" rx="4" class="zone"/>')
    o.append('<text x="190" y="447" class="t9 c-estop" text-anchor="middle">zona bat.</text>')
    o.append(block(X(10.5), Y(80), 56, 46, ["PC817", "Z8V2·1k5", "100k/18k"]))
    o.append(block(X(23), Y(80), 105, 40, ["AO3401A · PTC 2A", "SMBJ6.0A · 100µF", "B5819W · LED 5V/3V3"]))
    o.append(block(X(35), Y(88.5), 130, 18, ["U_ESD3 · 4k7 · 100nF"]))
    o.append(block(X(63), Y(84), 74, 34, ["U_ESD2 · 470Ω", "PTC 1,1A"]))
    o.append(conn(X(11), Y(92.4), 52.5, 38, '<circle cx="178" cy="531" r="5" class="screw"/><circle cx="191" cy="531" r="5" class="screw"/><circle cx="204" cy="531" r="5" class="screw"/>'))
    o.append(conn(X(23), Y(90.2), 40, 49))
    o.append(conn(X(35), Y(94), 60, 30) + conn(X(49), Y(94), 60, 30) + conn(X(63), Y(93), 74.5, 35))
    # ESP ploča preko
    o.append(f'<rect x="{X(72.6)}" y="50" width="127" height="313.5" rx="3" class="devkit"/>')
    o.append('<rect x="473" y="67.05" width="12.7" height="279.4" class="hdr"/><rect x="473" y="67.05" width="12.7" height="279.4" fill="url(#hdrL)"/>')
    o.append('<rect x="587.3" y="67.05" width="12.7" height="279.4" class="hdr"/><rect x="587.3" y="67.05" width="12.7" height="279.4" fill="url(#hdrR)"/>')
    o.append(f'<rect x="{X(76.3)}" y="50" width="90" height="30" class="modpcb"/>')
    o.append(f'<path d="M{X(76.3) + 8},74 h4 v-14 h9 v14 h9 v-14 h9 v14 h9 v-14 h9 v14 h9 v-14 h9 v14 h4" class="ant"/>')
    o.append(f'<rect x="{X(76.3)}" y="80" width="90" height="97.5" rx="2" class="shield"/>')
    o.append(f'<text x="{X(85.3)}" y="126" class="t9 c-ink" text-anchor="middle">ESP32-S3</text><text x="{X(85.3)}" y="139" class="t9 c-ink" text-anchor="middle">N16R8</text>')
    o.append(f'<text x="{X(85.3)}" y="250" class="t10 c-silk" text-anchor="middle">ESP ploča</text><text x="{X(85.3)}" y="263" class="t9 c-silk" text-anchor="middle">na letvicama</text><text x="{X(85.3)}" y="276" class="t9 c-silk" text-anchor="middle">2 × 22</text>')
    o.append(f'<circle cx="{X(88)}" cy="{Y(50)}" r="5" class="rgbled"/>')
    o.append(f'<rect x="{X(80.8)}" y="{Y(61.2)}" width="45" height="18" rx="4" class="metal"/>')
    # vazdušne veze
    p1 = lambda i: 73.4 + (i - 1) * 12.7
    xl, xr = 479.35, 593.65
    for i, (tx, ty) in [(4, (335, 352)), (5, (335, 352)), (6, (335, 352)), (7, (215, 470)), (8, (430, 135)), (9, (430, 135)),
                        (10, (430, 112)), (11, (430, 112)), (12, (430, 217)), (15, (430, 217)), (16, (215, 490)),
                        (17, (445, 352)), (18, (445, 352)), (19, (445, 352)), (20, (390, 405))]:
        o.append(air(xl, p1(i), tx, ty))
    for i, (tx, ty) in [(4, (240, 375)), (5, (240, 375)), (6, (480, 470)), (7, (415, 500)), (8, (415, 500)), (9, (415, 500)),
                        (16, (240, 390)), (17, (480, 470)), (18, (480, 470))]:
        o.append(air(xr, p1(i), tx, ty))
    # natpisi spolja
    lab = [(350, 40, "J_UART", "middle"), (400, 40, "J_CTRL", "middle"), (104, 425, "PROŠIRENJE", "end"), (104, 438, "2×8", "end"),
           (191, 568, "BAT", "middle"), (245, 568, "5V IN", "middle"), (315, 568, "SENS1", "middle"), (385, 568, "SENS2", "middle"),
           (462, 568, "LIDAR", "middle")]
    for x, y, t, a in lab:
        o.append(f'<text x="{x}" y="{y}" class="t10 c-ink b" text-anchor="{a}">{E(t)}</text>')
    o.append(f'<text x="{X(85.3)}" y="18" class="t10 c-muted" text-anchor="middle">antena · izrez · bez bakra</text>')
    o.append(f'<line x1="{X(85.3)}" y1="23" x2="{X(85.3)}" y2="44" class="lead"/>')
    o.append('<text x="537" y="568" class="t10 c-muted" text-anchor="middle">USB-C (hitno)</text>')
    o.append('<path d="M110,585 V595 M610,585 V595 M110,590 H610" class="dim"/><text x="360" y="608" class="t10 c-muted" text-anchor="middle">100 mm</text>')
    o.append('<path d="M640,50 H650 M640,550 H650 M645,50 V550" class="dim"/><text x="656" y="304" class="t10 c-muted">100 mm</text>')
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
  <div class="eyebrow">Robot-2027 · ESP32 · verzija 2 · 9. 11. 2026</div>
  <h1>ESP32-S3 ploča: pinovi, konektori i raspored</h1>
  <p class="lede">Ploča 100 × 100 mm sa ekranom, tasterima i enkoderom, ESP ploča Waveshare ESP32-S3-DEV-KIT-N16R8 na
  letvicama, veza sa Nucleo-om, lidar RPLIDAR A2, E-STOP i baterija 4S. Verzija 2 uključuje odluke tima od 9. 11.
  Ceo tekst sa obrazloženjima je u <code>docs/esp32s3-pcb-istrazivanje.md</code>.</p>
  <nav class="toc" aria-label="Sadržaj">
    <a href="#odluke">Odluke</a><a href="#kupovina">Kupovina</a><a href="#pinovi">Pinovi</a><a href="#nrst">NRST i UART</a>
    <a href="#estop">E-STOP i LED</a><a href="#buzzer">Buzzer</a><a href="#esd">ESD</a><a href="#napajanje">Napajanje</a>
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
      <tr><td>Lidar</td><td>RPLIDAR A2 na UART2 (TX GPIO47, RX GPIO21), MOTOCTL GPIO42, originalni XH-5 kabl direktno u ploču</td></tr>
      <tr><td>TX/RX</td><td>LED-ovi preko SN74LVC14 sa produživačem impulsa (ne opterećuju liniju)</td></tr>
      <tr><td>USB</td><td>samo za hitno flešovanje; prolaz za utikač bez visokih delova</td></tr>
      <tr><td>Nucleo</td><td>posebna ploča, kabl &lt; 0,5 m; J_UART 1 TX, 2 GND, 3 RX (za kabl 1:1 do „RX, GND, TX")</td></tr>
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
    <figcaption><b>Slika 2.</b> Dva PH-3 konektora sa GND u sredini: obrnut ili zamenjen utikač ne kvari ništa.
    GPIO15 = 1 → reset; kad se ESP restartuje ili nema napajanje, R2 drži Q1 ugašen i STM32 radi.</figcaption>
  </figure>
  <ul class="list">
    <li>Impuls od ~60 µs na GPIO15 pri uključenju ESP-a kroz MOSFET ne prolazi (u nulu je, a nula gasi Q1).</li>
    <li>Kabl &lt; 0,5 m na 921600 baud-a: 470 Ω × ~40 pF ≈ 20 ns, bit traje 1,08 µs.</li>
    <li><b>Proveriti redosled na Nucleo strani</b> (RX, GND, TX) pre pravljenja kabla.</li>
  </ul>
</section>

<section id="estop">
  <h2><span class="sec">05</span>E-STOP, VBAT i LED-ovi za TX/RX</h2>
  <figure>
    <div class="fig">{schematic2()}</div>
    <figcaption><b>Slika 3.</b> Gore: konektor baterije (VBAT posle glavnog prekidača, VMOT posle E-STOP-a). Zener od 8,2 V
    gasi optokapler čim napon motora padne ispod ~9,4 V. Dole: jedan kanal LED-a; SN74LVC14 ima 6 invertora, za TX i
    RX trebaju 4, ulaze preostala dva vezati na GND.</figcaption>
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
  <p><b>Preporuka:</b> pasivni magnetni (CEM-1206S), PWM 2,4 kHz: potvrda, upozorenje i greška mogu različitim tonom.
  Kolo (AO3400A, 100 Ω, 100 kΩ, 1N4148W) je isto i za aktivni, pa se odluka može promeniti i posle izrade.</p>
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
      <tr><td>J_UART</td><td>JST PH 3 (B3B-PH-K-S)</td><td>1 TX→PA10 · 2 GND · 3 RX←PA9</td></tr>
      <tr><td>J_CTRL</td><td>JST PH 3 (B3B-PH-K-S)</td><td>1 NRST · 2 GND · 3 BOOT0</td></tr>
      <tr><td>LIDAR</td><td>JST XH 5 (B5B-XH-A)</td><td>kao kabl A2: 1 5V · 2 TX lidara · 3 RX lidara · 4 GND · 5 MOTOCTL</td></tr>
      <tr><td>SENS1, SENS2</td><td>JST PH 5 (B5B-PH-K-S)</td><td>1 GND · 2 3V3 · 3 SCL1 · 4 SDA1 · 5 INT</td></tr>
      <tr><td>EXP</td><td>kutijasti 2×8 (302-S161)</td><td>vidi ispod</td></tr>
      <tr><td>OLED</td><td>ženski 1×4 (PPTC041LFBN-RC)</td><td>SJ1/SJ2 biraju GND-VCC ili VCC-GND; rupe M2</td></tr>
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
  <h2><span class="sec">10</span>Raspored ploče 100 × 100 mm</h2>
  <figure>
    <div class="fig">{layout()}</div>
    <figcaption><b>Slika 5.</b> 5 px = 1 mm, pogled odozgo (gornja strana robota). Isprekidane linije su veze, a
    pravougaonici sa isprekidanom ivicom grupe delova. Antena na gornjoj ivici iznad izreza; USB-C gleda u ploču, ispod
    njega prolaz bez visokih delova.</figcaption>
  </figure>
  <ul class="list">
    <li><b>ESP ploča</b> uz desnu ivicu, antena gore (WiFi je glavni put za programiranje). Bez bakra ~10 mm oko antene.</li>
    <li><b>Gore levo ekran</b> (0,96", mesto za 1,3"); između ekrana i antene J_UART i J_CTRL sa ESD-om, MOSFET-om, LVC14 i LED-ovima TX, RX, BOOT0.</li>
    <li><b>Sredina:</b> STOP (crveni), NAZAD (žuti), OK (zeleni) i enkoder, ~4 mm od letvice ESP-a.</li>
    <li><b>Dole:</b> proširenje uspravno uz levu ivicu, buzzer, zona baterije, PWR_IN, SENS1, SENS2, LIDAR.</li>
    <li><b>Rupe M3:</b> (4,4), (4,96), (96,96), (96,70). Gore desno nema rupe zbog antene.</li>
    <li>Donji sloj ceo GND; 5 V ≥ 1,5 mm; merne tačke 5V, 3V3, GND, TX, RX, NRST, BOOT0, SDA0, SCL0, GPIO7, VBAT.</li>
  </ul>
  <p>Za v2 (posle sezone): ESP32-S3-WROOM-1-N16R8 zalemljen direktno, bez letvica; sopstveni 3V3 regulator i USB-C sa ESD-om.</p>
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
      <tr><td>Schmitt invertor</td><td>TI SN74LVC14ADR (SOIC-14)</td><td>1</td></tr>
      <tr><td>Optokapler</td><td>Sharp PC817X1NSZ1B</td><td>1</td></tr>
      <tr><td>Zener, diode</td><td>BZT52C8V2 · 1N4148W ×4 · B5819W</td><td></td></tr>
      <tr><td>TVS, PTC</td><td>Littelfuse SMBJ6.0A · Bourns MF-MSMF200-2, -110-2, -050-2</td><td></td></tr>
      <tr><td>Buzzer</td><td>Same Sky CEM-1206S (ili CMI-1275-05TH)</td><td>1</td></tr>
      <tr><td>Enkoder, tasteri</td><td>Bourns PEC11R-4220F-S0024 · Omron B3F-4055 + kapice B32</td><td>1 · 3</td></tr>
      <tr><td>Konektori</td><td>B2P-VH · B3B-PH-K-S ×2 · B5B-PH-K-S ×2 · B5B-XH-A · 302-S161 · stezaljka 3,5 mm 3 pina</td><td></td></tr>
      <tr><td>Header-i</td><td>Sullins PPTC221LFBN-RC ×2 · PPTC041LFBN-RC</td><td></td></tr>
    </tbody></table></div>
  <p>Otpornici, kondenzatori i LED-ovi u 0805. Cene proveriti na DigiKey-u.</p>
</section>

<section id="pitanja">
  <h2><span class="sec">13</span>Pitanja</h2>
  <ol class="list">
    <li>Ekran: 0,96" (SSD1306, radi sa sadašnjim kodom), 1,3" (obično SH1106, drugi drajver) ili 2,42" (SSD1309, SPI)? Redosled pinova na modulu?</li>
    <li>Buzzer: pasivni CEM-1206S (preporuka) ili aktivni CMI-1275-05TH?</li>
    <li>Nucleo strana: koji konektor i tačan redosled (RX, GND, TX)? Gde ide NRST/BOOT0 kabl?</li>
    <li>Lidar: proveriti redosled na komadu (VCC, TX, RX, GND, MOTOCTL) i da li je baš XH.</li>
    <li>Mesto ploče: gornja ploča robota? Ima li metala pored antene (nosač bikona, lidar)?</li>
    <li>Tasteri 12 × 12 mm na ploči ili veći tasteri na panelu?</li>
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
    <li>DigiKey: <a href="https://www.digikey.com/en/products/detail/texas-instruments/TPD4E1U06DBVR/3929533">TPD4E1U06DBVR</a>, <a href="https://www.digikey.ca/en/products/detail/same-sky-formerly-cui-devices/CEM-1206S/412414">CEM-1206S</a>, <a href="https://www.digikey.com.au/en/products/detail/same-sky-formerly-cui-devices/CMI-1275-05TH/25577239">CMI-1275-05TH</a></li>
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
