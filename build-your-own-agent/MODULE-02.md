# Module 2 — Tools: teaching the model what it can do

*The part every tutorial skips. Tool choice is a writing problem before it is a code problem.*

In Module 1 you gave Rover one tool and it used it. That felt like magic, and magic is a bad
foundation.

This module is about what actually happened. The model chose that tool by reading your
description of it. When an agent picks the wrong tool, calls it with nonsense arguments, or
ignores a tool it obviously needed, the cause is almost always in the words you wrote.

---

## Lesson 2.1 — A tool is a description, a schema, and a function

### Try this first

Look at the tool from Lesson 1.7 again, and count the parts:

```python
{
    "name": "read_file",
    "description": "Read a text file from the current folder and return its contents.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "The name of the file"}
        },
        "required": ["path"],
    },
}
```

Three things go to the model: a name, a description, and a schema.

A fourth thing does not go to the model at all: your `read_file` function. The model never
sees it. It has no idea how the tool works, only what you said it does.

### The split that matters

| Part | Who reads it | What it decides |
|---|---|---|
| `name` | The model | How it refers to the tool |
| `description` | The model | **Whether to use it at all** |
| `input_schema` | The model | What arguments to send |
| Your function | Only your code | What actually happens |

The model is choosing from a menu written by you, in English, with no way to test anything.
It cannot call the tool to see what it does. It cannot read your source. It reads the
description and decides.

That is why this module is mostly about writing.

### What the schema is for

`input_schema` is JSON Schema. You are describing the shape of the arguments.

```python
"input_schema": {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "The file to read, for example notes.txt",
        },
        "max_lines": {
            "type": "integer",
            "description": "Stop after this many lines. Leave out to read the whole file.",
        },
    },
    "required": ["path"],
}
```

Two habits to start now.

**Describe every property.** A property with no description is a guess. `max_lines` without
a description could mean lines from the start, lines from the end, or a page size.

**Mark only what is truly required.** Everything in `required` must be sent every time. If a
sensible default exists, leave the property optional and apply the default in your function.

### `enum` is the strongest tool you have

When a parameter has a fixed set of valid values, say so:

```python
"sort_by": {
    "type": "string",
    "enum": ["name", "size", "modified"],
    "description": "Which field to sort the file list by.",
}
```

This does more than document. It removes a whole class of failure, because the model now has
three options rather than an open field. Whenever you catch yourself writing "must be one of"
in a description, that is an `enum`.

> The model chooses a tool by reading a sentence you wrote. Everything else in this module
> follows from that.

### Try this before the next lesson

Take your `read_file` tool and add an optional `max_lines` parameter, with a description.
Implement it in the function.

Then ask Rover: *"Show me the first two lines of notes.txt."* Watch whether it sends
`max_lines`. You did not tell it to. It read the schema and worked out that the parameter
matched the request.

---

## Lesson 2.2 — The description is the instruction manual, and the model reads nothing else

### Try this first

Here are two descriptions of the same function. Predict which one gets used more often.

**A:** `"Search the codebase."`

**B:** `"Search the project's source files for a text pattern and return matching lines with
their file paths and line numbers. Use this when you need to find where something is defined
or used, before reading whole files."`

Now count what B tells the model that A does not:

- What it searches (source files, not the whole disk)
- What comes back (matching lines, paths, line numbers)
- **When to reach for it** (finding where something lives)
- **What to do instead** (this before reading whole files)

A is a label. B is an instruction.

### The rule

A tool description has four jobs, in this order of importance:

1. **When to use it.** The single most valuable sentence. Most descriptions omit it entirely.
2. **What it does**, precisely enough that "does it fit here?" is answerable.
3. **What comes back**, so the model knows what it is getting before it asks.
4. **What it does not do**, when there is a near neighbour it could be confused with.

Three or four sentences is a normal length. One line is almost always too short.

### The mistake that goes the other way

