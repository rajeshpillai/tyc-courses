# Module 6 — Context: the resource you are actually managing

*Why the agent felt sharp for twenty minutes and useless after an hour.*

You have watched `input_tokens` climb every turn since Lesson 1.5. This module is about what
that number does to you, and the four different tools for keeping it under control.

They are easy to confuse, so name the difference now and hold on to it:

- **Caching** makes resending cheap.
- **Clearing** removes old tool results.
- **Compaction** replaces old turns with a summary.
- **Memory** writes things to a file so they survive the session ending.

Four different problems. Four different tools.

---

## Lesson 6.1 — The transcript grows until it breaks

### Try this first

Add one line to Rover's loop and run a real task:

```python
print(f"turn {turn}: {reply.usage.get('in')} in, {reply.usage.get('out')} out")
```

Watch the input number.

```
turn 1: 1,240 in, 180 out
turn 2: 3,100 in, 95 out
turn 3: 7,850 in, 210 out
turn 4: 12,400 in, 160 out
```

Output stays small. Input climbs, fast. By turn four you are paying for twelve thousand tokens
to get back a hundred and sixty.

### Why

Lesson 1.5: the API is stateless, so every call resends the entire `messages` list.

Turn four sends turns one, two, and three along with it — including every tool result. One
`read_file` on a 2,000-line file is 25,000 tokens, and you pay for it again on every
subsequent turn, forever.

The pattern is worse than linear. If each turn adds *n* tokens, the total you pay across *t*
turns grows with the square of *t*. Doubling the length of a session roughly quadruples the
cost.

### Two ceilings, not one

**The hard ceiling: the context window.** Anything from a few thousand tokens on a small
local model to a million on a large hosted one. On a big model you will rarely hit it in a
session you are watching; on a small local one you will hit it today.

**The soft ceiling: usefulness.** This one you hit constantly, and it has no error message.

Long before the window fills, quality drops. The important instruction from turn one is now
surrounded by forty thousand tokens of tool output. The model is not ignoring you. It is
attending to a haystack you built.

That is the "it felt sharp and then it did not" experience, and it is a context problem, not a
model problem.

### What is actually in there

Instrument it before you optimise it:

```python
from collections import Counter


def breakdown(messages):
    sizes = Counter()
    for m in messages:
        if m["role"] == "tool_results":
            for r in m["results"]:
                sizes["tool results"] += len(str(r["content"]))
        else:
            sizes[m["role"]] += len(m.get("content") or "")
            for tc in m.get("tool_calls", []):
                sizes["tool calls"] += len(str(tc.arguments))
    return sizes.most_common()
```

Run it on a real session. Almost every time, the answer is the same: **tool results are
seventy to ninety percent of your transcript.** Not the system prompt, not the conversation —
the output of `read_file` and `bash`, sitting there being resent.

That is where the money is, and it is why the next three lessons are all about tool results.

> The transcript is resent in full on every turn, so cost grows with the square of the session
> length. Tool results are almost all of it.

### Try this before the next lesson

Add the token print and the breakdown. Run a ten-turn task.

Find your single largest block. It will be one tool result — probably a file read or a test
run. Ask yourself whether the model still needed it at turn ten. It almost certainly did not,
and you paid for it ten times.

---

## Lesson 6.2 — What prompt caching actually caches, and how you break it by accident

### Try this first

Run any two-turn conversation and print two fields:

```python
print(reply.raw.usage)        # your provider's own usage object
```

Both are zero. You have never used caching, and you have been resending the same content at
full price the whole course.

### What caching is

The API can remember the beginning of your prompt and skip reprocessing it. A cache read costs
about a tenth of a normal input token. A cache write costs about a quarter more than normal.

So it pays for itself on the second request and is close to free after that. For an agent —
where the same system prompt, the same tools, and a growing shared history go out every turn —
it is the single biggest cost lever you have.

**How you switch it on depends on your provider**, and this is one of the few places in the
course where that matters:

| Provider | How caching works |
|---|---|
| OpenAI | **Automatic.** Repeated prefixes are cached for you, with no parameter |
| Anthropic | **Explicit.** You mark what to cache with a `cache_control` parameter |
| Gemini | **Explicit**, with its own separate caching API |
| Ollama / local | The model is already on your machine; there is no network cost to save |

