# Pravi docs/esp32s3-pcb-skice.html (SVG skice + tabele) iz jednog izvora.
#   python3 docs/esp32s3-pcb-skice-gen.py /tmp/artifact.html docs/esp32s3-pcb-skice.html
# Prvi fajl je bez <html>/<head> (za objavljivanje kao artifact), drugi je pun HTML za otvaranje iz repoa.
# Tekst sa obrazloženjima: docs/esp32s3-pcb-istrazivanje.md.
import sys
from html import escape as E

# ---------------------------------------------------------------- pin mapa DevKitC-1
J1 = [
    ("3V3", "3V3 izlaz · spolja ≤ ~250 mA", "pwr"),
    ("3V3", "", "pwr"),
    ("RST", "+ EN na EXP (reset ESP-a)", "aux"),
    ("IO4", "T1 · NAZAD", "btn"),
    ("IO5", "T2 · OK", "btn"),
    ("IO6", "T3 · STOP", "btn"),
    ("IO7", "E-STOP (PC817)", "estop"),
    ("IO15", "STM NRST · preko 2N7002", "stm"),
    ("IO16", "STM BOOT0 · 470 Ω", "stm"),
    ("IO17", "UART1 TX → PA10 (D2)", "stm"),
    ("IO18", "UART1 RX ← PA9 (D8)", "stm"),
    ("IO8", "I2C0 SDA · ekran", "i2c"),
    ("IO3", "× strapping", "no"),
    ("IO46", "× strapping", "no"),
    ("IO9", "I2C0 SCL · ekran", "i2c"),
    ("IO10", "+ VBAT / analog (ADC1)", "aux"),
    ("IO11", "ENC A (CLK)", "enc"),
    ("IO12", "ENC B (DT)", "enc"),
    ("IO13", "ENC SW", "enc"),
    ("IO14", "Buzzer · PWM", "buz"),
    ("5V", "5V ulaz · preko diode", "pwr"),
    ("G", "GND", "no"),
]
J3 = [
    ("G", "GND", "no"),
    ("IO43", "× UART0 · USB-UART", "no"),
    ("IO44", "× UART0 · USB-UART", "no"),
    ("IO1", "+ AUX analog (ADC1) · EXP", "aux"),
    ("IO2", "+ AUX analog (ADC1) · EXP", "aux"),
    ("IO42", "+ LIDAR MOTOCTL · PWM", "u2"),
    ("IO41", "+ I2C1 SDA · senzori", "i2c"),
    ("IO40", "+ I2C1 SCL · senzori", "i2c"),
    ("IO39", "+ INT / XSHUT senzora", "i2c"),
    ("IO38", "× RGB LED (v1.1)", "no"),
    ("IO37", "× octal PSRAM", "no"),
    ("IO36", "× octal PSRAM", "no"),
    ("IO35", "× octal PSRAM", "no"),
    ("IO0", "× BOOT taster · strapping", "no"),
    ("IO45", "× strapping (VDD_SPI)", "no"),
    ("IO48", "UART2 RX · ⚠ v1.0: RGB LED", "u2"),
    ("IO47", "UART2 TX", "u2"),
    ("IO21", "NeoPixel · preko 74AHCT1G125", "neo"),
    ("IO20", "× USB D+", "no"),
    ("IO19", "× USB D−", "no"),
    ("G", "GND", "no"),
    ("G", "GND", "no"),
]


def pinmap():
    o = ['<svg viewBox="0 0 780 640" role="img" aria-labelledby="f1t">',
         '<title id="f1t">Raspored pinova ESP32-S3-DevKitC-1 sa funkcijama iz plana</title>',
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
         '<text x="380" y="420" class="t10 c-silk" text-anchor="middle">DevKitC-1</text>',
         '<text x="380" y="434" class="t9 c-silk" text-anchor="middle">pogled odozgo</text>',
         '<rect x="342" y="604" width="30" height="14" rx="3" class="metal"/>',
         '<rect x="388" y="604" width="30" height="14" rx="3" class="metal"/>',
         '<text x="380" y="634" class="t10 c-muted" text-anchor="middle">2 × USB-C</text>']
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


# ---------------------------------------------------------------- šema NRST / BOOT0 / UART
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


def schematic():
    o = ['<svg viewBox="0 0 760 500" role="img" aria-labelledby="f2t">',
         '<title id="f2t">Šema: NRST preko 2N7002, BOOT0 sa pull-down-om, UART sa rednim otpornicima, dva odvojena konektora</title>',
         '<text x="40" y="30" class="t11 c-muted b">ESP32-S3 (DevKitC-1)</text>',
         '<text x="584" y="30" class="t11 c-muted b" text-anchor="middle">J_CTRL · PH-3</text>',
         '<text x="640" y="30" class="t11 c-muted b">→ Nucleo</text>']
    # J_CTRL
    o.append('<rect x="560" y="42" width="48" height="108" rx="3" class="conn"/>')
    for yy, n in ((60, "1 GND"), (95, "2 NRST"), (130, "3 BOOT0")):
        o.append(f'<circle cx="560" cy="{yy}" r="3" class="pad"/>')
        o.append(f'<text x="567" y="{yy + 4}" class="t9 c-conn">{n}</text>')
    o.append('<text x="622" y="64" class="t10 c-ink">CN7-8 GND</text>')
    o.append('<text x="622" y="99" class="t10 c-ink">CN7-14 NRST (CN6-3)</text>')
    o.append('<text x="622" y="134" class="t10 c-ink">CN7-7 BOOT0</text>')
    o.append(wire("M560,60 H535 V66") + gnd(535, 66))
    # NRST
    o.append('<text x="40" y="137" class="t11 c-stm b">GPIO15</text>')
    o.append(wire("M100,133 H170") + res_h(170, 133, "R1 1 kΩ") + wire("M210,133 H380"))
    o.append(dot(300, 133) + wire("M300,133 V150") + res_v(300, 150, "R2 100 kΩ") + wire("M300,184 V196") + gnd(300, 196))
    o.append('<rect x="380" y="105" width="56" height="56" rx="4" class="sym"/>')
    o.append('<text x="408" y="129" class="t10 c-ink b" text-anchor="middle">Q1</text>')
    o.append('<text x="408" y="143" class="t9 c-ink" text-anchor="middle">2N7002</text>')
    o.append('<text x="372" y="128" class="t9 c-muted" text-anchor="end">G</text>')
    o.append('<text x="426" y="100" class="t9 c-muted">D</text><text x="426" y="174" class="t9 c-muted">S</text>')
    o.append(wire("M420,105 V95 H560") + wire("M420,161 V180") + gnd(420, 180))
    o.append('<text x="40" y="160" class="t9 c-muted">1 = reset (obrnuta logika)</text>')
    # BOOT0
    o.append('<text x="40" y="244" class="t11 c-stm b">GPIO16</text>')
    o.append(wire("M100,240 H170") + res_h(170, 240, "R3 470 Ω") + wire("M210,240 H520 V130 H560"))
    o.append(dot(470, 240) + wire("M470,240 V252") + res_v(470, 252, "R4 10 kΩ") + wire("M470,286 V296") + gnd(470, 296))
    o.append('<text x="40" y="267" class="t9 c-muted">1 = bootloader (samo za flešovanje)</text>')
    o.append('<text x="40" y="284" class="t9 c-muted">Nucleo ima svoj ~10 kΩ: zajedno ≈ 5 kΩ → 3,0 V na BOOT0</text>')
    # UART
    o.append('<line x1="40" y1="318" x2="720" y2="318" class="sep"/>')
    o.append('<text x="584" y="340" class="t11 c-muted b" text-anchor="middle">J_UART · PH-3</text>')
    o.append('<rect x="560" y="352" width="48" height="108" rx="3" class="conn"/>')
    for yy, n in ((370, "1 GND"), (405, "2 TX"), (440, "3 RX")):
        o.append(f'<circle cx="560" cy="{yy}" r="3" class="pad"/>')
        o.append(f'<text x="567" y="{yy + 4}" class="t9 c-conn">{n}</text>')
    o.append('<text x="622" y="374" class="t10 c-ink">GND</text>')
    o.append('<text x="622" y="409" class="t10 c-ink">PA10 · D2 (RX)</text>')
    o.append('<text x="622" y="444" class="t10 c-ink">PA9 · D8 (TX)</text>')
    o.append(wire("M560,370 H535 V376") + gnd(535, 376))
    o.append('<text x="40" y="409" class="t11 c-stm b">GPIO17 TX</text>')
    o.append(wire("M118,405 H170") + res_h(170, 405, "R5 470 Ω") + wire("M210,405 H560"))
    o.append('<text x="40" y="444" class="t11 c-stm b">GPIO18 RX</text>')
    o.append(wire("M118,440 H170") + res_h(170, 440, "R6 470 Ω") + wire("M210,440 H560"))
    o.append('<path d="M470,399 l10,6 l-10,6" class="wire"/>')
    o.append('<path d="M480,434 l-10,6 l10,6" class="wire"/>')
    o.append('<text x="40" y="480" class="t9 c-muted">R5, R6 kod ESP-a: GPIO18 kratko vuče liniju pri uključenju; ograničavaju struju i kad je jedna strana bez napajanja.</text>')
    o.append('</svg>')
    return "\n".join(o)