There is an opposite failure, and it is more common in code written a couple of years ago:

```python
"description": "CRITICAL: You MUST use this tool for ALL file operations. NEVER skip this."
```

Shouting used to be necessary. Older models under-used tools, so people compensated with
capital letters. Current models follow instructions closely, so that same text now
**over**-triggers: the tool gets called when it is not needed, on tasks where reasoning would
have been better.

Write the trigger condition plainly and let it land:

```python
"description": (
    "Read a file from the project and return its contents. "
    "Use this when you need the actual text of a file, rather than just its name. "
    "Returns the whole file, so prefer search_files first on large files."
)
```

> Say when to use it, at normal volume. That one sentence does more than any amount of
> emphasis.

### Where to put things that are not descriptions

Two things people jam into descriptions that do not belong there:

**Worked examples and fake dialogue.** They cost tokens on every single request, and they
narrow the model's thinking to the shapes you demonstrated. Make the parameters expressive
instead — a well-named `enum` carries more than a paragraph of examples.

**Instructions about other tools.** `"ALWAYS use this instead of read_file"` in one
description, scattered across a dozen tools, becomes impossible to reason about. A preference
for tool X belongs in X's own description.

### Try this before the next lesson

Take your `read_file` description down to just `"Reads a file."` and ask Rover three questions
that should need it.

Then restore a full description and ask the same three. Note how many times each version
triggered. You have just measured the thing this lesson claims.

---

## Lesson 2.3 — Why it picked the wrong tool, and why that was your fault

### Try this first

Give Rover these two tools at the same time:

```python
{
    "name": "read_file",
    "description": "Read a file.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
},
{
    "name": "get_file_info",
    "description": "Get information about a file.",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
},
```

Now ask: *"How big is notes.txt?"*

Then ask: *"What does notes.txt say?"*

Watch which tool it picks each time. It will get at least one wrong, and it will look
arbitrary.

### What you just did

Read the two descriptions as the model does — as the only information available.

"Read a file" and "Get information about a file". Is the contents of a file information about
the file? Obviously yes. Is size something you get by reading? Arguably.

The boundary between these two tools does not exist in the text. The model is not confused.
**You were ambiguous, and it is guessing.**

### The fix is a boundary, not a warning

The instinct is to add emphasis: `"Get information about a file. NOT the contents."` That
helps a little, and it is the wrong shape of fix.

Say what each one is *for*, and let the boundary fall out:

```python
{
    "name": "read_file",
    "description": (
        "Return the full text contents of a file. "
        "Use this when you need to know what is written inside the file."
    ),
    ...
},
{
    "name": "get_file_info",
    "description": (
        "Return a file's size in bytes and when it was last modified. "
        "Does not return the file's contents. "
        "Use this to check whether a file is large before reading it."
    ),
    ...
},
```

Now the two questions have obvious answers, and one description even tells the model how the
tools work together.

### The three causes of wrong tool choice

When a model picks badly, it is nearly always one of these:

| Symptom | Cause | Fix |
|---|---|---|
| Picks between two similar tools inconsistently | Overlapping descriptions | Name the boundary in both |
| Ignores a tool that obviously applies | No trigger sentence | Add "Use this when..." |
| Calls a tool constantly, including when useless | Emphasis language, or too-broad description | Remove the shouting, narrow the scope |
| Sends wrong argument types | Missing property descriptions, or no `enum` | Describe every property |

Note what is not on that list: "the model is not good enough". That is occasionally true. It
is not the first thing to check, and it is the only item on the list you cannot fix.

### When you have too many tools

Two tools with a fuzzy boundary is a writing problem. Twenty tools with fuzzy boundaries is a
design problem.

If two tools take the same arguments and return similar things, they are usually one tool
with a parameter. Fewer, clearly bounded tools beat a large menu of near-duplicates — for the
model and for you.

> If you cannot state the boundary between two tools in one sentence, the model cannot infer
> it from your descriptions.

