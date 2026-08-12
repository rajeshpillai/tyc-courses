# tyc-courses

Source for the courses published to [teachyourselfcoding.com](https://teachyourselfcoding.com).

This repository is the source of truth. The site is a render target — lessons are written here
as Markdown, converted to HTML, and uploaded. Nothing is authored in WordPress.

**Read [CLAUDE.md](CLAUDE.md) first.** It covers the platform, the module file format the build
scripts depend on, the upload pipeline, and the house writing style.

## Courses

| Course | Folder | State |
|---|---|---|
| Build Your Own AI Agent — Season 1 | [`build-your-own-agent/`](build-your-own-agent/) | 7 modules, 49 lessons. Course ID 3201, **draft** |
| Learn Machine Learning from First Principles | — | Authored in the portal, no source here. Course ID 3026, live |
| AI-Driven Coding | — | Lives in a separate folder outside this repo. Course ID 3123, live |

## Working on a course

```bash
cd build-your-own-agent

python3 build_payload.py      # MODULE-*.md -> payload.json, with a content-leak check
python3 make_publish_js.py    # -> publish.js   (first upload: creates topics + lessons)
python3 make_sync_js.py       # -> sync.js      (updates an existing course in place)
```

Then run the generated `.js` through a browser session already signed in to wp-admin. See
CLAUDE.md for why it works that way and what the guard rails are.

`payload.json`, `publish.js` and `sync.js` are build output and are not committed.

## Course requirements

Courses here are provider-neutral where they touch an LLM. `build-your-own-agent/llm.py` is a
small adapter covering Anthropic, OpenAI, Google Gemini and local models via Ollama, so the
whole course can be completed for free on a laptop.

Verify a provider works before writing lessons against it:

```bash
cd build-your-own-agent
GOOGLE_API_KEY=... python3 verify_providers.py
```
