#!/usr/bin/env python3
"""Generator: protocol.yaml -> {nucleo,pogon-blackpill}/Core/Inc/protocol.h + ESP32/lib/protocol.py

Pokretanje (iz korena repoa):  python protocol/gen.py
Generisane fajlove NIKAD ne menjati ručno.

Polje može imati treći element: verziju od koje postoji, npr. [last_seq, u8, 3]. Takva polja moraju biti
na kraju poruke. C strana ih uvek ima; ESP (protocol.py) prima i kraću poruku sa starijeg STM32
(nedostajuća polja su None), pa novi ESP radi i sa starim firmverom.
"""
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = yaml.safe_load((ROOT / "protocol" / "protocol.yaml").read_text())

# tip -> (struct format, C tip, veličina)
TYPES = {
    "u8": ("B", "uint8_t", 1), "i8": ("b", "int8_t", 1),
    "u16": ("H", "uint16_t", 2), "i16": ("h", "int16_t", 2),
    "u32": ("I", "uint32_t", 4), "i32": ("i", "int32_t", 4),
    "f32": ("f", "float", 4),
}
HEADER = "GENERISANO iz protocol/protocol.yaml - ne menjati ručno"


SINCE = {}                     # (poruka, polje) -> verzija od koje polje postoji


def messages():
    for name, m in SPEC["messages"].items():
        fields = []
        for f in m["fields"]:
            fields.append((f[0], f[1]))
            if len(f) > 2:
                SINCE[(name, f[0])] = f[2]
        opt = [SINCE.get((name, f)) is not None for f, _ in fields]
        if any(opt) and opt != sorted(opt):
            raise SystemExit(f"{name}: polja sa verzijom moraju biti na kraju")
        for i, (fname, ftype) in enumerate(fields):
            if ftype == "bytes" and i != len(fields) - 1:
                raise SystemExit(f"{name}.{fname}: 'bytes' mora biti poslednje polje")
            if ftype != "bytes" and ftype not in TYPES:
                raise SystemExit(f"{name}.{fname}: nepoznat tip {ftype}")
        yield name, m["type"], m["dir"], fields


def check_unique():
    seen = {}
    for name, t, _, _ in messages():
        if t in seen:
            raise SystemExit(f"type 0x{t:02X} koriste i {seen[t]} i {name}")
        seen[t] = name


def gen_c():
    out = [f"/* {HEADER} */", "#pragma once", "#include <stdint.h>", "",
           f"#define PROTO_VERSION {SPEC['version']}", ""]
    for ename, vals in SPEC["enums"].items():
        for k, v in vals.items():
            out.append(f"#define {ename.upper()}_{k} {v}")
        out.append("")
    for name, t, d, fields in messages():
        out.append(f"#define MSG_{name} 0x{t:02X}  /* {d} */")
    out.append("")
    for name, t, d, fields in messages():
        fixed = [(f, ty) for f, ty in fields if ty != "bytes"]
        if not fixed:
            continue
        lname = name.lower()
        out.append(f"typedef struct __attribute__((packed)) {{")
        for f, ty in fixed:
            out.append(f"    {TYPES[ty][1]} {f};")
        out.append(f"}} msg_{lname}_t;")
        size = sum(TYPES[ty][2] for _, ty in fixed)
        out.append(f"_Static_assert(sizeof(msg_{lname}_t) == {size}, \"{name} size\");")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def gen_py():
    out = [f"# {HEADER}", "# Radi i u MicroPythonu i u CPythonu.", "import struct", "",
           f"VERSION = {SPEC['version']}", ""]
    for ename, vals in SPEC["enums"].items():
        out.append(f"class {ename}:")
        for k, v in vals.items():
            out.append(f"    {k} = {v}")
        out.append("")
    for name, t, d, fields in messages():
        out.append(f"{name} = 0x{t:02X}")
    out.append("")
    # tabela: type -> (ime, format, imena fiksnih polja, ime bytes polja ili None)
    out.append("# min = veličina bez polja koja postoje tek od novije verzije (starija poruka je kraća)")
    out.append("_MSGS = {")
    for name, t, d, fields in messages():
        fixed = [(f, ty) for f, ty in fields if ty != "bytes"]
        tail = next((f for f, ty in fields if ty == "bytes"), None)
        fmt = "<" + "".join(TYPES[ty][0] for _, ty in fixed)
        names = tuple(f for f, _ in fixed)
        mins = sum(TYPES[ty][2] for f, ty in fixed if SINCE.get((name, f)) is None)
        out.append(f"    0x{t:02X}: ({name!r}, {fmt!r}, {names!r}, {tail!r}, {mins}),")
    out.append("}")
    out.append("NAMES = {v[0]: k for k, v in _MSGS.items()}")
    out.append('''

def encode(name, **kw):
    """encode('GOTO', x=..., y=...) -> (type, payload bytes). Polja novijih verzija (na kraju) koja nisu zadata
    se izostave: poruka je kao u starijoj verziji (za stari STM32)."""
    t = NAMES[name]
    _, fmt, names, tail, mins = _MSGS[t]
    k = len(names)
    while k and names[k - 1] not in kw and struct.calcsize(fmt[:k]) >= mins:   # samo polja novijih verzija
        k -= 1
    payload = struct.pack(fmt[:k + 1], *[kw[n] for n in names[:k]]) if k else b""
    if tail:
        payload += bytes(kw.get(tail, b""))
    return t, payload


def decode(t, payload):
    """(type, payload) -> (ime, dict polja). Nepoznat tip -> (None, {})."""
    m = _MSGS.get(t)
    if m is None:
        return None, {}
    name, fmt, names, tail, mins = m
    size = struct.calcsize(fmt) if names else 0
    n = len(payload)
    if not tail and mins <= n < size:           # starija verzija: bez novijih polja na kraju
        k = len(names)
        while k and struct.calcsize(fmt[:k + 1]) > n:
            k -= 1
        if struct.calcsize(fmt[:k + 1]) != n:
            return None, {}
        d = dict(zip(names, struct.unpack(fmt[:k + 1], payload)))
        for f in names[k:]:
            d[f] = None
        return name, d
    if n < size or (not tail and n != size):
        return None, {}
    vals = struct.unpack(fmt, payload[:size]) if names else ()
    d = dict(zip(names, vals))
    if tail:
        d[tail] = bytes(payload[size:])
    return name, d
''')
    return "\n".join(out)


if __name__ == "__main__":
    check_unique()
    for robot in ("nucleo", "pogon-blackpill"):
        (ROOT / robot / "Core" / "Inc" / "protocol.h").write_text(gen_c())
    (ROOT / "ESP32" / "lib" / "protocol.py").write_text(gen_py())
    print(f"protocol v{SPEC['version']}: generisano protocol.h i protocol.py")