### Try this before the next lesson

Write descriptions for `list_files` and `search_files` that make the boundary unambiguous.
Then ask Rover: *"Which file mentions the plumber?"*

It should search, not list. If it lists, your search description has no trigger sentence.

---

## Lesson 2.4 — Returning results: what the model does with what you send back

### Try this first

Take Rover's `read_file` and change the return to this:

```python
def read_file(path):
    with open(path) as f:
        return {"ok": True, "data": f.read(), "bytes": 42}
```

Run it. It will fail, and the error will point at the API call rather than at this function.

### What a tool result must be

The `content` of a `tool_result` is **text**. Not a dict, not an object.

```python
{
    "id": call.id,
    "content": "Buy milk. Call the plumber.",
}
```

If your function produces structured data, you serialise it yourself:

```python
import json

return json.dumps({"size": 4096, "modified": "2026-08-10"})
```

The model reads JSON perfectly well. It just has to arrive as text.

### The result is the model's only view of the world

This is the point of the lesson. What you put in `content` **is** what happened, as far as the
model is concerned. It cannot check. It cannot look at the file itself. Your string is the
entire truth.

That has three consequences worth internalising now.

**Say what happened, not just the data.** A tool that writes a file and returns `""` leaves
the model guessing whether it worked. Return `"Wrote 412 bytes to summary.txt."` The model
then knows, and — importantly — so does anyone reading the transcript later.

**Do not dump everything.** A tool that returns a 40,000-line log costs you on every
subsequent turn, because the whole transcript is resent each time. Return the useful part and
say what you trimmed: `"Last 50 lines of 12,043 (showing the end):"`.

**Give it a next step when there is one.** If a search finds nothing, `"No matches"` is
correct but unhelpful. `"No matches for 'plumber' in 12 files searched. Try a shorter pattern
or check the folder."` gets a better next turn.

### Big results have a safety net

If a tool result is very large, the platform can offload it to a file in the sandbox and give
the model a preview plus a path, rather than pushing the whole thing into context.

That is a backstop, not a design. Deciding what is worth returning is your job, and doing it
well is one of the biggest levers you have on both cost and quality.

> The tool result is the model's only view of what happened. Write it for a reader who cannot
> see anything else.

### Try this before the next lesson

Change `read_file` to return the file contents prefixed with a line saying how many lines it
read. Ask Rover to summarise a file.

Then look at the transcript. That prefix is now part of the conversation forever, resent on
every later turn. Was it worth its size? That question is the whole of Module 6.

---

## Lesson 2.5 — Errors are results too: `is_error`, and how to word a failure

### Try this first

In Lesson 1.6 you asked Rover about a file that does not exist, and the program crashed with
a traceback.

Look at that crash again. Your agent died because a file was missing. A human assistant would
have said "there is no such file" and carried on.

### Errors go back to the model

An exception in a tool is not a program failure. It is information — and the model can act on
it, if you tell it.

```python
def run_tool(name, tool_input):
    try:
        if name == "read_file":
            return read_file(tool_input["path"]), False
        return f"No tool named {name}.", True
    except FileNotFoundError:
        return f"There is no file called {tool_input['path']} in this folder.", True
    except Exception as e:
        return f"The tool failed: {e}", True
```

Then set the flag on the result:

```python
output, failed = run_tool(call.name, call.arguments)
results.append({
    "id": call.id,
    "content": output,
    "is_error": failed,
})
```

`is_error: True` marks the result as a failure. The model then knows this was not a normal
answer, and typically tries something else — listing the folder, or asking you which file you
meant.

### Do not swallow the failure

There is a wrong version of this that looks reasonable:

```python
except Exception:
    return "", False          # never do this
```

An empty string with no error flag tells the model the tool ran and found nothing. It will
happily report that the file is empty. You have converted a crash into a confident lie, which
is strictly worse.

### Word the error for the reader

