# Module 4 — When the loop goes wrong

*Recovery cannot be taught in prose. This module is video-first.*

In Lesson 3.6 Rover told you it had added a tool, and it had added half of one. Nothing
errored. No exception, no warning, no failed check. It said it was done, and it was not.

That is the failure this module is about, along with its relatives: the loop that never stops,
the reply that was cut off, the command that failed into silence. None of them raise. All of
them need code you have not written yet.

---

## Lesson 4.1 — It never stops: turn limits and the runaway loop

### Try this first

Give Rover a task with no clear finish:

> "Improve the code in agent.py. Keep improving it until it is perfect."

Watch it. It reads, edits, reads again, edits again. It is not stuck — each turn does
something. It just has no way to decide that it is finished, because you gave it a goal with
no end state.

Stop it with Ctrl-C before your credit does something you regret.

### What you just did

The loop from Module 1 has no exit except the model's own choice:

```python
while True:
    reply = llm.send(messages, TOOLS)
    if not reply.wants_tool:
        break
```

If the model keeps asking for tools, that loop keeps running. Forever. Every iteration costs a
full API call with the entire transcript resent.

This is the first thing to add to any agent that runs unattended, and it is one line.

### The fix

```python
MAX_TURNS = 25

for turn in range(MAX_TURNS):
    reply = llm.send(messages, TOOLS)
    ...
    if not reply.wants_tool:
        break
else:
    print(f"[stopped after {MAX_TURNS} turns without finishing]")
```

The `for ... else` runs the `else` only if the loop finished without `break` — which is
exactly the runaway case, and reads better than a counter and a flag.

### Choosing the number

There is no correct value, but there is a way to pick one.

Run your real tasks and record how many turns each takes. Set the limit to roughly double the
worst honest case. If ordinary work takes four to eight turns, twenty-five gives room for a
hard task and still catches a loop within a minute.

Then treat hitting the limit as a signal, not just a stop. A task that suddenly needs thirty
turns when it used to need six has told you something — usually that a tool started failing,
or a description changed and the model is now flailing.

### Not every long run is a loop

Two different situations look identical from outside:

| What you see | What it might be | How to tell |
|---|---|---|
| Turn 15, still going | A genuinely hard task | Each turn does something new |
| Turn 15, still going | A loop | The same tool call, with the same arguments, repeating |

The second is worth detecting on its own, because it is common and it is cheap to catch:

```python
recent = []          # last few (name, arguments) pairs

signature = (call.name, json.dumps(call.arguments, sort_keys=True))
if recent.count(signature) >= 3:
    output, failed = (
        "You have already called this tool with these exact arguments three times "
        "and got the same result. Try something different, or stop and explain "
        "what is blocking you."
    ), True
recent.append(signature)
recent = recent[-10:]
```

Note the message. It does not just refuse — it tells the model what pattern it is stuck in and
gives it two ways out. Often it takes the second one, and explains the blocker, which is
usually more useful than the task succeeding.

> A turn limit stops the bleeding. A repeat detector tells you why it was bleeding.

### Try this before the next lesson

Add both. Then run the "keep improving it until it is perfect" task again.

Watch which one fires. On most runs it is the turn limit, because the model varies its edits
enough to dodge the repeat check. That tells you the two guards are catching different things,
and you want both.

---

## Lesson 4.2 — It stops too early: finished talking, half a job done

### Try this first

Ask Rover to do three things in one message:

> "Add a `word_count` tool to agent.py, add a test for it in test_agent.py, and update
> README.md to mention it."

Then check all three files.

On a good number of runs, two are done and one is not, and Rover's final message says all
three are complete.

### What you just saw

Go back to Lesson 1.5. A reply with no tool calls means the model stopped talking.

That is all it means. It does not mean the task is complete, the files are correct, or the
claim in the final message is true. Those are facts about the world, and the reply is a fact
about the conversation.

This is the single most expensive misunderstanding in agent work, because the failure is
*confident*. A crash tells you it failed. This tells you it succeeded.

