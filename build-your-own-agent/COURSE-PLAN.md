# Build Your Own AI Agent — Season 1

**Working title:** *Build Your Own AI Agent — the loop, the tools, and MCP, from an empty folder*

**One-liner:** You have used an AI agent. Now build one. We write the loop by hand, give it
tools, let it touch a real machine, and then put it on MCP so anything can talk to it.

---

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Audience | Working developers | Agent-building has a real floor of prerequisites. Pretending otherwise makes a worse course |
| Language | Python 3.10+ | The larger AI-developer audience, and `anthropic[mcp]` gives us first-class MCP helpers |
| Provider | **Neutral from Lesson 1**, via an `llm.py` adapter the learner derives in 1.3 | Many learners cannot afford or cannot pay for a hosted API. The whole course runs free on a local model |
| Free path | Ollama, OpenAI-compatible endpoint, one `base_url` | Verified end to end on `gemma4`: tool calling works, 3/3 discrimination between similar tools |
| Method | Build it by hand first, reach for the SDK helper second | The point is the mechanism. A learner who has written the loop understands every agent product afterwards |
| Project | One agent, built in layers | Same shape as Recall in the AI-driven coding course. Continuity, and it mirrors real work |
| Size | 7 modules × 7 lessons = 49 lessons, "Season 1" | Same as the previous course. Leaves room for Season 2 |
| House style | Lesson titles are plain-language claims or questions, never jargon | Same as both earlier courses |
| Language level | Class 9–10 English, Indian audience | See rules below — applies to every lesson |

### Language rules (applies to all lesson text)

Developers, but many reading technical English as a second or third language. Difficulty comes
from the ideas, never from the vocabulary.

- Most sentences under 20 words. One idea per sentence.
- Everyday words over formal ones: *use* not *utilise*, *wrong* not *erroneous*, *stop it*
  not *abort the operation*.
- **No idioms or phrasal verbs.** "Under the hood", "off the rails", "nail it down" — all out.
- Every technical term gets a plain definition the first time it appears. Then use it freely.
- Active voice. "The model asks for a tool", not "a tool is requested by the model".
- Contractions are fine. They are easy to read.
- Short paragraphs. Two to four sentences.
- Avoid Latin abbreviations: *for example* not *e.g.*, *that is* not *i.e.*

> This document is written for you, not for learners, so it does not follow these rules.
> Every lesson file does.

### The agent: **Rover** — a terminal coding agent

The learner builds a small version of the tool they used in the last course. Deliberately
plain stack (Python, standard library, no agent framework) so the *agent* is the subject,
not the scaffolding.

Rover has one piece of genuinely tricky behaviour, and it carries Module 4 the way Recall's
scheduler carried Module 5: **it says it is finished when it is not.** The model returns
`end_turn` with a confident summary, and the file on disk is half-written. That failure is
not a bug you can see in a stack trace. The learner has to build the check that catches it.

By the end, Rover reads and writes files, runs shell commands behind a permission layer,
recovers from its own errors, speaks MCP in both directions, manages its own context, and
has an eval suite that says whether a change made it better or worse.

### Non-goals for Season 1

Prompt-template libraries, model benchmark comparisons, RAG and vector databases, fine-tuning,
building a UI. Multi-agent orchestration gets one lesson, not a module.

---

## Module 1 — An agent is a loop

*The whole mechanism, in one module. Everything after this is detail.*

1. An agent is a loop, and it fits on one screen
2. One API call, and what comes back
3. The model cannot do anything — it can only ask
4. `stop_reason` is the whole control flow
5. The transcript is the state, and you own all of it
6. Lab: Rover reads one file and tells you what is in it
7. Every agent product you have used is this loop wearing a coat

> **Why by hand, and not the SDK's tool runner.** The SDK ships a helper that runs this loop
> for you. We build it manually here and introduce the helper in 2.7, once the learner knows
> what it is doing on their behalf. A learner who starts with the helper cannot debug it.

## Module 2 — Tools: teaching the model what it can do

*The part every tutorial skips. Tool choice is a writing problem before it is a code problem.*