Compare these three, for the same missing file:

| Message | What the model can do with it |
|---|---|
| `Traceback (most recent call last): ...` | Very little. Noise |
| `FileNotFoundError` | Knows it failed, not why or what next |
| `No file called notes.txt in /home/priya/rover. Files here: agent.py, summary.txt` | Can pick the right file and retry immediately |

The third one costs you three lines and often saves a whole turn.

Two rules for writing them:

**Say what was wrong and what exists.** "Not found" plus the available options beats "not
found" alone almost every time.

**Never put a raw traceback in a tool result.** It is long, it is mostly your source, and it
gets resent on every later turn.

> An error is a result, not a crash. Say what went wrong, and say what could work instead.

### Try this before the next lesson

Add error handling to Rover, then ask it about a file that does not exist.

Watch what it does next. In most runs it will list the folder and find the file you actually
meant — without being told to. That recovery is not the model being clever. It is your error
message being useful.

---

## Lesson 2.6 — Several tool calls in one turn, and the mistake that quietly stops them

### Try this first

Give Rover `read_file` and ask this:

> "Read notes.txt and summary.txt, and tell me if they disagree."

Print what came back:

```python
reply = llm.send(messages, TOOLS)
print([c.name for c in reply.tool_calls])
```

You will see **two** tool calls in one reply.

### What you just did

One assistant turn can contain many tool calls. The model asked for both files at once,
because neither depends on the other. This is normal, it is good, and it is a large part of
why agents feel fast.

Your loop from Lesson 1.7 already handles it — it walks every call and collects every result
before sending anything back. That was not an accident. It was the point.

### The mistake

Here is code that looks equivalent and is not:

```python
# WRONG — one message per result
for call in reply.tool_calls:
    output = run_tool(call.name, call.arguments)
    messages.append({
        "role": "tool_results",
        "results": [{"id": call.id, "content": output}],
    })
```

Run it. It works. No error, no warning, correct answer.

Then keep using it, and over the next few turns the model quietly stops making parallel calls.
It reads its own conversation history, sees that its parallel calls came back split into
separate turns, and adapts to a pattern of one call at a time. Your agent gets slower and
costs more, for no visible reason.

### The rule

**All results from one assistant turn go back in one user message.**

```python
# RIGHT
results = []
for call in reply.tool_calls:
    output = run_tool(call.name, call.arguments)
    results.append({"id": call.id, "content": output})

messages.append({"role": "tool_results", "results": results})
```

One message. A list of results. Every call in the turn gets exactly one matching result, keyed
by its `id`.

If a tool fails, you still return a result for it, with `is_error: True`. Dropping it is not
an option — a missing result for a call id is an error on the next request, on every provider.

### Why this lesson exists

There is no error message. There is no warning. The behaviour degrades over turns, and
nothing points at the cause.

This is the shape of most real agent bugs: not a crash, but a silent behaviour change several
turns after the mistake. Recognising that shape is worth more than memorising this particular
rule.

> Every tool call in a turn gets a result, and all of them travel in one message. Splitting
> them teaches the model to stop calling in parallel.

### Turning it off on purpose

Occasionally you want one call at a time — a tool with side effects where order matters, or a
step that needs approval:

Most providers have a switch for this — Anthropic spells it
`tool_choice={"type": "auto", "disable_parallel_tool_use": True}`, others differ. Check yours.

Use it deliberately, not as a way to avoid writing the loop correctly.

### Try this before the next lesson

Deliberately write the wrong version. Run a session of six or seven turns, asking for two
files each time.

Watch the number of `tool_use` blocks per turn. It usually drops to one within a few turns.
Now you have seen a silent behaviour change with your own eyes, and you will recognise the
next one faster.

---

## Lesson 2.7 — Lab: give Rover four tools, watch it choose, then swap in the SDK's tool runner

### Part one: four tools

Add three tools to Rover, alongside `read_file`. Write the descriptions yourself before
looking at mine.