### Why it happens

Not because the model is careless. Three ordinary mechanisms:

**It lost track.** Three tasks, twelve tool calls, a long transcript. Item two scrolled out of
the model's attention somewhere around turn eight.

**It thinks it did.** It wrote the edit, the edit did not apply cleanly, and it did not
re-read the file. Its belief about the file is stale, and its report is honest — about a file
that does not exist.

**The task was ambiguous.** "Update README.md to mention it" is done by adding one line. It
added one line. You expected a section.

None of those are lies. All of them produce a false completion claim.

### The fix is not a better prompt

You can improve this with prompting. "Verify each step before reporting completion" helps.
It does not solve it, because you are asking the thing that is mistaken to check whether it is
mistaken.

The fix is that **you** check. In code. Outside the model.

```python
def verify(checks):
    """checks: list of (description, callable returning bool)."""
    failures = [desc for desc, check in checks if not check()]
    if not failures:
        return None
    return "These are not done yet:\n" + "\n".join(f"- {f}" for f in failures)
```

And in the loop, when the model wants to stop:

```python
if not reply.wants_tool:
    problem = verify(CHECKS)
    if problem is None:
        break
    messages.append({"role": "user", "content": problem})
    continue          # send it back with the real state of the world
```

Now "I have finished" is a *proposal*, which your code accepts or rejects.

### What a check looks like

Cheap and concrete. The point is that they run outside the model:

```python
CHECKS = [
    ("word_count is defined in agent.py", lambda: "def word_count" in read("agent.py")),
    ("word_count is in the TOOLS list", lambda: '"word_count"' in read("agent.py")),
    ("there is a test for it", lambda: "word_count" in read("test_agent.py")),
    ("agent.py still imports", lambda: run("python3 -c 'import agent'") == 0),
]
```

The last one is the best kind: it does not check whether the model did what it said, it checks
whether the result actually works.

### The general principle

This is the same idea as tests, and it arrives for the same reason. You do not trust a
confident report about code. You run something.

For an agent it matters more, because an agent produces confident reports as its normal
output, in fluent English, with no signal distinguishing an accurate one from a wrong one.

> A reply with no tool calls is a proposal to stop, not proof of completion. Something outside
> the model has to decide whether the work is done.

### Try this before the next lesson

Write three checks for the three-part task above, and wire them in.

Then run the task five times and record how often the verify step fires. That number is the
most useful thing you will measure in this module — and in Module 7 you will make it a
permanent one.

---

## Lesson 4.3 — The stop reasons nobody handles

### Try this first

Search your `agent.py` for `reply.stop`. Count how many values you do something about.

Most agents handle one situation — "does it want a tool?" — and treat everything else as an
answer. Three other things can happen, and each one fails in a way that looks like a bug in
your code rather than a normal outcome.

### Every provider has its own words

This is the one place in the course where the vocabulary genuinely differs, so here is the
whole map:

| What happened | OpenAI / Ollama | Anthropic | Gemini |
|---|---|---|---|
| Finished normally | `stop` | `end_turn` | `STOP` |
| Wants a tool | `tool_calls` | `tool_use` | `STOP` — check the calls |
| **Cut off at your limit** | `length` | `max_tokens` | `MAX_TOKENS` |
| **Declined the request** | `content_filter` | `refusal` | `SAFETY` and others |

`reply.stop` gives you the provider's own word. Recognise your own column, and remember from
Lesson 1.5 that the Gemini row is why `wants_tool` looks at the calls rather than the word.

### The three that bite

**The reply was cut off.**

The reply looks normal. The text is truncated mid-sentence. If a tool call was being written
when the limit hit, its arguments may be incomplete too.

```python
CUT_OFF = {"length", "max_tokens", "MAX_TOKENS"}

if reply.stop in CUT_OFF:
    print("[reply cut off — raise max_tokens]")
    # Do not treat the text as an answer, and do not run a partial tool call.
    break
```

The fix is a bigger limit, or a task split into smaller pieces. What you must not do is carry
on as if the reply were complete.

