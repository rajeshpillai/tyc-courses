# teachyourselfcoding.com — courses

This folder holds the source for courses published to https://teachyourselfcoding.com.
The repo is the source of truth. The site is a render target, not the place where
content is written or edited.

One folder per course. A course folder owns its plan, its module files, its build
scripts and its generated payload.

> This folder is new and currently empty. Everything below describes the conventions
> already proven on the first two courses. The earlier work still lives outside this
> folder — see [Existing work](#existing-work). Ask before assuming a course has been
> moved here.

---

## The site

WordPress with **Tutor LMS Pro**. The content model is three levels:

**Course → Topic → Lesson**

A "topic" in Tutor is what we call a **module**. One `MODULE-0X.md` file becomes one
topic and all the lessons under it.

Plugin capabilities, verified against the live site:

| Want | How | Status |
|---|---|---|
| Syntax-highlighted code | Code Syntax Block | Active |
| Runnable demos | CodePen Embed Block | Active |
| Video per lesson | Tutor lesson video field (YouTube / Vimeo / external / self-hosted) | Active |
| Arbitrary HTML / JS / canvas | Custom HTML block (admin has `unfiltered_html`) | Active |
| Site-wide JS | Custom CSS and JavaScript plugin | Active |
| Mermaid / KaTeX | WP Githuber MD | Installed, **inactive** |
| Markdown import | Ultimate Markdown | Installed, **inactive** |
| Quizzes and assignments | Tutor LMS Pro | Active, unused so far |
| Programmatic publishing | JWT Auth for WP-API + `wp/v2` + `tutor/v1` | Active, but **not** how we upload — see [Uploading](#uploading) |

SVG upload is unverified. WordPress blocks it by default. Test before relying on
inline SVG.

Gutenberg is the active editor. Classic Editor is installed but switched off.

---

## Existing work

| Course | Where | State |
|---|---|---|
| Learn Machine Learning from First Principles using JavaScript | Authored **directly in the portal**. No repo source. Course ID 3026 | Reviewed and published by Rajesh, dripping weekly |
| AI-driven coding | `/home/rajesh/work/algo/courses/ai-driven-coding` | 7 modules, 49 lessons, course ID 3123, now **published** |
| Build Your Own AI Agent | `build-your-own-agent/` (this repo) | 7 modules, 49 lessons uploaded to course ID 3201, held in **draft** |

**`ai-driven-coding` is the reference.** It is the canonical pipeline — copy its shape for
every new course. Read its `COURSE-PLAN.md`, `build_payload.py`, `make_publish_js.py` and
`make_sync_js.py` before building anything new here.

The machine learning course came first and was written straight into the WordPress portal,
before the Markdown pipeline existed. That is why it has no folder here. Do not go looking
for its source, and do not treat the live course as a model for how to structure a course
folder. If it ever needs editing, it gets edited in the portal — or brought into this repo
first, deliberately.

---

## Course folder layout

```
<course-name>/
  COURSE-PLAN.md      audience, outcomes, module map, open questions
  MODULE-01.md        one file per module
  MODULE-02.md
  ...
  build_payload.py    modules -> payload.json
  make_publish_js.py  payload.json -> publish.js   (first upload)
  make_sync_js.py     payload.json -> sync.js      (update live lessons)
  payload.json        generated, do not hand-edit
```

Generated files (`payload.json`, `publish.js`, `sync.js`) are build output. Change the
Markdown and rebuild. Never edit them directly, and never edit a lesson in wp-admin —
the next sync overwrites it.

---

## Module file format

The build scripts parse these headings exactly. Get them wrong and lessons go missing
silently.

```markdown
# Module 1 — What is really happening when an LLM writes code

*One-line italic summary. This becomes the topic summary on the site.*

Short intro paragraph.

---

## Lesson 1.1 — It guesses the next word, and that explains almost everything

### Try this first
...

## Lesson 1.2 — The context window is the whole world the model can see
...

## Production notes (not for learners)

- Video, diagram and quiz plans for this module.
```

Rules that matter:

- Module heading is a single `#` line, `Module N — Title`.
- Lesson headings are `## Lesson X.Y — Title`. Em dash or hyphen both parse; keep the
  em dash for consistency.
- Everything inside a lesson uses `###` and below.
- **`## Production notes (not for learners)` is stripped before publishing.** It is the
  only place to put author-only material — video plans, diagram briefs, unconfirmed
  facts, cost notes. `build_payload.py` refuses the build if the strings
  `Production notes`, `not for learners` or `unconfirmed` reach the payload.

Markdown extensions enabled: `tables`, `fenced_code`, `sane_lists`, `attr_list`.
Tables are wrapped in a scrollable `div.tyc-table-wrap` because the courses target
phone readers.

---

## Uploading

There is no CLI publisher and no credentials in this repo.

Uploading runs as **Playwright JS against the already-logged-in browser session**. The
browser is signed in to wp-admin; the script navigates that live session and runs its
work inside the page. That is what makes it work at all — Tutor's curriculum API is an
`admin-ajax.php` endpoint that needs the page nonce, and the nonce only exists inside an
authenticated admin page.

So: no login step, no JWT handshake, no stored password. If the session has expired, the
script gets an HTML login page back instead of JSON and reports `_tutorobject missing`.
The fix is for Rajesh to log in again in that browser, not to add credentials anywhere.

### Draft first, always

**The course is created by hand in the Tutor course editor and left as a draft.** The
scripts then fill that draft with topics and lessons. Nothing the scripts do publishes
anything — they never set `post_status`, so no upload can make a course visible.

The handoff is fixed, and both courses so far have followed it:

**Claude builds it in draft → Rajesh reviews it on the site → Rajesh publishes.**

Publishing is his call, not a step to be helpful about. Do not publish a course, do not
add a status field to the payload, and do not ask to be given the publish step.

This is also why a bad upload is recoverable: it lands in a draft nobody can see.

```
python build_payload.py     # modules -> payload.json, with the leak check
python make_publish_js.py   # -> publish.js   (creates topics + lessons)
python make_sync_js.py      # -> sync.js      (updates existing lesson bodies)
```

Then run the generated file with `browser_run_code_unsafe`, loading it **from disk**. Each
generated script is a single `async (page) => {...}` that navigates to the course
curriculum screen, waits for Tutor to boot, and does the real work inside
`page.evaluate`. The payload is 150KB+; do not push it through a tool call.

- **Create** goes through `admin-ajax.php` with `action: tutor_save_topic` and
  `tutor_save_lesson`, using `window._tutorobject` for the ajax URL and nonce.
- **Update** goes through `wp-json/wp/v2/lesson/<id>` with the `X-WP-Nonce` header from
  `window.wpApiSettings`.
- Sync matches live lessons to source lessons **by title**. WordPress texturizes titles,
  so both sides are normalised — curly quotes to straight, whitespace collapsed — before
  comparing. If you change a lesson title in Markdown, sync will report it as unmatched
  rather than update it. Rename on the site first, or accept the miss and fix it.
- Sync only writes when the stored HTML actually differs.
- Sleep 250–350ms between writes. The site is production.

### Before running an upload

Draft status limits the blast radius, but these scripts still write to the production
database over an authenticated admin session. Confirm with Rajesh before the first upload
of a course, before any destructive step (deleting lessons, reordering topics), and before
touching a course that is already live with enrolled learners. Re-running a sync into a
draft course is routine and does not need a fresh confirmation.

Take the run log seriously. The scripts return a line per lesson and a final
`created=/failed=` or `updated=/unchanged=/unmatched=/failed=` count. Read it. A silent
partial upload looks exactly like a successful one until someone opens the course.

---

## Writing

Everything a learner reads follows
[rajesh-writing-style.md](../tutorials-courses/rajesh-writing-style.md).

The core rule: **simplify the language, not the idea.**

Short sentences, one idea each. Active voice, subject then verb then object. Contractions
where a person would use them. Concrete case before the general rule. **We** for the
journey, **you** for what the learner does. No marketing language, no hype, no filler
introductions, no clever aphorisms, no invented precision.

Lesson shape that works, from the published modules:

1. **Try this first** — something the learner does or predicts before being told anything.
2. **What you just did** — name the mechanism.
3. **Why this matters** — the consequence they will hit later.
4. One sentence worth remembering, as a blockquote.
5. **Try this before the next lesson** — small, no installation, works on a phone where possible.

Text must stand alone. Video is a companion and never the only copy of an idea.

---

## Video policy

Video is reserved for lessons where motion is the content — watching an agent loop run,
watching something go subtly wrong, watching a recovery. Conceptual modules get text and
diagrams.

Keep each under 10 minutes. Unedited but trimmed. Real sessions, including the failures.
A lab where nothing goes wrong teaches nothing about what to do when something does.

Never write "this lesson has a video" into a lesson body before the video exists. Cleaning
that promise out of 49 lessons has already cost a sync pass once.

---

## Confirm before relying on these

- Whether the AI-driven coding course is being **moved** into this folder, or stays where
  it is and this folder only holds new courses.
- Whether this folder should be a git repo of its own, or one repo per course.
