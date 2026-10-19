import json
import logging
import re
import secrets
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path

import httpx
import typer

from newsagent.config import get_settings
from newsagent.models import Slide
from newsagent.render.slides import render_slides
from newsagent.summarize import build_digest, save_history

app = typer.Typer(add_completion=False)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
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
    """Build today's slides, copy to Drive, and email an approval request."""
    s = get_settings()
    out = _today_dir()
    marker = out / ".prepared"
    if marker.exists() and not force:
        log.info("Already prepared today, re-delivering")
        paths = sorted(out.glob("slide_*.jpg"))
        caption = (out / "caption.txt").read_text()
    else:
        paths, caption, slides = _build(out)
        save_history(slides)
        marker.touch()
        if s.smtp_user and s.approver_email:
            from newsagent.notify.mailer import send_preview

            token = secrets.token_urlsafe(8)
            (out / ".token").write_text(token)
            (out / ".hold").unlink(missing_ok=True)
            try:
                send_preview(paths, caption, token)
            except Exception as e:  # never lose the Drive delivery over an email problem
                log.warning("Preview email failed: %s", e)
    _deliver(out, paths, caption)


def _publish(out: Path) -> None:
    from newsagent.publish.instagram import publish_carousel
    from newsagent.storage.cloudinary import upload

    paths = sorted(out.glob("slide_*.jpg"))
    caption = (out / "caption.txt").read_text()
    post_id = publish_carousel([upload(p) for p in paths], caption)
    _mark_posted(post_id)
    log.info("Published: %s", post_id)
    subprocess.run(
        [
            "osascript",
            "-e",
            'display notification "Posted to Instagram" with title "News carousel"',
        ],
        check=False,
    )


@app.command()
def post() -> None:
    """Publish today's prepared slides to Instagram (manual override)."""
    out = _today_dir()
    if (out / ".hold").exists() or _already_posted():
        log.info("Held or already posted, nothing to do")
        raise typer.Exit()
    if not (out / ".prepared").exists():
        log.error("Nothing prepared today, run `newsagent daily` first")
        raise typer.Exit(1)
    _publish(out)


@app.command("refresh-token")
def refresh_token() -> None:
    """Extend the Instagram token by 60 days and save it to .env."""
    s = get_settings()
    r = httpx.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": s.ig_token},
        timeout=30,
    )
    if r.is_error:
        log.warning("Token refresh failed: %s", r.text)
        raise typer.Exit(1)
    env = Path(".env")
    env.write_text(
        re.sub(r"(?m)^IG_TOKEN=.*$", f"IG_TOKEN={r.json()['access_token']}", env.read_text())
    )
    log.info("Token refreshed, valid for ~%s days", r.json().get("expires_in", 0) // 86400)

    log.info("Token refreshed, valid for ~%s days", r.json().get("expires_in", 0) // 86400)


@app.command()
def approvals() -> None:
    """Check for an emailed Approve/Reject reply and act on it. Run every 10 minutes."""
    s = get_settings()
    out = _today_dir()
    token_file = out / ".token"
    if not token_file.exists():
        log.info("No pending approval today (no .token)")
        return
    if (out / ".hold").exists():
        log.info("Hold file present, skipping")
        return
    if _already_posted():
        log.info("Already posted today, skipping")
        return
    if datetime.now().hour >= s.approval_deadline_hour:
        log.info("Past the %d:00 deadline, skipping", s.approval_deadline_hour)
        return

    from newsagent.notify.mailer import check_reply

    decision = check_reply(token_file.read_text().strip())
    if decision == "approve":
        log.info("Approved by email, publishing")
        _publish(out)
        try:
            refresh_token()
        except (typer.Exit, httpx.HTTPError):
            log.warning("Token refresh skipped")
    elif decision == "reject":
        (out / ".hold").touch()
        log.info("Rejected by email, skipping today")
    else:
        log.info("No reply yet")


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