**The model declined.**

The request hit a safety boundary. This is usually a normal, successful HTTP response — not an
exception — with the refusal in the stop reason and the text empty or partial. That is what
makes it dangerous: code that reads the text unconditionally crashes or reports nonsense.

```python
DECLINED = {"content_filter", "refusal", "SAFETY", "PROHIBITED_CONTENT"}

if reply.stop in DECLINED:
    print(f"[the model declined this request: {reply.stop}]")
    break
```

Two rules. **Check the stop reason before using the text.** And **do not retry the same
prompt** — it will be declined again. Change the request or stop.

Benign work occasionally trips this, especially security tooling. Some providers offer a way
to re-run a declined request on a different model automatically; if yours does and you need
it, that is where to look.

**It paused part-way.**

Some providers pause a long turn and expect you to ask for the rest, rather than finishing in
one reply. Append the assistant turn and send again with no new user message:

```python
if reply.stop in {"pause_turn", "PAUSE"}:
    messages.append({"role": "assistant", "content": reply.text,
                     "tool_calls": reply.tool_calls})
    continue          # no new user message — it resumes on its own
```

Do not add a "please continue" message. The provider sees the paused turn and resumes; an
extra user message just confuses the transcript.

### Handle them all in one place

```python
if reply.wants_tool:
    ...                      # run tools, append results, continue
elif reply.stop in PAUSED:
    continue                 # resume
elif reply.stop in CUT_OFF:
    print("[reply was cut off]")
    break
elif reply.stop in DECLINED:
    print("[the model declined this request]")
    break
else:
    ...                      # verify, then break
```

Ten lines. That is the difference between an agent that fails clearly and one that fails
mysteriously.

Note the order. `wants_tool` is checked **first**, before any stop word, because of the Gemini
problem from Lesson 1.5 — a provider can report "finished normally" while asking for a tool,
and checking words first would silently drop the request.

> Three outcomes are silent failures if you ignore them, and every provider names them
> differently. Know your own column, and check for tool calls before you check for words.

### Try this before the next lesson

Force each one:

- cut off: set `max_tokens` to 30 and ask for a long answer.
- declined: hard to force deliberately, and you should not try very hard. Just make sure the
  branch exists and does not crash on empty content.
- paused: skip until Module 5, when Rover talks to external services.

Then re-read your handler. If any branch uses `reply.text` before checking `reply.stop`, fix it now.

---

## Lesson 4.4 — Feeding failure back: stderr is input, not an exception

### Try this first

Ask Rover to run a command that fails:

> "Run `python3 -c 'import nosuchmodule'` and tell me what happens."

If your `bash` tool from Lesson 3.3 returns stdout, stderr, **and** the exit code, Rover reads
the `ModuleNotFoundError` and explains it. If it returns only stdout, Rover gets an empty
string and tells you the command worked.

Same command. Same failure. The difference is entirely in what you chose to send back.

### The principle

An agent's ability to recover is bounded by the quality of the failure information you give
it. Not by the model. By your tool result.

That is worth stating as a design rule:

> Everything that would help a person debug this should go in the tool result.

For a shell command, that means exit code, stdout, and stderr. For an HTTP call, the status
code and the response body. For a file operation, what was attempted and what exists instead.

### The recovery loop

Here is the pattern that makes agents feel capable:

```
model proposes → your code runs it → it fails
             → you send back the error
             → model reads the error and adjusts
             → your code runs the new version → it works
```

Nothing in that loop is new. It is Module 1's loop, with useful failure text in the tool
result. That is all "self-healing agent" means.

You can watch it work:

```
[bash] python3 -c "import nosuchmodule"
exit code 1
ModuleNotFoundError: No module named 'nosuchmodule'

[bash] pip install nosuchmodule
exit code 1
ERROR: Could not find a version that satisfies the requirement nosuchmodule

Rover: That module does not exist on PyPI. Did you mean a different name?
```

Two failures, and the second one produced the correct conclusion. Neither turn needed you.

### Where to trim