# ---------------------------------------------------------------- opcija A
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


def option_a():
    p1 = lambda i: 83.35 + (i - 1) * 12.7          # y pina i na letvici (5 px/mm)
    xl, xr = 322.85, 437.15
    o = ['<svg viewBox="0 0 760 470" role="img" aria-labelledby="fat">',
         '<title id="fat">Opcija A: nosač-ploča 100 × 63 mm sa DevKitC-1 u sredini i konektorima po ivicama</title>',
         '<defs>',
         '<pattern id="hdrL" x="316.5" y="77" width="12.7" height="12.7" patternUnits="userSpaceOnUse"><circle cx="6.35" cy="6.35" r="2.4" class="padf"/></pattern>',
         '<pattern id="hdrR" x="430.8" y="77" width="12.7" height="12.7" patternUnits="userSpaceOnUse"><circle cx="6.35" cy="6.35" r="2.4" class="padf"/></pattern>',
         '<pattern id="exp" x="452" y="62" width="17.5" height="22" patternUnits="userSpaceOnUse"><rect x="6" y="8" width="5" height="5" class="padf"/></pattern>',
         '</defs>',
         '<rect x="130" y="60" width="500" height="315" rx="10" class="mask"/>',
         '<rect x="326" y="60" width="108" height="80" class="keepout"/>',
         '<rect x="333" y="56" width="94" height="44" class="cut"/>',
         hole(148, 78), hole(612, 78), hole(148, 357), hole(612, 357)]
    # 5 V sabirnica (donji sloj)
    o.append('<path d="M262,331 V360 H573 V375 M495,360 V375" class="bus"/>')
    o.append('<path d="M300,313 H322.85 V337" class="bus"/>')
    o.append('<text x="380" y="352" class="t9 c-silk" text-anchor="middle">5 V · donji sloj</text>')
    # konektori, levo krilo
    o.append(conn(172, 60, 35, 30, '<circle cx="181" cy="75" r="5" class="screw"/><circle cx="198" cy="75" r="5" class="screw"/>'))
    o.append('<rect x="164" y="62" width="50" height="62" rx="4" class="zone"/>')
    o.append(conn(222, 60, 75, 28))
    o.append(conn(130, 97, 28, 40) + conn(130, 145, 28, 40) + conn(130, 193, 30, 62) + conn(130, 263, 30, 75))
    o.append(conn(172, 345, 37, 30) + conn(222, 338, 52, 37, '<rect x="230" y="350" width="14" height="16" rx="4" class="screw"/><rect x="252" y="350" width="14" height="16" rx="4" class="screw"/>'))
    # desno krilo
    o.append(conn(452, 62, 140, 44, '<rect x="452" y="62" width="140" height="44" fill="url(#exp)"/>'))
    o.append(conn(600, 118, 30, 75) + conn(600, 203, 30, 75))
    o.append(conn(452, 345, 87, 30) + conn(548, 345, 50, 30))
    # delovi
    o.append(block(168, 96, 42, 16, ["PC817"]))
    o.append(block(222, 96, 84, 16, ["10k · 100nF ×3"]))
    o.append(block(166, 128, 120, 16, ["2N7002 · 470Ω · 10k"]))
    o.append(block(166, 158, 120, 16, ["470Ω ×2 · LED"]))
    o.append(block(166, 214, 120, 16, ["2k2 pull-up · ESD"]))
    o.append(block(166, 272, 120, 16, ["10k/10nF · ESD"]))
    o.append(block(166, 302, 44, 16, ["FET+D"]))
    o.append(block(220, 296, 90, 34, ["PTC 3A · TVS", "470µF · dioda"]))
    o.append(block(490, 150, 103, 16, ["4k7 · ESD · 100nF"]))
    o.append(block(490, 235, 103, 16, ["TCA9548A (opc.)"]))
    o.append(block(490, 296, 103, 16, ["74AHCT1G125 · PTC"]))
    o.append(block(452, 318, 48, 16, ["PTC 1A"]))
    # DevKitC preko
    o.append('<rect x="316.5" y="60" width="127" height="314" rx="3" class="devkit"/>')
    o.append('<rect x="316.5" y="77" width="12.7" height="279.4" class="hdr"/><rect x="316.5" y="77" width="12.7" height="279.4" fill="url(#hdrL)"/>')
    o.append('<rect x="430.8" y="77" width="12.7" height="279.4" class="hdr"/><rect x="430.8" y="77" width="12.7" height="279.4" fill="url(#hdrR)"/>')
    o.append('<rect x="335" y="60" width="90" height="32" class="modpcb"/>')
    o.append('<path d="M343,84 h4 v-14 h9 v14 h9 v-14 h9 v14 h9 v-14 h9 v14 h9 v-14 h9 v14 h4" class="ant"/>')
    o.append('<rect x="335" y="92" width="90" height="95" rx="2" class="shield"/>')
    o.append('<text x="380" y="136" class="t9 c-ink" text-anchor="middle">ESP32-S3</text><text x="380" y="149" class="t9 c-ink" text-anchor="middle">N16R8</text>')
    o.append('<text x="380" y="270" class="t10 c-silk" text-anchor="middle">DevKitC-1</text><text x="380" y="283" class="t9 c-silk" text-anchor="middle">na letvicama 2×22</text>')
    o.append('<rect x="333" y="366" width="34" height="16" rx="4" class="metal"/><rect x="393" y="366" width="34" height="16" rx="4" class="metal"/>')
    # vazdušne veze
    for i in (4, 5, 6):
        o.append(air(xl, p1(i), 264, 104))
    o.append(air(xl, p1(7), 210, 104))
    for i in (8, 9):
        o.append(air(xl, p1(i), 254, 136))
    for i in (10, 11):
        o.append(air(xl, p1(i), 254, 166))
    for i in (12, 15):
        o.append(air(xl, p1(i), 254, 222))
    for i in (17, 18, 19):
        o.append(air(xl, p1(i), 286, 280))
    o.append(air(xl, p1(20), 210, 310))
    for i in (4, 5):
        o.append(air(xr, p1(i), 500, 106))
    for i in (7, 8, 9):
        o.append(air(xr, p1(i), 505, 158))
    for i in (6, 16, 17):
        o.append(air(xr, p1(i), 476, 318))
    o.append(air(xr, p1(18), 505, 304))
    # natpisi spolja
    lab = [(189.5, 48, "E-STOP", "middle"), (259.5, 48, "TASTERI", "middle"), (522, 48, "PROŠIRENJE 2×8", "middle"),
           (122, 121, "STM CTRL", "end"), (122, 169, "STM UART", "end"), (122, 228, "OLED · I2C0", "end"),
           (122, 304, "ENKODER", "end"), (638, 159, "SENZORI", "start"), (638, 172, "I2C1", "start"),
           (638, 244, "SENZORI", "start"), (638, 257, "I2C1", "start"),
           (190.5, 394, "BUZZER", "middle"), (248, 394, "5 V ULAZ", "middle"),
           (495.5, 394, "LIDAR · XH-6", "middle"), (573, 394, "NEOPIXEL", "middle")]
    for x, y, t, a in lab:
        o.append(f'<text x="{x}" y="{y}" class="t10 c-ink b" text-anchor="{a}">{E(t)}</text>')
    o.append('<text x="380" y="18" class="t10 c-muted" text-anchor="middle">antena iznad izreza · bez bakra na oba sloja</text>')
    o.append('<line x1="380" y1="23" x2="380" y2="54" class="lead"/>')
    o.append('<text x="189.5" y="121" class="t9 c-estop" text-anchor="middle">zona bat.</text>')
    o.append('<text x="380" y="416" class="t10 c-muted" text-anchor="middle">USB-C ka ivici · prolaz za utikač bez visokih delova</text>')
    o.append('<path d="M130,440 V450 M630,440 V450 M130,445 H630" class="dim"/><text x="380" y="462" class="t10 c-muted" text-anchor="middle">100 mm</text>')
    o.append('<path d="M690,60 H700 M690,375 H700 M695,60 V375" class="dim"/><text x="708" y="221" class="t10 c-muted">63 mm</text>')
    o.append('</svg>')
    return "\n".join(o)