Anthropic's explicit form looks like this, and it is the clearest illustration of the idea:

```python
# Anthropic-specific — check your provider's own documentation.
response = client.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    cache_control={"type": "ephemeral"},
    system=SYSTEM_PROMPT,
    tools=TOOLS,
    messages=messages,
)
```

Whether you switch it on or your provider does it silently, **the rule in the next section
decides whether it works at all** — and that rule is the same everywhere.

### The one rule

Everything else in this lesson follows from a single fact:

**Caching is a prefix match.** The API caches from the start of your prompt up to a marked
point. If any byte in that prefix changes, the cache is invalid from that byte onwards.

The prompt is assembled in a fixed order:

```
tools  →  system  →  messages
```

Tools first. So a change to your tool list invalidates everything. System prompt next; a
change there invalidates all the messages. Messages last, and each new turn extends the
prefix, which is why a growing conversation caches beautifully — the old part never changes.

### How people break it

Here is a system prompt that costs you every cache hit for the entire session:

```python
SYSTEM_PROMPT = f"""You are Rover, a coding assistant.
The current date is {datetime.now()}.
You are helping {user.name} in {os.getcwd()}.
"""
```

Three invalidators in four lines. The timestamp changes every call, so the prefix is different
every call, so nothing ever caches. There is no error. Your bill is just three times what it
should be, and `cache_read_input_tokens` stays at zero.

The usual suspects:

| Pattern | Why it breaks caching |
|---|---|
| `datetime.now()` in the system prompt | New prefix every request |
| A UUID or request ID near the top | Same |
| `json.dumps(d)` without `sort_keys=True` | Key order can vary between runs |
| Tools built per user or per session | Tools render first — nothing after them caches |
| Adding or removing a tool mid-session | Invalidates the whole prefix |

### The fix is ordering, not markers

Put stable content first and volatile content last. That is the whole technique.

If Rover needs to know the date, it does not go in the system prompt. It goes in the message,
at the end, where it invalidates nothing:

```python
messages.append({
    "role": "user",
    "content": f"[today is {date.today()}]\n\n{user_message}",
})
```

Same information. Same behaviour. Full cache hits.

### Checking your work

There is no way to tell by reading. Measure — and the field names are provider-specific, so
look yours up once:

| Provider | Where the cache hit shows up |
|---|---|
| Anthropic | `usage.cache_read_input_tokens` and `usage.cache_creation_input_tokens` |
| OpenAI | `usage.prompt_tokens_details.cached_tokens` |
| Gemini | `usage_metadata.cached_content_token_count` |

`reply.raw` gives you the untouched response, which is where these live:

```python
reply = llm.send(messages, TOOLS)
print(reply.raw.usage)          # look once, find your provider's field, then track it
```

By turn three of any session, most of your input should be cache reads. If it is zero, you
have an invalidator, and it is nearly always in the first thousand tokens.

One trap that catches people on every provider: **the plain input-token count is not your
prompt size once caching is on.** It is only the uncached remainder. Add the cached figures in
too, or you will badly under-read your own usage and think a long session is cheaper than it
is.

> Caching is a prefix match. Stable content first, volatile content last, and check
> `cache_read_input_tokens` — a broken cache is silent.

### Try this before the next lesson

Add `cache_control` and print the cache fields every turn.

Then deliberately put `datetime.now()` at the top of your system prompt and watch the reads
drop to zero. Take it out and watch them come back. Ten seconds of work, and you will never
mis-diagnose this again.

---

## Lesson 6.3 — Clearing old tool results without losing the thread

### Try this first

Look at a long transcript. Find the `read_file` from turn two.

The model has since edited that file twice. That result is now wrong, and it is still there,
still being resent, still competing for attention with the current state.

### Stale results are worse than large ones

Two separate problems, and the second is underrated.

**Cost.** You pay for it every turn.

**Contradiction.** The transcript now contains two versions of the same file. The model has to
work out which is current, and sometimes gets it wrong — reporting a function that was
deleted, or re-fixing something already fixed.

### Clearing them yourself

The transcript is your list, so this is a function you write. Twelve lines:

```python
def clear_old_tool_results(messages, keep_last=6):
    """Blank out tool results older than the last `keep_last` messages."""
    cutoff = max(0, len(messages) - keep_last)
    for m in messages[:cutoff]:
        if m["role"] == "tool_results":
            for r in m["results"]:
                r["content"] = "[older result removed to save context]"
    return messages
```