Errors can be enormous. A failing test suite produces thousands of lines, and all of it lands
in your transcript and gets resent every turn afterwards.

Trim with intent:

```python
def trim(text, limit=4000):
    if len(text) <= limit:
        return text
    head, tail = text[:1000], text[-3000:]
    return f"{head}\n\n[... {len(text) - 4000} characters trimmed ...]\n\n{tail}"
```

Keep the head and the tail. The head has the command and the first failure; the tail has the
summary line and the last error, which is usually the one that matters. The middle is
repetition.

And say that you trimmed. A silent truncation makes the model reason about a test suite it
thinks had four failures when it had four hundred.

### What not to send back

**Raw Python tracebacks from your own agent code.** If `run_tool` throws because of a bug in
*your* code, that is your problem, not the model's. Send a short message; keep the traceback
in your log.

**Secrets.** Error messages leak connection strings, tokens, and paths. Once one is in the
transcript it is resent on every turn for the rest of the session, and there is no way to take
it back.

### Try this before the next lesson

Break something on purpose. Introduce a syntax error into a file Rover is working on, then ask
it to run the tests.

Watch the loop: run, fail, read, fix, run. Then take the exit code out of your bash result and
run it again. Watch the recovery stop working. That contrast is the lesson.

---

## Lesson 4.5 — Watching a run: the log you will actually read

### Try this first

Run Rover on a ten-turn task and try to answer this afterwards: *which tool call changed
`agent.py`?*

You cannot. The terminal has scrolled, the tool output was long, and everything looks the same.

### What a useful log looks like

Not this:

```
DEBUG:anthropic:request POST /v1/messages
DEBUG:anthropic:response 200
```

That tells you the HTTP worked. You already knew that.

A useful agent log records **decisions and effects** — one line per event, scannable:

```
turn 3  think  (2 blocks)
turn 3  tool   read_file {"path": "agent.py"}          -> 4.1 KB
turn 4  tool   str_replace {"path": "agent.py", ...}   -> ok, 1 replacement
turn 4  tool   bash {"command": "python3 -c 'import agent'"}  -> exit 1  ERROR
turn 5  tool   read_file {"path": "agent.py"}          -> 4.2 KB
turn 5  tool   str_replace {"path": "agent.py", ...}   -> ok, 1 replacement
turn 6  tool   bash {"command": "python3 -c 'import agent'"}  -> exit 0
turn 7  stop   end_turn   (verify: passed)
```

Read that. You can see the whole run: it edited, the import broke, it re-read the file, fixed
it, checked again, and stopped. Seven turns in eight lines.

### The implementation

```python
import json


def log(turn, kind, detail, result=""):
    line = f"turn {turn:<3} {kind:<6} {detail}"
    if result:
        line += f"  -> {result}"
    print(line, flush=True)
    with open("rover.log", "a") as f:
        f.write(line + "\n")
```

Called at three points:

```python
log(turn, "tool", f"{call.name} {json.dumps(call.arguments)[:80]}", summarise(output, failed))
log(turn, "stop", reply.stop, f"verify: {'passed' if ok else 'FAILED'}")
log(turn, "usage", f"in={reply.usage.get('in')} out={reply.usage.get('out')}")
```

Where `summarise` turns a tool result into a few words — `ok`, `exit 1 ERROR`, `4.1 KB`,
`no matches` — never the whole output. The full output belongs in the transcript, not the log.

### Log the arguments, truncated

`read_file` tells you nothing. `read_file {"path": "agent.py"}` tells you what happened.

Truncate hard — eighty characters — because a `str_replace` argument can be a whole function
and will drown the log it is supposed to make readable.

### Log the usage line

One line per turn with input and output tokens. It costs nothing and it answers the question
you will eventually ask: *where did the money go?*

You will see input tokens climbing every turn even when nothing much happens. That is the
transcript growing, which is Module 6.

### The two logs

Worth separating from the start:

| Log | Contents | For |
|---|---|---|
| Console | One line per event | Watching a run happen |
| File | The same lines, plus the full transcript as JSON | Working out what went wrong afterwards |