# ---------------------------------------------------------------- opcija B
def option_b():
    o = ['<svg viewBox="0 0 760 330" role="img" aria-labelledby="fbt">',
         '<title id="fbt">Opcija B: nosač-ploča i panel sa ekranom, tasterima i enkoderom, spojeni jednim trakastim kablom</title>',
         '<rect x="30" y="60" width="280" height="220" rx="8" class="mask"/>',
         '<rect x="136" y="56" width="68" height="30" class="cut"/>',
         '<rect x="125.5" y="60" width="89" height="219" rx="3" class="devkit"/>',
         '<rect x="138.5" y="60" width="63" height="21" class="modpcb"/>',
         '<rect x="138.5" y="81" width="63" height="68" rx="2" class="shield"/>',
         '<rect x="125.5" y="72" width="9" height="196" class="hdr"/><rect x="205.5" y="72" width="9" height="196" class="hdr"/>',
         '<text x="170" y="210" class="t9 c-silk" text-anchor="middle">DevKitC-1</text>']
    o.append(conn(45, 60, 26, 22) + conn(30, 100, 20, 28) + conn(30, 140, 20, 28) + conn(60, 250, 36, 30))
    o.append(conn(279, 70, 31, 98) + conn(279, 180, 31, 52) + conn(225, 255, 61, 25))
    o.append(block(56, 186, 60, 30, ["PTC · TVS", "470 µF"]))
    o.append(block(222, 100, 50, 30, ["AHCT", "125"]))
    for x, y, t, a in [(58, 50, "E-STOP", "middle"), (24, 118, "STM CTRL", "end"), (24, 158, "STM UART", "end"),
                       (78, 298, "5 V ULAZ", "middle"), (256, 298, "LIDAR", "middle")]:
        o.append(f'<text x="{x}" y="{y}" class="t10 c-ink b" text-anchor="{a}">{E(t)}</text>')
    o.append('<text x="294" y="122" class="t9 c-conn" text-anchor="middle" transform="rotate(-90 294 119)">UI 2×8</text>')
    o.append('<text x="294" y="210" class="t9 c-conn" text-anchor="middle" transform="rotate(-90 294 206)">SENZ.</text>')
    o.append('<text x="170" y="318" class="t10 c-muted" text-anchor="middle">NOSAČ · ~80 × 63 mm</text>')
    # traka
    o.append('<path d="M310,119 C 324,119 318,180 334,180" class="ribbon"/>')
    o.append('<text x="322" y="96" class="t9 c-muted" text-anchor="middle">16 žila</text>')
    # panel
    o.append('<rect x="330" y="100" width="420" height="158" rx="8" class="mask"/>')
    o.append('<rect x="334" y="131" width="31" height="98" rx="2" class="back"/>')
    o.append('<rect x="352" y="115" width="210" height="128" rx="4" class="oled"/>')
    o.append('<rect x="364" y="127" width="186" height="96" rx="2" class="oledscr"/>')
    o.append('<text x="374" y="150" class="t11 c-oled">PROVERA  0:87</text><text x="374" y="170" class="t11 c-oled">&gt; kamenolomi</text><text x="374" y="190" class="t11 c-oled">  zuta  STM OK</text>')
    o.append('<circle cx="608" cy="160" r="35" class="knob"/><circle cx="608" cy="160" r="22" class="knob2"/><line x1="608" y1="141" x2="608" y2="152" class="knobmark"/>')
    o.append('<circle cx="608" cy="232" r="17" class="buzz"/><circle cx="608" cy="232" r="4" class="drill"/>')
    o.append('<circle cx="680" cy="136" r="16" class="f-estop"/><circle cx="680" cy="178" r="16" class="f-buz"/><circle cx="680" cy="220" r="16" class="f-btn"/>')
    o.append('<text x="702" y="140" class="t9 c-silk">STOP</text>')
    o.append(conn(470, 100, 37, 12))
    o.append('<text x="488.5" y="95" class="t9 c-ink b" text-anchor="middle">NEO</text>')
    o.append('<text x="349.5" y="246" class="t9 c-silk" text-anchor="middle">IDC</text>')
    o.append('<text x="540" y="282" class="t10 c-muted" text-anchor="middle">PANEL · ~120 × 45 mm (IDC na poleđini)</text>')
    o.append('<text x="702" y="182" class="t9 c-silk">NAZAD</text><text x="702" y="224" class="t9 c-silk">OK</text>')
    o.append('</svg>')
    return "\n".join(o)


