#!/usr/bin/env python3
"""CAD (STEP iz Fusion-a) -> GLB za 3D prikaz robota u simulatoru.

    pip install cascadio trimesh          # samo za konverziju (simulatoru ne trebaju)
    python simulator/tools/cad_to_glb.py robot.step --out simulator/web/models/robot.glb [--front +y]

Šta radi:
  - STEP -> trouglovi (OpenCascade preko cascadio), tolerancija --tol mm (veća = manji fajl);
  - okrene model tako da je "napred" robota +x simulatora (--front: koja osa u CAD-u gleda napred);
  - spusti ga na pod (najniža tačka modela, npr. dno gume, na z = 0) i centrira po osovini točkova
    (--center: "bbox" = sredina modela, ili "x,y" u mm u CAD koordinatama);
  - oboji delove po imenu (guma, felna, motor, ploča...), jer STEP iz Fusion-a često nema boje.
Jedinice: STEP u mm -> GLB u metrima (kao three.js scena simulatora).
"""
import argparse
import math
import pathlib
import tempfile

COLORS = [  # (deo imena, RGBA)
    ("guma", (25, 25, 25, 255)), ("omni", (40, 40, 40, 255)), ("odom_tocak", (30, 30, 30, 255)),
    ("oring", (20, 20, 20, 255)), ("felna", (190, 190, 195, 255)), ("ploca", (170, 175, 185, 255)),
    ("maxon", (60, 60, 65, 255)), ("motor", (90, 95, 105, 255)), ("enkoder", (30, 90, 160, 255)),
    ("remenica", (200, 200, 205, 255)), ("lezaj", (150, 150, 155, 255)), ("bearing", (150, 150, 155, 255)),
    ("blatobran", (230, 120, 20, 255)), ("blok", (230, 120, 20, 255)), ("nosac", (230, 120, 20, 255)),
    ("zatezac", (230, 120, 20, 255)), ("odom_ram", (230, 120, 20, 255)),
]
DEFAULT = (140, 140, 150, 255)
FRONT = {"+x": 0, "+y": -90, "-x": 180, "-y": 90}      # rotacija oko z (stepeni) da CAD osa postane +x


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step")
    ap.add_argument("--out", required=True)
    ap.add_argument("--front", choices=sorted(FRONT), default="+y", help="CAD osa koja gleda napred (podrazumevano +y)")
    ap.add_argument("--center", default="bbox", help='"bbox" ili "x,y" (mm, CAD) = tačka između pogonskih točkova')
    ap.add_argument("--tol", type=float, default=1.0, help="tolerancija mreže u mm (podrazumevano 1.0)")
    a = ap.parse_args()

    import cascadio
    import trimesh

    with tempfile.TemporaryDirectory() as d:
        raw = str(pathlib.Path(d) / "raw.glb")
        cascadio.step_to_glb(a.step, raw, a.tol, 0.5)
        scene = trimesh.load(raw)
    meshes = []
    for node in scene.graph.nodes_geometry:
        T, g = scene.graph[node]
        m = scene.geometry[g].copy()
        m.apply_transform(T)
        name = node.split(":")[0].lower()
        col = next((c for k, c in COLORS if k in name), DEFAULT)
        metal = 0.6 if any(k in name for k in ("felna", "ploca", "remenica", "lezaj", "bearing")) else 0.1
        m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            baseColorFactor=col, metallicFactor=metal, roughnessFactor=0.6))
        m.metadata["name"] = node
        meshes.append(m)
    allm = trimesh.util.concatenate(meshes)
    lo, hi = allm.bounds
    if a.center == "bbox":
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    else:
        cx, cy = (float(v) / 1000 for v in a.center.split(","))
    ang = math.radians(FRONT[a.front])
    M = trimesh.transformations.rotation_matrix(ang, [0, 0, 1]) @ \
        trimesh.transformations.translation_matrix([-cx, -cy, -lo[2]])
    out = trimesh.Scene()
    for m in meshes:
        m.apply_transform(M)
        out.add_geometry(m, node_name=m.metadata["name"], geom_name=m.metadata["name"])
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.export(a.out)
    b = out.bounds
    print("%s: %d delova, %.0f x %.0f x %.0f mm (napred = +x), %.0f KB"
          % (a.out, len(meshes), *(1000 * (b[1] - b[0])), pathlib.Path(a.out).stat().st_size / 1024))


if __name__ == "__main__":
    main()