Dump the whole `messages` list to a JSON file at the end of a run. When something behaves
strangely three turns in, that file is the only artifact that can tell you why — and it is the
exact input the model saw.

> Log decisions and effects, one line each. If you cannot reconstruct a run from your log,
> you cannot debug your agent.

### Try this before the next lesson

Add the log. Run the three-part task from Lesson 4.2.

Then read only the log — not the terminal output — and write down what happened. If you cannot
tell, add whatever line was missing. That is how you find out what your log needs.

---

## Lesson 4.6 — Interrupting, redirecting, and starting again

### Try this first

Run Rover on a longish task, and about four turns in, notice it is doing the wrong thing.

What are your options right now? With the code as it stands: Ctrl-C. That is the whole
interface. You lose the session and start over.

### Three things you actually want

| You want to | Because | What it needs |
|---|---|---|
| Interrupt | It is going the wrong way | Stop cleanly, keep the transcript |
| Redirect | It is close, one correction needed | Add a user message, continue |
| Restart | The context is a mess | Fresh transcript, keep what was learned |

All three are small changes to the loop, and all three depend on something you already have:
the `messages` list is yours.

### Interrupt

```python
try:
    output, failed = run_tool(call.name, call.arguments)
except KeyboardInterrupt:
    output, failed = "The user interrupted this. Stop and wait for instructions.", True
```

Catching Ctrl-C at the tool call and turning it into a tool result means the model finds out
it was interrupted, in the transcript, instead of the process dying.

The session survives. You can now type the correction.

### Redirect

Redirecting is one line, because a transcript is just a list:

```python
messages.append({"role": "user", "content": "Stop editing README. Fix the failing test first."})
```

Append and continue the loop. There is no special mechanism, no API for steering. It is a
conversation, and you can talk in the middle of it.

A prompt after each turn is enough of an interface:

```python
if reply.wants_tool:
    note = input("[enter to continue, or type a correction] ").strip()
    if note:
        messages.append({"role": "user", "content": note})
```

That is a supervised agent. Twelve lines, and it changes how the tool feels to use.

### Restart, without losing what was learned

Sometimes the transcript is beyond saving — twenty turns of a wrong approach, and every future
turn is anchored to it.

Restarting does not have to mean starting from nothing. Ask for a handover first:

```python
messages.append({"role": "user", "content":
    "Summarise for a fresh session: what you were asked, what you tried, "
    "what you learned about this codebase, and what you would do next. "
    "Be specific about file names and what did not work."})

summary = llm.send(messages).text

messages = [{"role": "user", "content":
    f"You are continuing earlier work. Here is what happened:\n\n{summary}\n\n"
    f"Now: {original_task}"}]
```

You have thrown away twenty turns of transcript and kept the findings. The new session is
cheap, focused, and knows what the last one learned.

This is the same idea as compaction in Module 6, done by hand. Doing it manually first is
worth it, because you can see exactly what survived and what did not.

> The transcript is a list you own. Interrupting, correcting, and restarting are all just
> edits to that list.

### Try this before the next lesson

Add the after-each-turn prompt. Use Rover for a real task for ten minutes.

Notice how often you type something. That number tells you whether your tool descriptions are
carrying enough — every correction you type is a description that could have been clearer.

---

## Lesson 4.7 — Lab: break Rover four ways and fix each one

### The exercise

Four failures. For each: reproduce it, watch it fail, then add the guard. Work in a git repo
and commit after each fix, so you can see the four diffs afterwards.

### Break 1: the runaway

```
Improve agent.py. Keep going until it cannot be improved further.
```

**What you see:** it never stops.
**Fix:** `MAX_TURNS` and the repeat detector from 4.1.
**Check:** run it again. It stops, and tells you it hit the limit.

### Break 2: the false finish

```
Add a word_count tool, add a test for it, and mention it in README.md.
```