# ---------------------------------------------------------------- opcija C
def option_c():
    o = ['<svg viewBox="0 0 520 340" role="img" aria-labelledby="fct">',
         '<title id="fct">Opcija C: ESP32-S3-WROOM-1 zalemljen na ploču 70 × 50 mm</title>',
         '<rect x="100" y="50" width="350" height="250" rx="10" class="mask"/>',
         '<rect x="170" y="50" width="120" height="34" class="keepout"/>',
         '<rect x="185" y="30" width="90" height="30" class="modpcb"/>',
         '<path d="M193,54 h4 v-14 h9 v14 h9 v-14 h9 v14 h9 v-14 h9 v14 h9 v-14 h9 v14 h4" class="ant"/>',
         '<rect x="185" y="60" width="90" height="98" rx="2" class="shield"/>',
         '<text x="230" y="106" class="t9 c-ink" text-anchor="middle">WROOM-1</text><text x="230" y="119" class="t9 c-ink" text-anchor="middle">N16R8</text>',
         '<rect x="207" y="272" width="45" height="34" rx="6" class="metal"/>',
         hole(118, 68), hole(432, 68), hole(118, 282), hole(432, 282)]
    o.append(block(196, 236, 68, 28, ["USBLC6-2", "ESD"]))
    o.append(block(116, 236, 72, 28, ["3V3 1 A", "regulator"]))
    o.append(block(272, 236, 76, 28, ["EN 10k/1µF", "BOOT · RST"]))
    o.append(block(116, 196, 72, 28, ["5 V ulaz", "PTC · TVS"]))
    o.append(block(196, 176, 68, 28, ["NRST FET", "BOOT0 R"]))
    o.append(block(272, 176, 76, 28, ["NeoPixel", "AHCT125"]))
    for (y, h, t) in ((88, 26, "CTRL"), (120, 26, "UART"), (152, 34, "OLED"), (192, 40, "ENK.")):
        o.append(conn(100, y, 18, h) + f'<text x="94" y="{y + h / 2 + 3.5}" class="t9 c-ink b" text-anchor="end">{t}</text>')
    for (y, h, t) in ((88, 40, "SENZ."), (136, 46, "LIDAR"), (190, 26, "NEO"), (222, 22, "BUZ")):
        o.append(conn(432, y, 18, h) + f'<text x="456" y="{y + h / 2 + 3.5}" class="t9 c-ink b">{t}</text>')
    o.append(conn(118, 50, 34, 18) + '<text x="135" y="44" class="t9 c-ink b" text-anchor="middle">E-STOP</text>')
    o.append(conn(306, 50, 44, 18) + '<text x="328" y="44" class="t9 c-ink b" text-anchor="middle">TASTERI</text>')
    o.append(conn(360, 50, 64, 18) + '<text x="392" y="44" class="t9 c-ink b" text-anchor="middle">EXP</text>')
    o.append('<text x="275" y="326" class="t10 c-muted" text-anchor="middle">~70 × 50 mm · USB-C na ivici</text>')
    o.append('</svg>')
    return "\n".join(o)


# ---------------------------------------------------------------- opcija D
def option_d():
    o = ['<svg viewBox="0 0 560 360" role="img" aria-labelledby="fdt">',
         '<title id="fdt">Opcija D: matična ploča sa Nucleo-om i DevKitC-om, ESP-STM veze su vodovi</title>',
         '<rect x="40" y="30" width="480" height="300" rx="10" class="mask"/>',
         '<rect x="60" y="55" width="210" height="248" rx="6" class="nucleo"/>',
         '<rect x="66" y="105" width="12" height="145" class="hdr"/><rect x="252" y="105" width="12" height="145" class="hdr"/>',
         '<text x="165" y="170" class="t10 c-ink b" text-anchor="middle">NUCLEO-F401RE</text>',
         '<text x="165" y="185" class="t9 c-muted" text-anchor="middle">u ženskim morpho letvicama</text>',
         '<rect x="430" y="12" width="76" height="188" rx="3" class="devkit"/>',
         '<rect x="440" y="12" width="56" height="20" class="modpcb"/>',
         '<rect x="440" y="32" width="56" height="54" rx="2" class="shield"/>',
         '<rect x="430" y="22" width="8" height="170" class="hdr"/><rect x="498" y="22" width="8" height="170" class="hdr"/>',
         '<text x="468" y="150" class="t9 c-silk" text-anchor="middle">DevKitC</text>']
    o.append('<path d="M264,120 H430 M264,132 H430 M264,144 H430 M264,156 H430" class="trace"/>')
    o.append('<text x="347" y="112" class="t9 c-silk" text-anchor="middle">UART · NRST · BOOT0</text>')
    o.append(block(290, 180, 120, 22, ["drajveri motora"]))
    o.append(block(290, 208, 120, 22, ["enkoderi točkova"]))
    o.append(block(290, 236, 120, 22, ["IR ×8 · činč"]))
    o.append(block(290, 264, 120, 22, ["AX servo (USART6)"]))
    o.append(block(426, 214, 84, 34, ["UI · senzori", "lidar · NEO"]))
    o.append(conn(426, 300, 40, 30) + conn(472, 300, 40, 30))
    o.append('<text x="280" y="350" class="t10 c-muted" text-anchor="middle">~160 × 100 mm · logika i snaga na istoj ploči</text>')
    o.append('</svg>')
    return "\n".join(o)


# ---------------------------------------------------------------- strana
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