Note what it does **not** do. It does not delete the message. The turn is still there, the
tool call still happened, only the stale contents are gone.

That distinction matters. The model still knows it read `agent.py` at turn two. It just no
longer has the old text in front of it, so it re-reads when it needs to — which is exactly the
behaviour you want, because the file has changed since.

### Some providers will do it for you

Anthropic has a context-editing feature that clears old tool results server-side:

```python
# Anthropic-specific. Same idea as the function above, done for you.
response = client.beta.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    betas=["context-management-2025-06-27"],
    context_management={"edits": [{"type": "clear_tool_uses_20250919"}]},
    tools=TOOLS,
    messages=messages,
)
```

Use it if you are on that provider and it fits. The reason we wrote the function first is that
now you know precisely what such a feature does, and you can decide whether its policy — which
results, how old — is the one you want.

### Clearing versus summarising

This is the distinction to keep straight:

| | **Context editing** | **Compaction** (next lesson) |
|---|---|---|
| Does what | Deletes old tool results | Replaces old turns with a summary |
| Keeps structure | Yes | No — turns are collapsed |
| Costs | Nothing | A model call to write the summary |
| Loses | The content of old results | Detail, and possibly something important |
| Reach for it | Tool output is your bulk (usually) | The conversation itself is long |

Reach for clearing first. It is cheaper, it is lossless in the sense that matters (the model
can re-read anything it needs), and per Lesson 6.1 tool results are most of your transcript
anyway.

### One caution, whichever way you do it

Clearing rewrites part of the transcript, which means it **changes the prefix** — and Lesson
6.2 just taught you what that does to your cache. Everything after the edit point has to be
processed fresh.

So clear in occasional large batches rather than every turn. Clearing one result per turn is
the worst of both worlds: you save a little context and pay a cache miss every single time,
which usually costs more than you saved.

> Clearing removes stale tool output while keeping the shape of the conversation. It is the
> first thing to reach for, and it is the cheapest.

### Try this before the next lesson

Run a fifteen-turn task, then again with clearing on.

Compare total input tokens and check the answer is still correct. Then look for the moment the
model re-reads a file it had already read — that is the mechanism working, not failing.

---

## Lesson 6.4 — Compaction: throwing away the right things

### Try this first

Have a long conversation with Rover — twenty turns of genuine back-and-forth, not just tool
calls.

Now clearing will not save you. There are no large tool results left. The conversation itself
is the bulk, and every turn of it might matter.

### What compaction does

It replaces the earlier part of the conversation with a summary of that part, written by the
model, and keeps going.

You can do this yourself — and in a moment we will argue you usually should. Some providers
also offer it as a feature that triggers automatically as the conversation grows.

### If your provider offers it, read the rules carefully

Automatic compaction is convenient and it has a sharp edge, which is worth seeing once even if
you never use the feature.

When compaction happens, the provider's reply contains **more than text** — there is a marker
recording what the compacted history was replaced with, and it has to go back on the next
request. Keep only the text and you silently throw the marker away. The conversation then
appears to forget everything from the compacted section, with no error.

That is the same failure shape as Lesson 2.6 and the same fix as Lesson 1.6: **append what
came back, not a piece of it.** Any time a provider puts state in its reply, extracting one
field and discarding the rest will break something three turns later.

Because these features are provider-specific, versioned, and move faster than anything else in
this course, look up your own provider's current documentation rather than trusting a code
sample — including one printed here.

### What compaction costs you

It is not free, in two ways.

**A model call.** Something has to write the summary.

**Detail, chosen by someone else.** A summary is lossy by definition, and you do not control
what survives. The exact error message from turn four, the specific file path, the thing the
user said not to do — any of them can be summarised away.

That is the real risk. Not that it forgets everything, but that it forgets the one constraint
that mattered while remembering the general shape of the work.

### Compact deliberately instead

Because of that, hand-rolled compaction is often better for a specific agent. You know what
matters in your domain; the summariser does not.

You already wrote this in Lesson 4.6:

```python
messages.append({"role": "user", "content":
    "Summarise this session for a fresh start. Include: the original task, "
    "files changed and how, what failed and why, and constraints the user gave. "
    "Be specific about file names and error messages."})
```

