# News Carousel Agent

Generates a daily 10-slide Instagram carousel (tech, business and India news) using a local LLM,
and delivers the slides and caption to Google Drive for posting. Instagram API publishing is
implemented and will be enabled once Meta developer access is available.

## What it does

| # | Slide | Source |
|---|---|---|
| 1 | AI updates, new models, pros and cons | AI feeds |
| 2 | India and the global economy | economy feeds |
| 3 | Political impact in India | India news feeds |
| 4 | Markets: last, high, low | live Yahoo Finance data (no LLM) |
| 5 | Technology advancement | tech feeds |
| 6 | Jobs: hiring and layoffs | filtered business/tech feeds |
| 7 | Masters abroad | education feeds |
| 8 | Startups and funding | Inc42, TechCrunch |
| 9 | Cybersecurity | The Hacker News, BleepingComputer |
| 10 | Space and science | NASA, The Hindu |

## How it works

```
RSS feeds (per category) -> LLM (Ollama) picks 1 story + writes a short summary
  -> image from the story's own page (og:image), else Wikimedia Commons
  -> Pillow renders 1080x1350 slides -> Drive folder + caption on clipboard
  -> (later) Cloudinary upload -> Instagram Graph API carousel
```

Design choices: fetching and rendering are deterministic. The LLM only ranks and summarizes
text it was given ("use only facts in the text"). Market numbers never go through the LLM.
Stories already used are remembered, so they don't repeat on later days.

## Requirements

macOS, Python 3.12+, [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com) with `qwen2.5:7b`,
Google Drive for desktop (for delivery).

## Quickstart

```bash
git clone <your-repo-url> && cd news-carousel-agent
uv sync
ollama pull qwen2.5:7b
cp .env.example .env        # set SYNC_DIR to your Drive folder
uv run newsagent daily      # slides -> Drive, caption -> clipboard
```

Commands:

- `newsagent daily [--force]`: build slides, copy to Drive, copy caption (manual posting)
- `newsagent run [--no-dry-run] [--auto]`: render, and optionally publish via the Instagram API

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `OLLAMA_MODEL` | local model | `qwen2.5:7b` |
| `IMAGE_SOURCE` | `auto`, `article`, `commons`, `none` | `auto` |
| `SYNC_DIR` | Drive folder to copy slides into | empty |
| `IG_TOKEN`, `IG_USER_ID` | Instagram API (optional) | empty |
| `CLOUDINARY_CLOUD`, `CLOUDINARY_PRESET` | image host for API posting | empty |

Categories and feeds live in `src/newsagent/categories.py`. A dead feed is logged and skipped.

## Scheduling (macOS)

```bash
cp deploy/com.sravanth.newsagent.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.sravanth.newsagent.plist
```
Runs daily at 07:30; logs go to `~/Library/Logs/newsagent.log`. Edit the paths in the plist first.

## Development

```bash
uv run ruff check . && uv run ruff format .
uv run pytest
```
CI runs lint, format check and tests on every push.

## Limitations and notes

- Small local LLMs can distort facts. Review the slides before posting.
- Publisher images (`og:image`) are copyrighted. Slides credit the source, but you are responsible
  for reuse rights. `IMAGE_SOURCE=commons` uses only freely licensed images, with credit.
- Market data comes from an unofficial Yahoo endpoint and may be delayed or unavailable.
- Instagram caps carousels at 10 items.

## Roadmap

- [ ] Enable Instagram API publishing (waiting on Meta developer access) and token refresh
- [ ] Hosted free-tier LLM option and a GitHub Actions schedule
- [ ] Dockerfile

## License

MIT