```python
import json
import os

TOOLS = [
    {
        "name": "read_file",
        "description": (
            "Return the full text contents of a file. "
            "Use this when you need to know what is written inside a file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File to read."}},
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": (
            "List the file names in the current folder. "
            "Use this when you do not know what files exist, or the user names a file "
            "you cannot find."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_files",
        "description": (
            "Search every text file in the current folder for a pattern, and return "
            "matching lines with their file names. "
            "Use this to find which file mentions something, before reading whole files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Text to look for."}
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write text to a file, replacing anything already there. "
            "Use this only when the user asks for something to be saved."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File to write."},
                "content": {"type": "string", "description": "Text to write into it."},
            },
            "required": ["path", "content"],
        },
    },
]


def list_files():
    return "\n".join(sorted(os.listdir(".")))


def search_files(pattern):
    hits = []
    for name in sorted(os.listdir(".")):
        if not os.path.isfile(name):
            continue
        try:
            with open(name) as f:
                for i, line in enumerate(f, 1):
                    if pattern.lower() in line.lower():
                        hits.append(f"{name}:{i}: {line.strip()}")
        except (UnicodeDecodeError, PermissionError):
            continue
    return "\n".join(hits) if hits else f"No matches for {pattern!r} in this folder."


def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} characters to {path}."


def run_tool(name, tool_input):
    """Returns (output_text, is_error)."""
    try:
        if name == "read_file":
            with open(tool_input["path"]) as f:
                return f.read(), False
        if name == "list_files":
            return list_files(), False
        if name == "search_files":
            return search_files(tool_input["pattern"]), False
        if name == "write_file":
            return write_file(tool_input["path"], tool_input["content"]), False
        return f"No tool named {name}.", True
    except FileNotFoundError:
        return (
            f"No file called {tool_input.get('path')} here. "
            f"These exist: {list_files()}"
        ), True
    except Exception as e:
        return f"The tool failed: {e}", True
```

Now run the loop from Lesson 1.6 with these four tools and try each of these:

| Ask | What it should do |
|---|---|
| "What files are here?" | `list_files` only |
| "Which file mentions the plumber?" | `search_files`, not four `read_file` calls |
| "Read notes.txt and summary.txt" | Two `read_file` calls **in one turn** |
| "Save a summary of notes.txt to out.txt" | `read_file`, then `write_file` — two turns |
| "What is 12 times 12?" | No tools at all |

The fourth one is the interesting case. It needs two turns because the second call depends on
the first. The model works that out from the task, not from anything you wrote.

### If you are running a small local model

Run that table anyway, and expect one row to fail. Small models are good at choosing *between*
tools and bad at choosing *no tool*. A local model tested for this course got the first four
rows right and then called `read_file` for "what is 12 times 12?".

That is worth knowing precisely, because it tells you which lessons in this module still apply
to you:

| Claim | Holds on a small local model? |
|---|---|
| Clear descriptions beat vague ones | **Yes** — this reproduces |
| A stated boundary fixes confusion between two similar tools | **Yes** |
| Trigger sentences change how often a tool is used | **Yes** |
| A good description stops it using a tool it does not need | **Weakly** — expect over-triggering |

So do the whole module locally. Just do not conclude that your description is broken when the
model reaches for a tool on a question that needed none. That one is the model, and the fix is
a better model rather than better words — which is the only place in this course where that is
the honest answer.

### Part two: your provider may ship a loop

Most providers offer a helper that runs the loop for you. The names differ — Anthropic calls
it a tool runner, others call it an agent or an assistant — but the idea is the same, and it
usually looks something like this:

```python
# Sketch of the shape these helpers take. Check your provider's own documentation
# for the exact names; this is here so you recognise one when you meet it.

@tool                                   # a decorator that registers the function
def read_file(path: str) -> str:
    """Return the full text contents of a file.

    Use this when you need to know what is written inside a file.

    Args:
        path: The file to read, for example notes.txt.
    """
    with open(path) as f:
        return f.read()


runner = some_provider.tool_runner(tools=[read_file], messages=[...])
for message in runner:
    ...
```

