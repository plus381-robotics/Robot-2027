# Prenos starih lokalnih fajlova (simulator/lidar, runs, scenarios, opponents, profiles) u studio/ (Gambit Studio).
from eurosim import migrate


def test_move_old_local_premesta_bez_prepisivanja(tmp_path):
    (tmp_path / "studio" / "lidar").mkdir(parents=True)
    old = tmp_path / "simulator" / "lidar"
    old.mkdir(parents=True)
    (old / "a.jsonl.gz").write_bytes(b"A")
    (old / "b.jsonl.gz").write_bytes(b"OLD")
    (tmp_path / "studio" / "lidar" / "b.jsonl.gz").write_bytes(b"NEW")
    (tmp_path / "simulator" / ".venv").mkdir()                     # .venv se ne dira
    r = migrate.move_old_local(tmp_path)
    assert r["moved"] == ["lidar/a.jsonl.gz"] and r["skipped"] == ["lidar/b.jsonl.gz"]
    assert (tmp_path / "studio/lidar/a.jsonl.gz").read_bytes() == b"A"
    assert (tmp_path / "studio/lidar/b.jsonl.gz").read_bytes() == b"NEW"
    assert (tmp_path / "simulator/lidar/b.jsonl.gz").exists() and (tmp_path / "simulator/.venv").exists()
    assert not (tmp_path / "simulator/lidar/a.jsonl.gz").exists()


def test_move_old_local_brise_prazne_stare_foldere(tmp_path):
    (tmp_path / "studio").mkdir()
    sub = tmp_path / "simulator" / "runs" / "x"
    sub.mkdir(parents=True)
    (sub / "r.json").write_text("{}")
    r = migrate.move_old_local(tmp_path)
    assert r["moved"] == ["runs/x/r.json"] and r["skipped"] == []
    assert (tmp_path / "studio/runs/x/r.json").exists()
    assert not (tmp_path / "simulator/runs").exists()


def test_move_old_local_bez_starog_foldera(tmp_path):
    assert migrate.move_old_local(tmp_path) == {"moved": [], "skipped": []}