That prompt names what must survive. It is the difference between a summary that keeps the
useful things and one that keeps the readable things.

Then rebuild the list with the summary at the front and the last few turns intact:

```python
messages = [
    {"role": "user", "content": f"Earlier work on this task:\n\n{summary}"},
    *messages[-4:],
]
```

Keeping the recent turns verbatim matters. The summary carries the history; the last few turns
carry exactly where you are.

### Which to use

| Situation | Use |
|---|---|
| A general assistant, unpredictable conversations | Automatic compaction |
| A specific agent where you know what matters | Your own summary prompt |
| Bulk is tool output, not conversation | Neither — clear instead (6.3) |

> Compaction trades detail for room, and you do not choose what is lost. When you know what
> must survive, say so yourself.

### Try this before the next lesson

Run a long session with automatic compaction on. Afterwards, ask about a specific detail from
early in the conversation.

Note what survived and what did not. Then do the same with your own summary prompt naming that
detail as important. The difference is the argument for writing your own.

---

## Lesson 6.5 — Files as memory: what to write down, and when

### Try this first

Close Rover. Open it again. Ask it what you were working on.

Nothing. Every session starts from zero, because the transcript was the only memory and you
just threw it away.

### Memory is a file

Everything so far has been about one session. Memory is about the next one, and the mechanism
is unglamorous: **the agent writes things to a file, and reads that file next time.**

That is it. There is no special storage. Give it a tool:

```python
MEMORY = Path("MEMORY.md")


def remember(note):
    """Append a note for future sessions."""
    with open(MEMORY, "a") as f:
        f.write(f"- {note}\n")
    return f"Noted: {note}"
```

And load it at the start:

```python
if MEMORY.exists():
    system += f"\n\nThings you learned in earlier sessions:\n{MEMORY.read_text()}"
```

Two functions. That is a persistent agent.

### Some providers define a memory tool for you

Anthropic, for example, has a pre-defined memory tool you switch on rather than describe:

```python
# Anthropic-specific.
{"type": "memory_20250818", "name": "memory"}
```

It is **client-executed** — you still write the storage, exactly as above. What you get is a
standard set of operations the model is already familiar with, instead of an interface you
designed.

Use one if your provider has it and you want a full memory directory. Use the two functions
above when you want to understand what is happening, which is now — and when you want the same
code to work on every provider.

### The hard part is not storage

Writing to a file is easy. Deciding *what* to write is the entire problem, and agents get it
wrong in both directions.

**Writing too much.** Every session appends five notes. After a month, `MEMORY.md` is nine
hundred lines, it goes into the system prompt on every request, and it is now a context
problem pretending to be a memory feature.

**Writing the wrong thing.** "The user asked me to fix the login bug." That was true on
Tuesday. It is noise now.

### What is worth remembering

The test: **would this still be true and useful next month?**

| Worth writing | Not worth writing |
|---|---|
| "Tests are run with `make test`, not pytest directly" | "The user asked me to fix a bug" |
| "The API client is in `lib/http.py`, not `api/`" | "I read three files" |
| "Do not edit `generated/` — it is rebuilt from schema.sql" | "The tests passed" |
| "The user prefers small commits with a body" | "I was working on the login page" |

Left column: durable facts about the project and the person. Right column: events, which the
transcript already covered and which expire.

That distinction is worth putting in the tool description, because the model applies it:

```python
"description": (
    "Save something for future sessions. "
    "Only save durable facts about this project or the user's preferences — "
    "things that will still be true next month. "
    "Do not save what you did today; that is not useful later."
)
```

### Keep it small on purpose

Memory is loaded into every request, so it competes directly with the work. Two habits:

**Update rather than append.** If a note is wrong, fix it. Do not add a correction underneath
and leave both.

**Cap it.** A hard limit — fifty lines, say — forces the question "is this worth more than
what it displaces?" every time.

An agent's memory file should read like a good README, not a diary.

> Memory is a file the agent writes and reads. The mechanism is trivial; deciding what
> deserves a line is the whole skill.

### Try this before the next lesson

Add the memory tool with the description above. Use Rover for three real sessions on the same
project.

Then read `MEMORY.md`. Delete every line that fails the "still true next month" test. What is
left is what your description should have asked for — tighten it.