Look at what disappeared. No `while` loop. No stop check. No result assembly. No schema —
it is generated from the type hints, and the description comes from the docstring.

Now look at what did **not** disappear. That docstring is a tool description. The trigger
sentence — *"Use this when you need to know what is written inside a file"* — is doing exactly
the job Lesson 2.2 described, and if you leave it out the helper cannot put it back.

### Which one should you use

For real work on a single provider, use their helper. It is less code, and the loop it runs is
the one you just wrote by hand.

Two things to know before you reach for one:

**It ties you to that provider.** These helpers are not standardised. Writing one loop yourself
and swapping `connect(...)` is the reason this course can offer you four options in Lesson 1.1.

**It does not write your descriptions.** The helper removes the loop, which was the easy part.
Everything in this module still applies, unchanged.

**We keep the manual loop for the rest of this course.** Modules 3 and 4 add permission checks
and recovery logic in the middle of it, and those changes are much clearer in a loop you can
read than inside somebody else's callback.

> The helper removes the loop. It does not remove the thinking. The part you had to learn is
> the part it cannot do for you.

### Try this before the next module

Take the four-tool Rover and deliberately break one description — remove the trigger sentence
from `search_files`.

Ask "which file mentions the plumber?" five times. Count how often it searches versus reading
every file one by one.

That number is your evidence for the claim this module opened with. Keep it. In Module 7 you
will turn exactly this kind of manual counting into an eval that runs on its own.

---

## Production notes (not for learners)

- **No video in this module.** Nothing moves. Two diagrams instead.
- **Diagram 1 (Lesson 2.3): the model choosing.** Four tool descriptions on cards, one
  question, an arrow to the chosen card. Then the same picture with two overlapping
  descriptions and a forked arrow. This is the module's whole argument in one image.
- **Diagram 2 (Lesson 2.6): parallel calls.** One assistant turn with two `tool_use` blocks,
  two results travelling back in a single user message. Then the wrong version, split across
  two messages, with the parallel calls dying off over the following turns.
- **2.6 is the sleeper lesson of the course.** No error, no warning, degrades over turns. Do
  not let it get trimmed for length — it is the clearest example of the failure shape that
  Modules 4 and 6 both rely on the learner recognising.
- **2.7 introduces the tool runner and then puts it away.** That is deliberate and should be
  stated plainly, as done, so learners do not think they are being taught the hard way for its
  own sake. Modules 3 and 4 modify the middle of the loop; a visible loop makes those diffs
  readable.
- **2.7 part two is deliberately a sketch, not runnable code.** Provider helpers are not
  standardised and naming them all would date the lesson within months. The point being taught
  is recognition — "you will meet one of these, here is what it does and does not do for you" —
  not usage. Resist requests to make it a working example for one vendor; that reintroduces
  exactly the lock-in the course now avoids.
- **The capability-floor table in 2.7 is measured, not estimated.** `gemma4` via Ollama scored
  3/3 on discriminating between `read_file` / `list_files` / `search_files`, then called
  `read_file` for "what is 12 times 12?". Re-measure if the recommended local model changes,
  and keep the table honest — a learner who hits an unexplained failure on the free path is
  the most likely person to abandon the course.
- **Check before shipping:** `disable_parallel_tool_use` placement inside `tool_choice`, and
  whether the large-tool-result offload behaviour mentioned in 2.4 is still accurate and still
  worth mentioning in a provider-neutral course (it is Anthropic-specific).
- **The emphasis-language guidance in 2.2 is version-sensitive.** It is correct for current
  models and was the opposite advice three years ago. Re-check at each model release, because
  a learner who applies old advice gets over-triggering and will blame the course.
