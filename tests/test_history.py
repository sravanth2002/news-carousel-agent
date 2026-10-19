from types import SimpleNamespace

from newsagent import summarize
from newsagent.models import Slide


def test_history_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(summarize, "get_settings", lambda: SimpleNamespace(out_dir=str(tmp_path)))
    summarize.save_history([Slide(headline="h", source="s", link="https://a")])
    assert summarize._history() == {"https://a"}