1. A tool is a description, a schema, and a function
2. The description is the instruction manual, and the model reads nothing else
3. Why it picked the wrong tool, and why that was your fault
4. Returning results: what the model does with what you send back
5. Errors are results too: `is_error`, and how to word a failure
6. Several tool calls in one turn, and the mistake that quietly stops them
7. Lab: give Rover four tools, watch it choose, then swap in the SDK's tool runner

> **2.6 is the sleeper lesson.** One assistant turn can contain several tool calls. If you
> return their results across several user messages instead of one, nothing errors — the model
> just stops making parallel calls from then on. A silent behaviour change with no error
> message is exactly the kind of thing this course exists to teach.

## Module 3 — Letting it touch your machine

*Where a toy becomes something you have to be careful with.*

1. Read, write, edit: the three file tools everything is built on
2. The tools Anthropic already defined for you, and why they have no schema
3. Running commands, and why this is the one that should worry you
4. Permissions: ask, allow, deny, remember
5. The path the model sent you is not a path you can trust
6. Lab: Rover edits its own source code
7. What a real agent product guards that your prototype does not

> **3.5 is a security lesson taught as a bug.** The learner writes a file tool, the model
> sends `../../.ssh/config`, and it works. Then we fix it. Teaching path traversal as
> something the learner just did lands harder than teaching it as a category.

## Module 4 — When the loop goes wrong

*Recovery cannot be taught in prose. This module is video-first.*

1. It never stops: turn limits and the runaway loop
2. It stops too early: `end_turn` while the job is half done
3. `max_tokens`, `pause_turn`, `refusal` — the stop reasons nobody handles
4. Feeding failure back: stderr is input, not an exception
5. Watching a run: the log you will actually read
6. Interrupting, redirecting, and starting again
7. Lab: break Rover four ways and fix each one

## Module 5 — MCP: the protocol under the tools

*The reason this course is worth taking now. Almost nobody teaches the mechanism.*

1. The problem MCP solves, in one picture
2. JSON-RPC over a pipe: the whole wire format, read once
3. Tools, resources, prompts: the three things a server offers
4. Lab: write an MCP server in one file
5. Lab: make Rover an MCP client
6. stdio or HTTP: transports, and which one you actually want
7. Publishing a server other people can trust

> **5.2 is the differentiator for the whole course.** Every MCP tutorial in circulation is
> "paste this config into a JSON file". We read the actual bytes on the wire once, and after
> that the learner can debug an MCP server instead of restarting it and hoping.

## Module 6 — Context: the resource you are actually managing

*Why the agent felt sharp for twenty minutes and useless after an hour.*

1. The transcript grows until it breaks
2. What prompt caching actually caches, and how you break it by accident
3. Clearing old tool results without losing the thread
4. Compaction: throwing away the right things
5. Files as memory: what to write down, and when
6. Sub-agents: one job, one clean context
7. Lab: give Rover a memory and a summariser

> **6.2 pays for the module.** Caching is a prefix match, so one timestamp near the top of a
> prompt silently costs you every cache hit for the rest of the session. There is no error.
> The learner checks `cache_read_input_tokens`, sees zero, and finds the interpolated date.

## Module 7 — Proving it works, and what it costs

*Ends with the learner's own agent, not ours.*

1. How do you test something that answers differently every time
2. Your first eval: ten cases, one scorer, a number you trust
3. Judging with a model, and when the judge lies to you
4. Reading the bill: tokens, caching, and effort
5. Choosing a model per job inside one agent
6. Shipping Rover: packaging, config, and other people's machines
7. Season 1 final project: an agent that does one real job for you

---

## Video policy

Video is for lessons where motion is the content. Everything else is text and diagrams, and
the text must stand alone.

| Module | Videos | Why |
|---|---|---|
| 1 | **1** (1.6 — the first loop running) | Seeing the loop turn is the moment it clicks |
| 2 | None | Conceptual. Nothing moves |
| 3 | **2** (3.3 shell + permissions, 3.6 Rover editing itself) | Watching it ask before it acts is the lesson |
| 4 | **3** (4.1 runaway, 4.2 the false finish, 4.6 interrupt and redirect) | Failure and recovery are temporal |
| 5 | **2** (5.4 server, 5.5 client connecting) | The handshake is worth watching once |
| 6 | None | Text and two diagrams |
| 7 | **1** (7.2 an eval run) | Payoff is cumulative |

