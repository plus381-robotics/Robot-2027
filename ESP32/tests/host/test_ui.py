import protocol as P
import ssd1306
from conftest import run


def test_sve_stranice_se_crtaju(app, stm):
    app.ui.fb = ssd1306.SSD1306_I2C(128, 64)
    run(app, 300)
    for page in range(len(app.pages.NAMES)):
        app.pages.page = page
        app.ui.dirty = True
        app.ui.tick()
        assert any(any(row) for row in app.ui.fb.frames[-1])
    app.ui.input("menu")                                 # dugi NAZAD: meni
    app.ui.dirty = True
    app.ui.tick()
    assert app.ui.top is not app.pages