---

## Lesson 6.6 — Sub-agents: one job, one clean context

### Try this first

Ask Rover something that needs a lot of reading:

> "Which file defines the permission check, and what does it do?"

It reads six files. All six are now in your transcript forever, and you wanted one sentence.

### The idea

Start a second agent with a fresh transcript, give it one job, and take back only the answer.

```python
CHEAP = connect("ollama:gemma4")      # or any cheaper/faster model you have


def sub_agent(task, tools, llm=CHEAP):
    """Run a task in a fresh context. Return only the final text."""
    messages = [{"role": "user", "content": task}]

    for _ in range(10):
        reply = llm.send(messages, tools)
        messages.append({"role": "assistant", "content": reply.text,
                         "tool_calls": reply.tool_calls})

        if not reply.wants_tool:
            break

        results = []
        for call in reply.tool_calls:
            output, failed = run_tool(call.name, call.arguments)
            results.append({"id": call.id, "content": output, "is_error": failed})
        messages.append({"role": "tool_results", "results": results})

    return reply.text
```

That is Module 1's loop, in a function, returning a string.

Then expose it as a tool:

```python
{
    "name": "investigate",
    "description": (
        "Ask a helper to look into a question that needs reading several files, "
        "and get back a short answer. "
        "Use this for wide searches so the details do not fill up your own context."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "A specific, self-contained question."}
        },
        "required": ["question"],
    },
}
```

Six files get read. Six file contents land in the sub-agent's transcript, which is discarded.
One sentence comes back to yours.

### Why a cheaper model

Note that `sub_agent` takes its own `llm`, and the default is a cheap one.

Searching and reading is mostly input tokens and little hard reasoning. That is exactly the
work to move to a cheaper model — or to a local one, which costs nothing at all. The main
agent keeps the strong model for planning, judgement, and writing code.

This is also why `connect()` returns an object rather than setting a global. Two agents, two
models, in one program.

This is the practical version of the point in Lesson 7.5: one agent, more than one model,
chosen per job.

### When it is worth it

| Good fit | Bad fit |
|---|---|
| Reading many files to answer one question | Anything needing two tool calls |
| Independent work that can run in parallel | Work needing the main conversation's context |
| Bulk that would otherwise fill your context | A task you could finish directly |

The failure mode is over-use. Every sub-agent costs a round trip and a re-briefing, and it
starts with **no** context — it does not know what you discussed, what the user prefers, or
what has been tried. Every one of those must be in the question.

That is why the description says "specific, self-contained". A sub-agent asked "check if that
works" has no idea what "that" is.

### The trade

You are trading detail for room. The main agent gets one sentence instead of six files — which
is the point, and also the risk. If the sentence is wrong or incomplete, the main agent has no
way to notice, because the evidence was discarded.

Use sub-agents for gathering, not for judgement. "Which file defines X?" is a good delegation.
"Is this code correct?" is not.

> A sub-agent is your loop in a function with a fresh transcript. It buys context room by
> throwing away evidence — so delegate gathering, not judgement.

### Try this before the next lesson

Add `investigate` and ask the six-file question both ways.

Compare the transcript sizes and the answers. Then ask a question that needs context from your
conversation, and watch the sub-agent flounder because it was not told. That failure is the
description doing its job badly, and it is fixable.

---

## Lesson 6.7 — Lab: give Rover a memory and a summariser

### The plan

Everything from this module, in the working agent. Four changes, in order of what they buy
you.

### 1. Caching (biggest win, smallest change)

Move anything volatile out of the system prompt, then turn caching on:

```python
SYSTEM_PROMPT = """You are Rover, a coding assistant working in a project folder.
Prefer search_files before reading whole files.
Always read a file before editing it."""          # nothing dynamic in here

reply = llm.send(messages, TOOLS, system=SYSTEM_PROMPT)
```

Then switch caching on the way your provider wants it (Lesson 6.2) — or, on OpenAI, simply
benefit from it now that the prefix is stable.

Dynamic things — the date, the folder, the user — go into the first user message.

**Check:** by turn three, `cache_read_input_tokens` should be most of your input.

### 2. Clearing

```python
if turn > 0 and turn % 5 == 0:
    messages = clear_old_tool_results(messages, keep_last=6)
```

