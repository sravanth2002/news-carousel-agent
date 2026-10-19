import json
import logging
import shutil
import subprocess
from datetime import date
from pathlib import Path

import typer

from newsagent.config import get_settings
from newsagent.models import Slide
from newsagent.render.slides import render_slides
from newsagent.summarize import build_digest, save_history

app = typer.Typer(add_completion=False)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("newsagent")


@app.callback()
def main() -> None:
    """Tech & business news carousel agent."""


def _today_dir() -> Path:
    return Path(get_settings().out_dir) / str(date.today())


def _state_path() -> Path:
    return Path(get_settings().out_dir) / "posted.json"


def _already_posted() -> bool:
    p = _state_path()
    return p.exists() and str(date.today()) in json.loads(p.read_text())


def _mark_posted(post_id: str) -> None:
    p = _state_path()
    data = json.loads(p.read_text()) if p.exists() else {}
    data[str(date.today())] = post_id
    p.write_text(json.dumps(data, indent=2))


def _build(out: Path) -> tuple[list[Path], str, list[Slide]]:
    slides, caption = build_digest()
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("slide_*.jpg"):  # clear leftovers from earlier runs
        old.unlink()
    paths = render_slides(slides, str(out))
    (out / "caption.txt").write_text(caption)
    log.info("Rendered %d slides to %s", len(paths), out)
    return paths, caption, slides


def _deliver(out: Path, paths: list[Path], caption: str) -> None:
    s = get_settings()
    subprocess.run(["pbcopy"], input=caption.encode(), check=False)  # caption to Mac clipboard
    where = out
    if s.sync_dir:
        root = Path(s.sync_dir)
        if not root.parent.exists():
            raise SystemExit(
                f"Drive folder not found: {root.parent}\n"
                "Check SYNC_DIR in .env and that Drive for desktop is signed in."
            )
        dest = root / str(date.today())
        dest.mkdir(parents=True, exist_ok=True)
        for p in [*paths, out / "caption.txt"]:
            shutil.copyfile(p, dest / p.name)
        where = dest
        log.info("Copied %d files to Drive folder %s", len(paths) + 1, dest)
    elif s.import_to_photos:
        files = ", ".join(f'POSIX file "{p.resolve()}"' for p in paths)
        script = f'tell application "Photos" to import {{{files}}} skip check duplicates true'
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if r.returncode != 0:
            log.warning("Photos import failed: %s", r.stderr.strip())
    else:
        subprocess.run(["open", str(out)], check=False)
    msg = f"{len(paths)} slides ready in {where.name}"
    subprocess.run(
        ["osascript", "-e", f'display notification "{msg}" with title "News carousel"'], check=False
    )


@app.command()
def daily(
    force: bool = typer.Option(False, help="Regenerate even if already prepared today"),
) -> None:
    """Build today's slides, copy them to Drive/Photos, copy the caption. Post manually."""
    out = _today_dir()
    marker = out / ".prepared"
    if marker.exists() and not force:
        log.info("Already prepared today, re-delivering")
        paths = sorted(out.glob("slide_*.jpg"))
        caption = (out / "caption.txt").read_text()
    else:
        paths, caption, slides = _build(out)
        save_history(slides)  # so tomorrow's stories differ
        marker.touch()
    _deliver(out, paths, caption)


@app.command()
def run(
    dry_run: bool = typer.Option(True, help="Render only, don't post"),
    auto: bool = typer.Option(False, help="Skip approval prompt"),
) -> None:
    """Full API posting (needs the Instagram token, for later)."""
    if not dry_run and _already_posted():
        log.info("Already posted today, exiting")
        raise typer.Exit()

    out = _today_dir()
    paths, caption, slides = _build(out)
    typer.echo(f"\nCaption:\n{caption}\n")

    if dry_run:
        return
    if not auto:
        subprocess.run(["open", str(out)], check=False)
        if not typer.confirm("Approve posting to Instagram?"):
            raise typer.Exit()

    from newsagent.publish.instagram import publish_carousel
    from newsagent.storage.cloudinary import upload

    urls = [upload(p) for p in paths]
    post_id = publish_carousel(urls, caption)
    _mark_posted(post_id)
    save_history(slides)
    log.info("Published: %s", post_id)