**What you see:** two of three done, reported as three of three.
**Fix:** the verify step from 4.2, with a check per file.
**Check:** run five times. Count how often verify fires. Write that number down — it is your
first eval result, and Module 7 turns it into a real one.

### Break 3: the silent failure

Take the exit code and stderr out of your `bash` result, so it returns only stdout. Then:

```
Run the tests and fix anything that fails.
```

**What you see:** it reports success. Nothing was fixed. The test command failed and returned
an empty string.
**Fix:** restore exit code, stdout, and stderr, per 4.4.
**Check:** run it again. Watch it read the failure and act on it.

### Break 4: the cut-off reply

Set the output limit to 200 tokens and ask for something long:

```
Explain everything agent.py does, function by function.
```

**What you see:** the answer stops mid-sentence. If your code ignores `reply.stop`, it looks
like the model gave a short answer.
**Fix:** the stop-reason handler from 4.3.
**Check:** run it again. You get a clear `[reply was cut off]` instead of a confusing result.

### Read your four diffs

```bash
git log --oneline
git diff HEAD~4
```

About forty lines of guards. Read them as a group, because they have a shape in common:

Every one turns a **silent** failure into a **loud** one. None of them make Rover smarter. They
make it honest — about stopping, about finishing, about failing, about being cut off.

That is what hardening an agent is. Not better prompts. Not a better model. Code that refuses
to let a failure pass as a success.

### The one that is still missing

You have not fixed the underlying cause of Break 2. You added a check that catches it.

There is no fix for the underlying cause. The model will sometimes believe it did something it
did not, and no prompt reliably prevents that. What you can do is never take its word for it.

That is not a limitation of this model or this year. It is a property of asking a system to
report on itself, and the answer — check from outside — is the same answer as in every other
part of engineering.

> Hardening an agent means turning silent failures into loud ones. You are not making it
> smarter. You are making it honest.

### Try this before the next module

Run all four broken versions once more, with all four guards in place.

Then read `rover.log` for each run. Every failure should be visible in the log without you
having watched it happen. If one is not, your log is missing a line — add it now, because
Module 5 makes the runs longer and harder to watch.

---

## Production notes (not for learners)

- **Three videos, the most in the course.** 4.1 the runaway (short — thirty seconds of it
  looping is enough, and funnier than describing it). 4.2 the false finish, which is the most
  important recording in the whole course. 4.6 interrupt and redirect, because the feel of
  supervising an agent does not survive being written down.
- **4.2's video must be a real take.** Ask for three things, get two, read the confident
  summary out loud, then open the third file and show it empty. Do not stage it. If the model
  completes all three on the first take, film again — over several runs it will fail, and that
  is exactly the point being made.
- **The three-part task in 4.2 and 4.7 is the same task on purpose.** The learner meets it as
  a demonstration, then fixes it as a lab. Keep them identical so the second one feels like
  closure rather than a new exercise.
- **4.7's "count how often verify fires" is the seed of Module 7.** It is a manual eval with a
  sample size of five. When 7.2 arrives, refer back to this number explicitly — the learner
  should feel they already did the thing, badly, and are now doing it properly.
- **Diagram (Lesson 4.4): the recovery loop.** propose → run → fail → error text → adjust →
  succeed. Small, and reused in 4.7. Consider making it the module's thumbnail.
- **Check before shipping: the stop-word table in 4.3 is the most fragile thing in the module.**
  It names values for three providers, and each vendor renames them independently. Verified
  2026-08-12: OpenAI/Ollama `tool_calls`/`stop`/`length`, Anthropic `tool_use`/`end_turn`/
  `max_tokens`/`refusal`, Gemini `STOP` (including when requesting a tool — confirmed by live
  call) and `MAX_TOKENS`. Re-run `verify_providers.py` and read the `stop word on tool turn`
  line for each provider before every ship.
- **The check-order point at the end of 4.3 is load-bearing**, not a stylistic note. Checking
  `wants_tool` before any stop word is what keeps the loop correct on Gemini, and it is the
  payoff for the design decision made back in Lesson 1.5. Keep the cross-reference.