Every fifth turn, not every turn — clearing invalidates the cache from that point, so batching
it keeps both features working together.

**Check:** total input tokens on a fifteen-turn task should drop noticeably.

### 3. Memory

```python
MEMORY = Path("MEMORY.md")

if MEMORY.exists():
    SYSTEM_PROMPT += f"\n\nFrom earlier sessions:\n{MEMORY.read_text()}"
```

Plus the `remember` tool from 6.5, with the durable-facts description.

**Check:** run three sessions. Session three should know something from session one without
being told.

Note where it goes: **in the system prompt**, which is cached. Memory is stable content, so it
belongs in the stable part. Putting it in the last message would work and would waste the
cache.

### 4. The handover summariser

```python
def handover(messages):
    messages = messages + [{"role": "user", "content":
        "Summarise for a fresh session: the task, files changed and how, "
        "what failed and why, and any constraints the user gave. "
        "Be specific about file names and error messages."}]

    return llm.send(messages).text
```

Wire it to a turn threshold or a key press:

```python
if turn == 20:
    summary = handover(messages)
    messages = [
        {"role": "user", "content": f"Earlier work on this task:\n\n{summary}"},
        *messages[-4:],
    ]
```

**Check:** run past turn twenty and confirm it still knows the task.

### Measure the whole thing

Run one realistic task — say fifteen turns of real work — three times:

| Configuration | Total input tokens | Cost | Still correct? |
|---|---|---|---|
| Module 5's Rover | | | |
| Caching only | | | |
| All four | | | |

Fill it in with your own numbers. Two things usually come out of this table.

The caching row is a much bigger jump than people expect, for four lines of code.

And the third row must keep the "still correct?" column honest. Every technique here trades
information for room. If the answers got worse, you cleared too aggressively or summarised
away something that mattered — and finding that out is the point of the column.

> Caching first, clearing second, memory third, summarising last. Measure after each, and
> keep checking whether the answers are still right.

### Try this before the next module

Take the numbers from your table into Module 7.

You have just made four changes and formed opinions about them from a handful of runs. Module
7 is about whether those opinions are true — and the "still correct?" column is exactly the
thing you are about to learn to measure properly.

---

## Production notes (not for learners)

- **No video.** Nothing moves. Two diagrams, both reused from earlier modules.
- **Diagram 1 (Lesson 6.1): the growing transcript.** Reuse the Module 1 artwork (Diagram 2
  from 1.5) with the cost curve added underneath. Learners should recognise it and feel the
  callback.
- **Diagram 2 (Lesson 6.2): the prefix.** `tools → system → messages` as a bar, with the cache
  boundary marked and a timestamp near the left end colouring everything after it red. This is
  the one image that makes the invalidation rule obvious.
- **The four-way distinction in the module intro is load-bearing.** Caching / clearing /
  compaction / memory get confused constantly, including in other people's documentation. If
  the intro gets trimmed, the rest of the module reads as four similar things.
- **6.2's deliberate-break exercise is the best thirty seconds in the module.** Insert
  `datetime.now()`, watch reads go to zero, remove it, watch them return. Keep it.
- **6.4 no longer prints a compaction code sample.** Auto-compaction is provider-specific and
  versioned, and the first draft shipped a beta flag (`compact-2026-01-12`) that is **not** in
  the Anthropic SDK's known-beta list — caught by introspection, never by a live call. The
  lesson now teaches the trap (append what came back, not one field of it) without a sample
  that would rot. If anyone wants the sample restored, verify the flag against a live call
  first.
- **6.7's measurement table is the module's assessment.** It is also the setup for 7.2, so
  keep the "still correct?" column even though it is the hardest one to fill honestly — that
  difficulty is precisely what motivates the next module.
- **Check before shipping:** the per-provider caching table in 6.2 (does OpenAI still cache
  automatically, does Gemini still use a separate API), the usage field names in 6.2's
  measurement table — `cache_read_input_tokens` / `prompt_tokens_details.cached_tokens` /
  `cached_content_token_count` — and the two Anthropic-specific samples that remain, which are
  clearly labelled as such: `context-management-2025-06-27` with `clear_tool_uses_20250919`,
  and `memory_20250818`. Verified 2026-08-12 against `anthropic` 0.121.0. This module still has
  more version-sensitive strings than any other.