**9 videos.** Under 10 minutes each. Real sessions including the failures. A lab where
nothing goes wrong teaches nothing about what to do when something does.

---

## Course-page copy (Tutor LMS fields)

**What Will You Learn?**
- Write an agent loop from scratch, with no framework
- Design tools the model chooses correctly, and debug it when it does not
- Give an agent safe access to files and a shell behind a permission layer
- Recover from runaway loops, false finishes, and every stop reason that matters
- Build an MCP server and an MCP client, and explain the protocol underneath
- Manage context, caching, and memory so a long session stays sharp
- Write evals that tell you whether a change helped

**Requirements**
- Comfortable in a terminal, and able to read and write code in some language
- Python 3.10 or newer, and an editor
- A model to talk to. Any of: a local model via Ollama (free), Google Gemini (free tier),
  OpenAI, or Anthropic. A few dollars covers the whole course on a paid provider, and the
  local option costs nothing
- No prior experience with agents or MCP

**Audience**
- Developers who have used coding agents and want to know how they work
- Anyone building an internal tool on top of an LLM and hitting the limits
- Engineers who need to review or maintain agent code somebody else wrote

**Material Includes**
- 49 lessons across 7 modules
- Rover, a complete reference implementation
- A working MCP server and client
- An eval harness and a starter case set
- Capstone brief and rubric

---

## Production notes (not for learners)

**API facts to get right, and to re-check before each module ships.** This is the part of the
course most likely to rot. Verify against the current API docs at writing time — do not copy
these from memory or from an older tutorial.

- Default model for every code sample: `claude-opus-5`. Use `claude-haiku-4-5` for the
  cheap sub-agent in 6.6 and the model-per-job lesson in 7.5.
- Adaptive thinking (`thinking: {type: "adaptive"}`) plus `output_config.effort`. There is no
  token thinking budget any more — do not teach one.
- Do not use `temperature` or `top_p` in samples. They are rejected on current models.
- No assistant-turn prefills. Structured output goes through `output_config.format`.
- Bash and text-editor tools are Anthropic-defined and schema-less. Module 3.2 exists because
  learners will otherwise write their own tool named `bash` and wonder why it behaves
  differently.
- Module 5 covers two different things and must keep them apart. The server-side MCP connector
  on the Messages API needs **both** `mcp_servers` and a matching `mcp_toolset` entry in
  `tools`. Building and running a local server is the separate `mcp` package, and connecting
  Rover to one uses the conversion helpers in `anthropic.lib.tools.mcp` — install with
  `pip install "anthropic[mcp]"`, which is why the course requires Python 3.10+.
- Verify the `mcp` package's current server API before drafting 5.4. It is the one dependency
  in this course that is not an Anthropic SDK, and it moves.
- Module 6 uses three distinct features that get confused: context editing clears, compaction
  summarises, the memory tool persists. Name the difference in 6.1 and hold the line.

**Diagrams.** 1.1 the loop itself — this one image carries the whole course, worth doing
properly. 2.3 the model choosing between four tool descriptions. 5.1 the MCP picture: one
client, several servers, why that beats N bespoke integrations. 6.1 a transcript growing past
the window.

**Quizzes.** Tutor LMS Pro quizzes are still unused site-wide. Module boundaries 1, 3, and 5
are the natural places. Five questions each, all of the form "the agent did X — why?".

**Retention point is Lesson 1.6.** It is the first time the learner's own loop calls a tool
and something real happens. Make it reachable in one sitting with no MCP, no permissions, and
no framework.

---

## Season 2 (sketch, not committed)

Multi-agent orchestration in depth · computer use · long-running and scheduled agents ·
hosted agent platforms · agent security and prompt injection · cost engineering at team scale.

---

## Open questions before writing

1. **Does this course live in `tyc/`, or its own repo?** The folder-structure question from
   `CLAUDE.md` is still open and this is the first course that has to answer it.
2. **Publishing cadence.** The ML course drips weekly. Same here?
3. **Prompt-injection lesson.** Agents with shell access and web content are a real target.
   Currently one bullet in Season 2. It may deserve a lesson in Module 3 instead.
4. **Does Rover need a name at all?** Recall worked because it was a product. Rover is a tool
   the learner already owns a better version of. An alternative is to call it what it is —
   `agent.py` — and let the learner name it in the capstone.
