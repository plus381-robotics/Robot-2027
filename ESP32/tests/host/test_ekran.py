# Rework ekrana: kontrole, PROVERA i tok izbora, poruke, izveštaj, crtanje na promenu.
import compat
import protocol as P
import ssd1306
from conftest import run


def setup(app, tmp_path, monkeypatch, src="from tac import *\nSTART = (250, 1000, 0)\nmove(100)\n"):
    import app as appmod
    (app.tactics_dir / "t.py").write_text(src)
    monkeypatch.setattr(appmod, "MEC_DIR", str(tmp_path / "mec"))
    app.ui.fb = ssd1306.SSD1306_I2C(128, 64)
    run(app, 300)


def test_kontrole_iste_svuda(app, tmp_path, monkeypatch):
    setup(app, tmp_path, monkeypatch)
    u = app.ui
    u.input("back")
    assert len(u.stack) == 1                            # NAZAD na stranici ne otvara ništa
    u.input("menu")
    assert u.top.title == "Meni"                        # dugi NAZAD = meni
    u.input("back")
    assert len(u.stack) == 1
    app.select("t", "plava")
    app.arm()
    u.input("menu")
    assert len(u.stack) == 1                            # u meču meni je zaključan


def test_pocetni_ekran_opcije(app, tmp_path, monkeypatch):
    """Početni ekran: opcije se biraju enkoderom; taktika se bira ovde, ne u meniju."""
    setup(app, tmp_path, monkeypatch)
    u, home = app.ui, app.pages.list[0]
    assert [r[0] for r in home.rows()] == ["taktika", "strana", "provera", "naoruzaj", "test odmah"]
    ok, items = app.check()
    assert not ok and ("ne", "taktika", "izaberi") in items
    u.input("ok")                                       # taktika -> spisak
    assert u.top.title == "Taktike"
    u.input("ok")                                       # t
    assert u.top.title == "Strana"
    u.input("rot", 1)
    u.input("ok")                                       # zuta
    assert len(u.stack) == 1 and app.pages.cur.name == "PROVERA"
    assert app.st["sel_tactic"] == "t" and app.st["sel_side"] == "zuta"
    import json
    assert json.load(open(app.st.path))["sel_side"] == "zuta"     # pamti se posle restarta
    u.input("rot", 1)
    u.input("ok")                                       # strana: OK menja plava/zuta
    assert app.st["sel_side"] == "plava"
    u.input("rot", 2)
    assert home.rows()[home.sel][0] == "naoruzaj"
    assert app.check()[0]
    u.input("ok")                                       # naoruzaj
    assert app.match.state == "NAORUZAN"
    assert [r[0] for r in home.rows()][3:] == ["simul. cinc", "otkazi"]
    u.input("back")                                     # NAZAD = otkaži
    assert app.match.state == "NEMA"


def test_okret_prelazi_sa_opcija_na_stranice(app, tmp_path, monkeypatch):
    setup(app, tmp_path, monkeypatch)
    u, home = app.ui, app.pages.list[0]
    u.input("rot", 4)                                   # poslednja opcija
    assert app.pages.page == 0 and home.sel == 4
    u.input("rot", 1)                                   # dalje: sledeća stranica
    assert app.pages.cur.name == "TAKTIKA"
    u.input("rot", -1)                                  # nazad: poslednja opcija
    assert app.pages.page == 0 and home.sel == 4
    assert "Taktike" not in [i.label for i in app.settings_menu().items]   # nije u meniju


def test_stop_preko_celog_ekrana(app, tmp_path, monkeypatch):
    setup(app, tmp_path, monkeypatch)
    app.stop()
    assert app.ui.alarmed
    app.ui.dirty = True
    app.ui.tick()
    fr = app.ui.fb.frames[-1]
    assert sum(map(sum, fr)) > 128 * 64 // 2           # inverzno: većinom upaljeno
    app.ui.input("rot", 1)
    assert app.ui.alarmed                               # samo OK ga zatvara
    app.ui.input("ok")
    assert not app.ui.alarmed


def test_greska_ostaje_i_pokazuje_uzvicnik(app, stm, tmp_path, monkeypatch):
    from runner import run_tactic
    import app as appmod
    setup(app, tmp_path, monkeypatch, "from tac import *\nmove(100)\n")
    stm.drop = 3
    run_tactic(app, "t")
    assert app.errors and app.unseen
    assert any(ic is appmod.ICON_BANG for ic, _ in app.indicators())
    app.ui.input("ok")                                  # zatvori prekid
    app.pages.show("DNEVNIK")
    app.ui.dirty = True
    app.ui.tick()
    assert app.unseen == 0 and app.errors               # pogledano, ali lista ostaje


def test_izvestaj_posle_taktike_i_cuvanje(app, stm, tmp_path, monkeypatch):
    from runner import run_tactic
    setup(app, tmp_path, monkeypatch)
    app.select("t", "plava")
    run_tactic(app, "t")
    rp = app.report
    assert rp["ok"] and rp["done"] == 1 and app.pages.cur.name == "IZVESTAJ"
    assert app.reports() == ["0001.json"]
    app.report = None
    app.load_report("0001.json")
    assert app.report["name"] == "t"
    for v in range(3):                                  # sve tri strane izveštaja se crtaju
        app.pages.cur.view = v
        app.ui.dirty = True
        app.ui.tick()


def test_salje_na_ekran_samo_kad_se_promeni(app, tmp_path, monkeypatch):
    setup(app, tmp_path, monkeypatch)
    app.pages.show("VEZA")
    u = app.ui
    compat.fake[0] = (compat.fake[0] // 1000) * 1000 + 100     # početak sekunde (puls stoji)
    u.dirty = True
    u.tick()
    n = u.sent
    for _ in range(3):
        u.dirty = True
        u.tick()
    assert u.sent == n                                  # ista slika: ništa se ne šalje
    compat.sleep_ms(1000)
    u.tick()
    assert u.sent == n + 1                              # puls jednom u sekundi


def test_miran_ekran_u_mecu(app, tmp_path, monkeypatch):
    setup(app, tmp_path, monkeypatch)
    app.match.state = "MEC"
    app.pages.show("TAKTIKA")
    assert app.pages.cur.calm() and app.pages.cur.title() == "MEC" and app.pages.live_ms == 500
    app.ui.dirty = True
    app.ui.tick()


def test_okret_budi_i_izvrsi_se(app, tmp_path, monkeypatch):
    setup(app, tmp_path, monkeypatch)
    u = app.ui
    u.asleep = True
    home = app.pages.list[0]
    s0 = home.sel
    u.input("rot", 1)
    assert not u.asleep and home.sel == s0 + 1          # okret je izvršen (pomerio izbor)
    u.asleep = True
    u.input("menu")
    assert len(u.stack) == 1                            # posle spavanja samo pali ekran
