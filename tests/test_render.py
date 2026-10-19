from PIL import Image

from newsagent.models import Slide
from newsagent.render import slides as mod


def _no_image(monkeypatch):
    monkeypatch.setattr(mod, "get_image", lambda s, i=0: (None, ""))


def test_text_slide_renders_at_instagram_size(tmp_path, monkeypatch):
    _no_image(monkeypatch)
    s = Slide(category="AI UPDATE", headline="Headline " * 6, body="Body text " * 25, source="Test")
    paths = mod.render_slides([s], str(tmp_path))
    assert Image.open(paths[0]).size == (1080, 1350)


def test_market_table_slide_renders(tmp_path, monkeypatch):
    _no_image(monkeypatch)
    rows = [["Index", "Last", "High", "Low", "Chg"], ["Nifty 50", "1.00", "2.00", "0.50", "+1.00%"]]
    s = Slide(category="MARKETS", headline="Market snapshot", source="Yahoo Finance", rows=rows)
    assert len(mod.render_slides([s], str(tmp_path))) == 1