LEGEND = "".join(
    f'<span><i style="background:var(--g-{g})"></i>{t}</span>' for g, t in [
        ("stm", "STM32 (UART, NRST, BOOT0)"), ("estop", "E-STOP"), ("btn", "tasteri"), ("i2c", "I2C"),
        ("enc", "enkoder"), ("buz", "buzzer"), ("neo", "NeoPixel"), ("u2", "UART2 / lidar"),
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
  <div class="eyebrow">Robot-2027 · ESP32 · nacrt 9. 11. 2026</div>
  <h1>ESP32-S3 ploča: pinovi, konektori i raspored</h1>
  <p class="lede">Provera plana pinova sa slike „ESP32-S3 · povezivanje" prema kodu u <code>ESP32/</code> i planu
  <code>docs/faza4-esp32s3-lidar.md</code>, šta treba dodati na ploču, NRST i BOOT0 na odvojenom konektoru i četiri
  opcije rasporeda. Ceo tekst sa obrazloženjima je u <code>docs/esp32s3-pcb-istrazivanje.md</code>.</p>
  <nav class="toc" aria-label="Sadržaj">
    <a href="#ukratko">Ukratko</a><a href="#pinovi">Pinovi</a><a href="#nrst">NRST i BOOT0</a>
    <a href="#blokovi">Blokovi</a><a href="#napajanje">Napajanje</a><a href="#konektori">Konektori</a>
    <a href="#raspored">Raspored ploče</a><a href="#smernice">Smernice</a><a href="#softver">Softver</a>
    <a href="#pitanja">Pitanja</a>
  </nav>
</header>

<section id="ukratko">
  <h2><span class="sec">01</span>Ukratko</h2>
  <div class="verdict">
    <div><span class="k">Izbor pinova</span><span class="v">Dobar, ostaje kako je</span>
      <span>Izbegnuti strapping, USB, UART0 i octal PSRAM. Sve od korisničkog interfejsa je na J1, redom.</span></div>
    <div><span class="k">Mora da se promeni</span><span class="v">NRST preko MOSFET-a</span>
      <span>GPIO15 daje impuls od ~60 µs pri uključenju i resetovao bi STM32.</span></div>
    <div><span class="k">Fali na slici</span><span class="v">Lidar MOTOCTL, I2C1, INT</span>
      <span>Lidar iz faze 4 nema PWM pin; ToF senzori traže XSHUT.</span></div>
    <div><span class="k">Raspored za v1</span><span class="v">Nosač 100 × 63 mm</span>
      <span>DevKitC na letvicama, antena iznad izreza, USB na ivici. Modul na ploči tek za v2.</span></div>
  </div>
  <div class="tbl"><table>
    <thead><tr><th>Šta</th><th>Zašto</th><th></th></tr></thead>
    <tbody>
      <tr><td>NRST preko 2N7002</td><td>Impuls na GPIO15 pri uključenju ESP-a resetuje STM32; ESP bez napajanja drži NRST nisko.</td><td><span class="chip mora">MORA</span></td></tr>
      <tr><td>E-STOP: otpornik i dioda</td><td>LED u PC817: najviše 50 mA i 6 V obrnuto; bez otpornika izgori na naponu baterije.</td><td><span class="chip mora">MORA</span></td></tr>
      <tr><td>NeoPixel: 74AHCT1G125</td><td>WS2812 traži ≥ 3,5 V na DIN-u pri 5 V; ESP daje 3,3 V.</td><td><span class="chip mora">MORA</span></td></tr>
      <tr><td>Buzzer: pull-down i dioda</td><td>Bez pull-down-a zuji pri pokretanju; bez diode indukcioni napon kvari tranzistor.</td><td><span class="chip mora">MORA</span></td></tr>
      <tr><td>5 V ulaz: zaštita i dioda ka DevKitC</td><td>USB, 5V pin i 3V3 pin su po Espressif-u međusobno isključivi izvori.</td><td><span class="chip mora">MORA</span></td></tr>
      <tr><td>Konektori bez opasne zamene</td><td>Tri XH-2 na slici: E-STOP kabl u konektoru za buzzer pušta napon baterije na 5 V.</td><td><span class="chip mora">MORA</span></td></tr>
      <tr><td>Lidar MOTOCTL (GPIO42), XH-6</td><td>RPLIDAR A2 traži PWM za motor; konektor na slici ga nema.</td><td><span class="chip prep">PREPORUKA</span></td></tr>
      <tr><td>470 Ω na UART-u ka STM32</td><td>GPIO18 pri uključenju kratko vuče liniju protiv TX-a STM32.</td><td><span class="chip prep">PREPORUKA</span></td></tr>
      <tr><td>I2C1 za senzore + INT/XSHUT</td><td>Kvar kabla senzora ne obara ekran; više ToF senzora sa istom adresom.</td><td><span class="chip prep">PREPORUKA</span></td></tr>
      <tr><td>Konektor za proširenje 2×8</td><td>Slobodni pinovi za CAN, servo ploču, kameru, bez nove ploče.</td><td><span class="chip prep">PREPORUKA</span></td></tr>
      <tr><td>VBAT na GPIO10 ili INA3221</td><td>Baterija je u planu (PROVERA, ROBOT), na slici je nema.</td><td><span class="chip opc">OPCIJA</span></td></tr>
    </tbody></table></div>
</section>

<section id="pinovi">
  <h2><span class="sec">02</span>Pinovi na DevKitC-1 N16R8</h2>
  <p>Pinovi sa slike, kako stvarno stoje na letvicama J1 i J3 (od antene ka USB-u). Sa „+" su predloženi novi, sa
  „×" oni koji se ne koriste. Pinovi za tastere, E-STOP, STM32, ekran, enkoder i buzzer su na J1 istim redom kao
  funkcije, pa se konektori poređaju oko leve strane ploče bez ukrštanja.</p>
  <figure>
    <div class="fig">{pinmap()}</div>
    <div class="legend">{LEGEND}</div>
    <figcaption><b>Slika 1.</b> Raspored J1 i J3 iz Espressif uputstva za DevKitC-1 v1.1. GPIO48 na v1.0 ploči vozi RGB LED,
    a GPIO47 i 48 su 1,8 V kod modula sa 1,8 V memorijom (R8V, R16V); kod N16R8 su 3,3 V.</figcaption>
  </figure>
  <div class="tbl"><table>
    <thead><tr><th>GPIO</th><th>Ocena</th><th>Napomena</th></tr></thead>
    <tbody>
      <tr><td>15 (NRST)</td><td><span class="chip mora">PROMENITI</span></td><td>XTAL_32K_P: impuls u nulu ~60 µs pri uključenju; STM32 propušta impuls duži od ~300 ns. Preko MOSFET-a je bezopasan.</td></tr>
      <tr><td>18 (UART RX)</td><td><span class="chip prep">OTPORNIK</span></td><td>Impuls u 0 ili 1 pri uključenju: pin kratko gura liniju protiv TX-a STM32.</td></tr>
      <tr><td>47, 48 (UART2)</td><td><span class="chip prep">PROVERITI</span></td><td>Na DevKitC-1 v1.0 je RGB LED na 48. Domen VDD_SPI: ne menjati modul na R8V/R16V.</td></tr>
      <tr><td>16, 17, 14</td><td><span class="chip opc">OK</span></td><td>Impuls u nulu je za BOOT0, UART TX (COBS preživi) i buzzer bezbedno stanje.</td></tr>
      <tr><td>4-9, 11-13, 21</td><td><span class="chip opc">OK</span></td><td>ADC1 pinovi 4-9 su digitalni; za analogno ostaju 1, 2, 10 (ADC2 se deli sa WiFi-jem).</td></tr>
    </tbody></table></div>
</section>

<section id="nrst">
  <h2><span class="sec">03</span>NRST i BOOT0 na odvojenom konektoru</h2>
  <p>Odvojen konektor je dobra odluka: BlackPill koristi samo UART, izvučen kabl znači da ESP ne može da resetuje pogon
  ni greškom u meču, a kablovi mogu da idu na različita mesta na Nucleo-u. Dva konektora PH-3 sa GND na pinu 1;
  zamena kablova ne kvari ništa, samo ne radi.</p>
  <figure>
    <div class="fig">{schematic()}</div>
    <figcaption><b>Slika 2.</b> GPIO15 = 1 → Q1 provodi → reset. Kad se ESP restartuje ili nema napajanje, R2 drži Q1 ugašen
    i STM32 radi. Druga mogućnost bez promene softvera: 74LVC1G07 sa RC filtrom 10 kΩ / 100 nF na ulazu.</figcaption>
  </figure>
  <div class="callout warn"><p><b>Softver:</b> <code>match.StmReset</code> i <code>stmflash</code> sada spuštaju NRST na 0
  (open-drain). Sa MOSFET-om logika je obrnuta: predlog <code>STM_NRST_ACTIVE = 1</code> u board fajlu. Bootloader
  STM32 (AN2606) prepoznaje brzinu do 115200, pa kad <code>UART_BAUD</code> pređe na 921600, flešovanje mora da
  koristi 115200.</p></div>
</section>

<section id="blokovi">
  <h2><span class="sec">04</span>Blok po blok</h2>
  <div class="tbl"><table>
    <thead><tr><th>Blok</th><th>Na ploči</th><th>Napomena</th></tr></thead>
    <tbody>
      <tr><td>E-STOP</td><td>R redno sa LED-om, 1N4148 suprotno paralelno, izlaz 10 kΩ na 3V3 + 100 nF</td><td>R = (Vbat − 1,2 V) / 5 mA: 3S 2,2 kΩ, 4S 3,3 kΩ, 6S 4,7 kΩ 0,25 W. Prekid kabla = „pritisnut" (bezbedno).</td></tr>
      <tr><td>Buzzer</td><td>AO3400A ili 2N7002, 100 Ω u gejtu, 100 kΩ na GND, 1N4148 preko buzzera</td><td>Sa BC547: 1 kΩ u bazi, 10 kΩ baza-GND. PWM na rezonanci (2,7 ili 4 kHz).</td></tr>
      <tr><td>NeoPixel</td><td>74AHCT1G125 na 5 V, 330 Ω, 470-1000 µF, PTC 1,5 A</td><td>60 mA po LED-u na beloj: 16 LED = 1 A.</td></tr>
      <tr><td>I2C0 (ekran)</td><td>2,2 kΩ pull-up, kratak kabl</td><td>S3 radi do 800 kbit/s, ne 1 MHz. Konektor nikad sa 5 V.</td></tr>
      <tr><td>I2C1 (senzori)</td><td>GPIO41/40, 4,7 kΩ, INT/XSHUT na GPIO39, mesto za TCA9548A</td><td>VL53L0X/L1X svi na 0x29.</td></tr>
      <tr><td>Tasteri</td><td>10 kΩ pull-up, 1 kΩ redno, 100 nF</td><td>Interni pull-up je ~45 kΩ. STOP reaguje na pritisak, smetnja ne sme da ga „pritisne".</td></tr>
      <tr><td>Enkoder</td><td>10 kΩ redno + 10 nF na A i B, mesto za 10 kΩ pull-up</td><td>KY-040 ima svoje pull-up-ove. Redni otpornik štiti kontakt.</td></tr>
      <tr><td>UART2 / lidar</td><td>XH-6 sa MOTOCTL (GPIO42), 220-470 Ω redno, PTC 1 A + 100 µF</td><td>A2: 5 V, TX/RX 3,3 V, MOTOCTL aktivno visoko, PWM 20-25 kHz.</td></tr>
      <tr><td>Svi spoljni signali</td><td>100 Ω-1 kΩ redno kod konektora, ESD diode gde ruke dolaze, 100 nF na napajanju konektora</td><td>Motori i dugi kablovi.</td></tr>
    </tbody></table></div>
  <h3>Konektor za proširenje (2×8, sa ključem)</h3>
  <pre class="code"> 1 GND            2 GND
 3 3V3            4 5V (PTC 1 A)
 5 I2C1 SDA (41)  6 I2C1 SCL (40)
 7 GPIO1 (ADC1)   8 GPIO2 (ADC1)
 9 GPIO39        10 GPIO10 (ADC1, ako nije VBAT)
11 UART2 TX (47) 12 UART2 RX (48)
13 GPIO42        14 GPIO38 (kratkospojnik, bez RGB LED-a)
15 EN (reset)    16 GND</pre>
</section>

<section id="napajanje">
  <h2><span class="sec">05</span>Napajanje</h2>
  <figure>
<pre class="mermaid">
flowchart LR
  BAT["Baterija"] --> ES["E-STOP"] --> MOT["Motori i aktuatori"]
  ES -. "E-STOP+ / E-STOP−" .-> OPT["PC817 → GPIO7"]
  BAT --> DCDC["DC-DC 5 V, najmanje 3 A"]
  DCDC --> IN["PWR_IN: polaritet, TVS, PTC 3 A, 470 µF"]
  IN --> D1["Schottky ili idealna dioda"] --> DK["DevKitC 5V → LDO 3V3"]
  DK --> L3["ESP32-S3, OLED, enkoder, tasteri"]
  IN --> P1["PTC 1,5 A"] --> NEO["NeoPixel"]
  IN --> P2["PTC 1 A"] --> LID["Lidar / UART2 5 V"]
  IN --> BZ["Buzzer"]
  IN -. "opcija" .-> AUX["3V3_AUX LDO 600 mA"] --> SEN["I2C1 senzori, UART2 3V3"]
</pre>
    <figcaption><b>Slika 3.</b> Dioda ka DevKitC-u: kad je priključen samo USB, ne napaja NeoPixel i lidar; kad je
    priključena baterija, 5 V ne ide nazad u USB.</figcaption>
  </figure>
  <div class="tbl"><table>
    <thead><tr><th>Potrošač</th><th>Tipično (5 V)</th><th>Najviše</th><th>Napomena</th></tr></thead>
    <tbody>
      <tr><td>ESP32-S3 + PSRAM</td><td>120 mA</td><td>500 mA</td><td>WiFi slanje do ~350 mA na 3,3 V</td></tr>
      <tr><td>OLED</td><td>20 mA</td><td>40 mA</td><td></td></tr>
      <tr><td>NeoPixel 12-16 LED</td><td>100-200 mA</td><td>0,7-1 A</td><td>softver ograničava svetlinu</td></tr>
      <tr><td>Lidar RPLIDAR A2</td><td>~450 mA</td><td>~600 mA + start</td><td>proveriti datasheet</td></tr>
      <tr><td>Buzzer</td><td>30 mA</td><td>60 mA</td><td></td></tr>
      <tr><td>Senzori I2C</td><td>50 mA</td><td>100 mA</td><td>na 3,3 V</td></tr>
      <tr><td>Kamera (opciono)</td><td>150-300 mA</td><td>400 mA</td><td></td></tr>
      <tr><td><b>Ukupno</b></td><td><b>~1 A</b></td><td><b>2,5-3 A</b></td><td>DC-DC ≥ 3 A, bolje 5 A</td></tr>
    </tbody></table></div>
</section>

<section id="konektori">
  <h2><span class="sec">06</span>Konektori</h2>
  <div class="callout"><p><b>Pravilo:</b> konektori istog tipa i broja pinova imaju napajanje na istim pozicijama (ili ga
  nemaju), pin 1 je uvek GND. Pogrešan kabl tada menja samo signale. Napajanje i E-STOP (napon baterije) idu na
  konektore drugog tipa.</p></div>
  <ul class="list">
    <li>Na slici su tri XH-2: E-STOP kabl u konektoru za buzzer pušta napon baterije na 5 V liniju ESP-a.</li>
    <li>Enkoder (XH-5) u konektoru za UART2: SW pin dobija 5 V, pritisak na dugme pravi kratak spoj.</li>
    <li>Tasteri (XH-4) u I2C konektoru: T3 je na 3V3, pritisak kratko spaja 3V3 sa GND.</li>
  </ul>
  <div class="tbl"><table>
    <thead><tr><th>Konektor</th><th>Tip</th><th>Pinovi</th></tr></thead>
    <tbody>
      <tr><td>PWR_IN</td><td>XT30 ili stezaljka 5,08</td><td>+5V, GND</td></tr>
      <tr><td>ESTOP</td><td>stezaljka 3,5 mm (ili JST-VH)</td><td>E-STOP+, E-STOP−</td></tr>
      <tr><td>STM_UART</td><td>JST-PH 3</td><td>1 GND · 2 TX→PA10 · 3 RX←PA9</td></tr>
      <tr><td>STM_CTRL</td><td>JST-PH 3</td><td>1 GND · 2 NRST · 3 BOOT0</td></tr>
      <tr><td>OLED (I2C0)</td><td>XH-4</td><td>1 GND · 2 3V3 · 3 SCL · 4 SDA</td></tr>
      <tr><td>TASTERI</td><td>XH-5</td><td>1 GND · 2 3V3 · 3 T1 · 4 T2 · 5 T3</td></tr>
      <tr><td>ENKODER</td><td>XH-5</td><td>1 GND · 2 3V3 · 3 SW · 4 B · 5 A</td></tr>
      <tr><td>SENZORI ×2</td><td>XH-5</td><td>1 GND · 2 3V3 · 3 SCL · 4 SDA · 5 INT</td></tr>
      <tr><td>BUZZER</td><td>XH-2</td><td>1 BUZ− · 2 +5V</td></tr>
      <tr><td>NEOPIXEL</td><td>XH-3</td><td>1 GND · 2 +5V · 3 DIN</td></tr>
      <tr><td>LIDAR / UART2</td><td>XH-6</td><td>1 GND · 2 5V · 3 TX · 4 RX · 5 MOTOCTL · 6 3V3</td></tr>
      <tr><td>PROŠIRENJE</td><td>kutijasti 2×8</td><td>vidi blok 04</td></tr>
    </tbody></table></div>
</section>

<section id="raspored">
  <h2><span class="sec">07</span>Raspored ploče</h2>
  <div class="opt">
    <span class="tag">Opcija A · preporuka za v1</span>
    <h3>Nosač-ploča sa DevKitC-1 u sredini</h3>
    <figure>
      <div class="fig">{option_a()}</div>
      <figcaption><b>Slika 4.</b> 5 px = 1 mm. Konektori levo prate redosled pinova na J1, desno na J3. Isprekidane linije su
      veze (ne vodovi), pravougaonici sa isprekidanom ivicom su grupe delova. Pinovi 1-4 letvica su pored antene, pa
      se ploča ne skraćuje ispod antene nego dobija izrez između letvica.</figcaption>
    </figure>
    <div class="pc">
      <div><h4>Za</h4><ul><li>DevKitC se menja za minut, USB za razvoj ostaje</li><li>najmanje rizika za prvu ploču</li><li>ispod 100 × 100 mm (najjeftinija izrada)</li></ul></div>
      <div><h4>Protiv</h4><ul><li>visina ~20 mm sa letvicama</li><li>treba držač protiv vibracija (vezica ili klin)</li><li>sve od korisničkog interfejsa ide kablovima</li></ul></div>
    </div>
  </div>
  <div class="two">
    <div class="opt">
      <span class="tag">Opcija B · ako je UI na jednom panelu</span>
      <h3>Nosač + panel, jedan trakasti kabl</h3>
      <figure><div class="fig">{option_b()}</div>
      <figcaption><b>Slika 5.</b> 16 žila: 5V ×2, GND ×3, 3V3, SDA, SCL, T1-T3, ENC A/B/SW, BUZ, NEO DIN (5 V posle AHCT-a).</figcaption></figure>
      <div class="pc">
        <div><h4>Za</h4><ul><li>jedan kabl umesto pet</li><li>tasteri i enkoder zalemljeni, bez letećih žica</li></ul></div>
        <div><h4>Protiv</h4><ul><li>dve ploče</li><li>zavisi od mehanike panela</li></ul></div>
      </div>
    </div>
    <div class="row">
      <figure><div class="fig">{option_c()}</div></figure>
      <div class="side opt">
        <span class="tag">Opcija C · za v2</span>
        <h3>Modul WROOM-1 zalemljen na ploču</h3>
        <p class="cap"><b>Slika 6.</b> Nativni USB (bez USB-UART čipa), sopstveni 3V3 regulator, EN RC (10 kΩ / 1 µF), BOOT i RESET tasteri, ESD na USB-u.</p>
        <div class="pc">
          <div><h4>Za</h4><ul><li>najmanja i najotpornija</li><li>nema letvica</li></ul></div>
          <div><h4>Protiv</h4><ul><li>više projektovanja (USB, regulator, strapping)</li><li>kvar modula = lemljenje</li></ul></div>
        </div>
      </div>
    </div>
    <div class="row">
      <figure><div class="fig">{option_d()}</div></figure>
      <div class="side opt">
        <span class="tag">Opcija D · za razgovor</span>
        <h3>Matična ploča: Nucleo + ESP</h3>
        <p class="cap"><b>Slika 7.</b> Nucleo u ženskim morpho letvicama, DevKitC pored. UART, NRST i BOOT0 su vodovi na ploči.</p>
        <div class="pc">
          <div><h4>Za</h4><ul><li>nema kablova ESP-STM32</li></ul></div>
          <div><h4>Protiv</h4><ul><li>velika ploča, logika i snaga zajedno</li><li>deo je ploča pogona; ne slaže se sa odvojenim NRST konektorom</li></ul></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section id="smernice">
  <h2><span class="sec">08</span>Smernice za crtanje</h2>
  <ul class="list">
    <li><b>Antena:</b> ni bakra ni delova ispod antene i ~15 mm oko nje, na oba sloja; najbolje izrez između letvica (~19 mm). U robotu: gornji nivo, dalje od baterije, motora i metala; za metalno kućište varijanta sa U.FL antenom.</li>
    <li><b>Masa:</b> donji sloj ceo GND (osim ispod antene), gornji razliven GND sa vijama na ~10 mm.</li>
    <li><b>5 V:</b> glavni vod ≥ 1,5 mm (3 A), grane od 1 A ≥ 0,5 mm.</li>
    <li><b>E-STOP zona:</b> u ćošku, ≥ 2 mm do ostalog bakra, bez razlivenog bakra ispod optokaplera između strana.</li>
    <li><b>Letvice:</b> ženske 2×22, 8,5 mm; ispod DevKitC-a samo SMD; razmak redova iz Espressif DXF crteža (forum: 22,86 mm, nije zvanično).</li>
    <li><b>Rupe:</b> 4 × M3; ako je šasija metalna, bez veze sa GND (ili preko 0 Ω).</li>
    <li><b>Merne tačke:</b> 5V, 3V3, GND, TX, RX, NRST, BOOT0, SDA0, SCL0, NEO_DIN, GPIO7.</li>
    <li><b>LED-ovi:</b> 5V, 3V3, BOOT0; TX/RX aktivnost od 3V3 preko 2,2-4,7 kΩ na liniju (svetli na saobraćaju), ne sa linije na GND.</li>
    <li><b>Silkscreen:</b> raspored pinova pored svakog konektora, pin 1, NAZAD/OK/STOP, verzija, smer umetanja DevKitC-a.</li>
    <li><b>Izrada:</b> 2 sloja, ≤ 100 × 100 mm, 0805 i SOT-23.</li>
  </ul>
</section>

<section id="softver">
  <h2><span class="sec">09</span>Softver kad ploča stigne</h2>
  <p>Za odobrenje; ovde nije menjano ništa u <code>ESP32/</code>.</p>
  <ol class="list">
    <li><code>board_s3.py</code> (S-1): pinovi sa slike + <code>LIDAR_MOTOCTL=42</code>, <code>I2C1_SDA=41</code>, <code>I2C1_SCL=40</code>, <code>SENS_INT=39</code>, <code>VBAT_ADC=10</code>, <code>STM_NRST_ACTIVE=1</code>, <code>ESTOP_ACTIVE=1</code>, <code>UART_ID=1</code>; T1/T2/T3 → NAZAD/OK/STOP.</li>
    <li><code>match.StmReset</code> i <code>stmflash</code>: NRST sa obrnutom logikom.</li>
    <li><code>stmflash</code>: bootloader uvek na 115200.</li>
    <li><code>screen.py</code>: frekvencija I2C iz board fajla (800 kHz tek sa 2,2 kΩ).</li>
    <li>E-STOP na PROVERA/ROBOT i prekid taktike; NeoPixel (K-1), buzzer (K-2), lidar (L-1..L-3, rxbuf ≥ 4 KB).</li>
    <li>Host test: board fajl ima sve pinove, bez duplikata i bez zabranjenih pinova.</li>
  </ol>
</section>

<section id="pitanja">
  <h2><span class="sec">10</span>Pitanja</h2>
  <ol class="list">
    <li>Napon baterije (2S, 3S, 4S, 6S)? Za otpornik u E-STOP-u i delitelj VBAT-a.</li>
    <li>Da li su GND baterije i GND logike isti (DC-DC bez izolacije)?</li>
    <li>Nucleo: posebna ploča (koliko dug kabl?) ili matična ploča (D)? Može li ploča pogona da dobije PH konektor?</li>
    <li>Da li su ekran, tasteri i enkoder na jednom panelu (opcija B)? NeoPixel: traka ili prsten, koliko LED-ova?</li>
    <li>Revizija DevKitC-1: v1.0 ili v1.1 (piše na ploči)?</li>
    <li>Buzzer: aktivni ili pasivni, magnetni ili piezo?</li>
    <li>Baterija: INA3221 (gde?) ili delitelj na GPIO10?</li>
    <li>UART2: lidar (A2M8 ili A2M12?) ili kamera/PAMI? Ako oba, treba treći UART.</li>
    <li>Izrada: JLCPCB, 2 sloja, ručno lemljenje ili montaža kod proizvođača?</li>
    <li>Mehanika: najveće dimenzije, mesto u robotu, ima li metala oko antene?</li>
    <li>DC-DC: koji modul i koliko struje?</li>
    <li>Da li STOP taster ide i direktno na STM32 (radi i kad je ESP zaglavljen)?</li>
  </ol>
</section>

<footer>
  <span>Izvori</span>
  <ul>
    <li><a href="https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html">ESP32-S3-DevKitC-1 v1.1 user guide</a>: J1/J3, RGB LED, PSRAM pinovi, napajanje</li>
    <li><a href="https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html">ESP32-S3 Schematic Checklist</a>: strapping, impulsi pri uključenju, ADC1</li>
    <li><a href="https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf">ESP32-S3 datasheet</a>: GPIO47/48 i VDD_SPI, interni pull-up</li>
    <li><a href="https://www.st.com/resource/en/user_manual/um1724-stm32-nucleo64-boards-mb1136-stmicroelectronics.pdf">UM1724 Nucleo-64</a>: CN7-7 BOOT0, CN7-14 NRST</li>
    <li><a href="https://manuals.plus/slamtec/rplidar-a2-low-cost-360-degree-laser-range-scanner-manual">Slamtec RPLIDAR A2</a>: MOTOCTL, napajanje</li>
    <li>STM32F401 datasheet (NRST filter), AN2606 (USART bootloader), WS2812B, PC817, 74AHCT1G125, Bourns PEC11</li>
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
            '<!-- Generisano iz istog izvora kao objavljena verzija; tekst: docs/esp32s3-pcb-istrazivanje.md -->\n'
            '</head>\n<body>\n' + body +
            '\n<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>\n'
            '<script>mermaid.initialize({startOnLoad:true,theme:matchMedia("(prefers-color-scheme: dark)").matches?"dark":"neutral"});</script>\n'
            '</body>\n</html>\n')
    open(sys.argv[2], "w", encoding="utf-8").write(full)
print("ok")
