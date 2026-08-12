# Module 3 — Letting it touch your machine

*Where a toy becomes something you have to be careful with.*

So far Rover reads and writes files in one folder. That is enough to be useful and not enough
to be dangerous.

This module gives it real reach: the file tools a coding agent actually needs, and a shell.
Then it takes some of that reach back, because an agent with a shell and no permission layer
is not a tool. It is a liability with good manners.

---

## Lesson 3.1 — Read, write, edit: the three file tools everything is built on

### Try this first

Ask Rover to change one line in a file it has already read. Watch what it does with
`write_file`.

It rewrites the whole file. Every time. Even for a one-character change.

### Why that is a problem

Three reasons, and the third is the one that matters.

**Cost.** The whole file goes into the transcript twice — once when read, once when written —
and stays there for every later turn.

**Truncation.** A long file plus a long reply can hit `max_tokens`, and you get half a file
written to disk. Silently.

**Lost work.** If anything changed the file between the read and the write, that change is
gone. The model is writing from what it remembers, not from what is there.

### The three tools

Real coding agents use three file tools, not two:

| Tool | What it does | When the model reaches for it |
|---|---|---|
| `read_file` | Return the contents | It needs to know what is there |
| `write_file` | Create a file, or replace it entirely | New file, or a full rewrite |
| `edit_file` | Replace one exact string with another | Changing part of an existing file |

`edit_file` is the one people leave out, and it is the one that does most of the work.

```python
def edit_file(path, old_text, new_text):
    with open(path) as f:
        content = f.read()

    count = content.count(old_text)
    if count == 0:
        return f"Could not find that text in {path}. Nothing changed."
    if count > 1:
        return (
            f"That text appears {count} times in {path}. "
            "Nothing changed — include more surrounding lines to make it unique."
        )

    with open(path, "w") as f:
        f.write(content.replace(old_text, new_text))
    return f"Replaced 1 occurrence in {path}."
```

### The two checks are the whole design

Look at what that function refuses to do.

**Zero matches: it does nothing and says so.** The model's memory of the file was wrong, or
the file changed. Guessing here would corrupt the file.

**More than one match: it does nothing and says so.** The model asked to change "return x"
in a file with nine of them. Which one? It does not know, and neither do you. The error tells
it how to fix its own request — send more surrounding lines.

That second message is doing real work. It does not just report a failure, it teaches the
model the technique that avoids the failure. The next attempt usually includes three lines of
context and succeeds.

> An edit tool that refuses ambiguous edits is safer than one that guesses, and the refusal
> message is where you teach the model to ask better.

### Try this before the next lesson

Add `edit_file` to Rover. Ask it to change one word in `notes.txt`.

Then ask it to change a word that appears three times. Read the error it gets and watch what
it sends next.

---

## Lesson 3.2 — The tools some providers define for you, and why they have no schema

### Try this first

Here is a tool definition with something missing:

```python
# Anthropic's version. Other providers have their own; some have none.
{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}
```

No description. No `input_schema`. Two keys.

Compare it with the ones you have been writing, which have four or five keys and a paragraph
of English. This one still works.

### What is going on

Some tools are **defined by the provider**, not by you. The model already knows their names,
their arguments and how to use them, because they were part of its training. You are not
describing a tool. You are switching on one it already knows.

Anthropic's file editor and shell are the clearest examples:

```python
{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}
{"type": "bash_20250124", "name": "bash"}
```

Note the `type` carries a date. These are versioned, and the `name` and `type` are a matched
pair — mixing a name from one version with a type from another is an error, not a warning.

Whether your provider offers anything like this varies, and it is not something to build on if
you want your agent to be portable. What matters is the idea, and one consequence of it that
people get wrong.

### They are still executed by you

This goes straight back to Lesson 1.4.

"Provider-defined" describes who wrote the *schema*. It does not mean the tool runs on the
provider's servers. The model asks for the tool, and **your code** performs the file operation
or runs the command, exactly as with your own tools.

You get the definition for free. You still write the implementation, and you still own every
consequence of it — including everything in the next three lessons.

The text editor, for instance, sends you a `command` field and expects you to implement four
operations:

```python
def text_editor(arguments):
    command = arguments["command"]

    if command == "view":
        ...      # return file contents, or a directory listing
    if command == "create":
        ...      # write arguments["file_text"] to arguments["path"]
    if command == "str_replace":
        ...      # replace old_str with new_str, exactly once
    if command == "insert":
        ...      # insert insert_text after line insert_line
    return f"Unknown command: {command}"
```

Look at `str_replace`. That is `edit_file` from the last lesson, with the same one-match rule.
You did not build a worse version of a standard tool — you built the standard tool, and now
you know why it is shaped that way.

That is the real lesson here. These pre-defined tools are not magic and they are not a
different mechanism. They are the same three fields, with the description already written and
the schema already agreed.

### Which to use

| Use a provider-defined tool when | Use your own when |
|---|---|
| You are committed to that provider | You want to run anywhere — **the default in this course** |
| You want the model's trained familiarity with it | Your tool does something specific to your app |
| You do not want to write and tune a description | You want full control of the contract |

One trap worth naming: do not define a *custom* tool named `bash` with your own schema on a
provider that already defines one. You get a different tool that happens to share a name,
without the built-in behaviour, and the resulting confusion is hard to see.

**Rover keeps its own tools for the rest of the course.** Not because provider-defined ones are
worse, but because a tool you defined works on every model in Lesson 1.1, and everything from
here on — permissions, path safety, recovery — attaches to the implementation, which is yours
either way.

> Provider-defined means the provider wrote the schema. Your code still does the work, and
> still carries every risk in the next three lessons.

### Try this before the next lesson

Whether or not your provider has these, do this thought experiment properly: write down what
your `read_file`, `write_file` and `edit_file` would look like as **one** tool with a `command`
field, the way the text editor does it.

Then ask yourself which is easier for a model to choose correctly — three tools with three
clear descriptions, or one tool with four modes. That question has no single right answer, and
Module 2 gave you everything you need to argue it either way.

---

## Lesson 3.3 — Running commands, and why this is the one that should worry you

### Try this first

Do not run this yet. Read it.

```python
import subprocess

def bash(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr
```

Six lines. That is a shell tool. It works.

It also means any text the model produces gets executed on your machine, with your user
account's permissions, with no check of any kind.

### Why a shell tool is different from every other tool

Every tool so far had a fixed shape. `read_file` reads a file — a bad path is still only a
file read.

A shell tool has no shape. `bash` is not one capability. It is *every* capability your account
has: your files, your network, your credentials, your git remotes, `rm -rf`. You cannot
enumerate what it can do, which means you cannot reason about the worst case.

That is worth saying plainly, because it is the honest reason this lesson exists:

> Adding a shell tool changes the question from "what can this agent do?" to "what can this
> account do?" Those are very different questions.

### Where the danger actually comes from

Not from the model deciding to be destructive. That is rare, and it is not the realistic
threat.

The realistic threats are ordinary:

**A confident mistake.** It runs `git checkout .` to "clean up" and discards your uncommitted
work. It was trying to help. Your work is still gone.

**Text it read somewhere.** The model reads a file, a web page, or an issue comment. That
text contains instructions. The model has no reliable way to tell your instructions from
instructions it merely *read*, so text in a file can become a command. This is prompt
injection, and a shell tool is what turns it from an annoyance into a breach.

Neither of these needs the model to be malicious. Both need only that it is helpful and
literal.

### What "careful" means concretely

Four things, in order of how much they buy you:

1. **A permission layer.** Ask before running. Lesson 3.4.
2. **A working directory boundary.** The agent works in a project folder, not `$HOME`.
3. **A timeout.** A command that hangs should not hang the agent.
4. **Isolation.** A container or a VM, so the worst case is bounded by something other than
   your own care.

Here is the same tool with three of the four, which is where our version lands:

```python
import subprocess

def bash(command, workdir):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=workdir,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return "The command took longer than 30 seconds and was stopped."

    output = (result.stdout + result.stderr).strip()
    if not output:
        return f"Command finished with exit code {result.returncode} and no output."
    return f"exit code {result.returncode}\n{output[:4000]}"
```

Three things changed and each earns its place. `cwd` keeps it in the project. `timeout` stops
a hang. Returning stdout **and** stderr **and** the exit code means the model can tell success
from failure — which is Lesson 4.4.

### The honest limit

`shell=True` with a model-supplied string cannot be made safe by validation. People try
blocklists — banning `rm`, banning `sudo` — and blocklists lose. There are always more ways to
express a command than you can enumerate.

If you need a real boundary, an allowlist of specific commands beats a blocklist, and a
container beats both. What we build in the next lesson is a permission prompt, which is a
different thing: it does not constrain the agent, it puts a human in front of the action.

### Try this before the next lesson

Give Rover the bash tool above, in a scratch folder with nothing you care about. Ask it to
count the Python files.

Then ask it to "clean up the folder" and read the command it proposes **without running it**.
That pause you just felt is the entire argument for the next lesson.

---

## Lesson 3.4 — Permissions: ask, allow, deny, remember

### Try this first

Go back to Lesson 1.3. The model asks. Your code acts.

That means the permission layer is not a feature you have to negotiate with the model. It is
an `if` statement in a function you own, on a code path the model cannot reach.

### The simplest version that works

```python
ALWAYS_ALLOW = {"read_file", "list_files", "search_files"}
remembered = set()


def may_run(name, tool_input):
    if name in ALWAYS_ALLOW or name in remembered:
        return True

    print(f"\nRover wants to run: {name}")
    print(f"  with: {tool_input}")
    answer = input("  allow? [y]es / [n]o / [a]lways: ").strip().lower()

    if answer == "a":
        remembered.add(name)
        return True
    return answer == "y"
```

And in the loop, in front of the tool call:

```python
if not may_run(block.name, block.input):
    output, failed = "The user did not allow this. Do not try it again.", True
else:
    output, failed = run_tool(block.name, block.input)
```

That is the whole mechanism. Thirty lines, and it is the same mechanism the agent products
you have used are running.

### The four decisions

| Answer | What happens | When you want it |
|---|---|---|
| Allow once | Runs this time only | Anything with a side effect you want to see each time |
| Deny | Does not run, model is told | It proposed something wrong |
| Always allow | Runs now and skips the prompt later | Reads, searches, listing — things that cannot hurt |
| Deny and explain | Does not run, model is told **why** | It has the right idea and the wrong command |

That last row is the one people forget, and it is the most useful.

### Denial is a message, not a silence

A denied tool must still return a result. Look at the wording above:

```python
"The user did not allow this. Do not try it again."
```

Compare with what happens if you say nothing useful. The model sees a failure with no
explanation, assumes something went wrong mechanically, and tries again — sometimes the exact
same command, sometimes a variation. You end up denying the same thing five times.

Better still, let yourself say why:

```python
answer = input("  allow? [y]es / [n]o / [a]lways / [e]xplain: ").strip().lower()
if answer == "e":
    reason = input("  tell Rover why not: ")
    return False, f"The user declined: {reason}"
```

Now `"Do not delete the folder — use git clean -n first to see what would go"` reaches the
model, and its next proposal is usually right.

> A denial is a turn in the conversation. Say why, and the next proposal improves. Stay
> silent, and it tries again.

### Read-only is not automatically safe

`ALWAYS_ALLOW` above includes the read tools, and that is a reasonable default for a personal
tool on your own machine.

It is not a universal rule. Reading is how data leaves. An agent that can read any file and
also reach the network can move your credentials somewhere else, without ever writing to
disk. In that setting, "reads are free" is wrong.

The right default depends on what else the agent can do. Name the assumption, do not inherit
it.

### Try this before the next lesson

Add the permission layer. Ask Rover to do something with several steps, like "tidy up this
folder and write a summary".

Say no to one step and explain why. Watch how it adapts. Then say no to the same class of
thing with no explanation, and watch it retry. The difference is the lesson.

---

## Lesson 3.5 — The path the model sent you is not a path you can trust

### Try this first

You have been carrying a security hole since Lesson 1.6. Let us use it.

Start Rover in your project folder and ask:

> "Read the file at ../../.ssh/config and tell me what is in it."

It will do it.

Try `/etc/passwd`. That works too. On your own machine, with your own account, Rover will
read anything you can read.

### What you just did

Your `read_file` does this:

```python
with open(path) as f:      # path came from the model
    return f.read()
```

`path` is a string the model produced. You passed it straight to `open()`. There is no folder
boundary anywhere in that code — you *thought* there was one because you have been running in
a project folder, but nothing enforces it.

This is path traversal, and it is one of the oldest bugs there is. You just wrote it, in four
lines, without noticing. That is exactly how it happens in real systems.

### Why "just check for `..`" does not work

The obvious fix:

```python
if ".." in path:           # not enough
    return "Not allowed."
```

That blocks `../../.ssh/config` and misses:

- `/etc/passwd` — absolute, no `..` needed
- `notes/../../.ssh/config` — the `..` is not at the start
- A symlink inside the project pointing anywhere on disk
- `%2e%2e%2f` if anything URL-decodes on the way through

Every one of those is a real bypass. This is the blocklist problem from Lesson 3.3 in
miniature: you cannot enumerate the bad inputs.

### The fix: resolve, then compare

Stop inspecting the string. Resolve it to a real location, then check that location:

```python
from pathlib import Path

ROOT = Path.cwd().resolve()


def safe_path(path):
    """Resolve path inside ROOT, or raise if it escapes."""
    candidate = (ROOT / path).resolve()
    if not candidate.is_relative_to(ROOT):
        raise ValueError(f"{path} is outside the project folder.")
    return candidate
```

Then every file tool goes through it:

```python
def read_file(path):
    with open(safe_path(path)) as f:
        return f.read()
```

Three things make this work where string checks fail. `resolve()` collapses `..` **and**
follows symlinks, so you are checking where the path really lands. `ROOT / path` makes an
absolute `path` replace the root, and `resolve()` then reveals that — so the check catches it.
And `is_relative_to` compares resolved locations, not text.

### Test the fix

Re-run every attack from the top of this lesson. All refused. Then check that normal use still
works — `notes.txt`, `sub/folder/file.txt` — because a security fix that breaks the tool gets
removed by the next person.

Give the refusal a useful message, per Lesson 2.5:

```python
except ValueError as e:
    return f"{e} Rover can only read files inside {ROOT.name}.", True
```

The model then stays in the folder rather than trying six variations of the same escape.

> Never inspect a path. Resolve it, then check where it landed. The string tells you nothing
> about where it points.

### The general rule

The model produced that path. It is untrusted input, in the same way a form field on a web
page is untrusted input — not because the model is hostile, but because you did not write it
and cannot predict it.

Everything the model sends you is in that category: paths, commands, URLs, SQL fragments,
filenames. Treat tool arguments the way you treat user input, because that is what they are.

### Try this before the next lesson

Apply `safe_path` to every file tool in Rover, including `write_file` and `edit_file`.

Then try to write outside the folder. Then check that ordinary editing still works. That last
check is the one people skip.

---

## Lesson 3.6 — Lab: Rover edits its own source code

### The task

Rover is going to add a feature to itself.

This is not a stunt. It exercises everything in the module at once — read, edit, shell,
permissions, path safety — and it produces the clearest possible evidence that the loop you
built in Module 1 is doing real work.

### Set up

Work in a copy, and put it under git so you can undo anything:

```bash
cp -r rover rover-selfedit && cd rover-selfedit
git init && git add -A && git commit -m "before"
```

Rover should now have: the text editor tool (3.2), `bash` with `cwd` and a timeout (3.3), the
permission layer (3.4), and `safe_path` on every file tool (3.5).

### The prompt

```
Add a tool called word_count to this agent.

It should take a path and return the number of words in that file.

Steps:
1. Read agent.py to see how the existing tools are written.
2. Add the tool definition and the function, following the same style.
3. Run: python3 -c "import agent" to check it still imports.

Tell me what you changed.
```

### What to watch for

Four moments, in order:

**It reads before it writes.** Nobody told it the file layout. It asks for `agent.py` first
because your `read_file` description says to.

**It edits rather than rewrites.** With `str_replace` available, it changes the `TOOLS` list
in place. Watch the `old_str` it sends — it includes surrounding lines to make the match
unique. That is Lesson 3.1's error message having taught it a technique.

**It asks permission to run Python.** Your prompt appears. This is the moment where the two
halves of the module meet: the model wants to run a command, and a human decides.

**It checks its own work.** The import either succeeds or it does not, and the exit code comes
back. If it fails, watch it read the traceback and fix the file. That recovery loop is all of
Module 4, arriving early.

### When it goes wrong

It will, on some runs. Three common ones:

| What happens | Why | What it teaches |
|---|---|---|
| `str_replace` finds no match | Its memory of the file is stale after its own edit | Re-read after editing |
| Adds the function but not the definition | It did half the job and stopped at `end_turn` | Lesson 4.2, exactly |
| Import fails, it fixes the wrong line | It guessed instead of reading the traceback | Lesson 4.4 |

The second one is worth stopping on. It will say something like "I've added the `word_count`
tool" and it will be half true. The tool definition is there and the function is missing, or
the other way around.

Nothing errored. `stop_reason` was `end_turn`. The claim was confident. And it is wrong.

That is the failure the whole of Module 4 is built on, and you have now met it in the wild.

### Check the diff yourself

```bash
git diff
```

Read every line. Not because you expect sabotage — because reading a change you did not write
is a skill, and this is the module where you start.

### Try this before the next lesson

Run the same task again from the clean commit, twice.

The two runs will differ — different edit points, different order, maybe one succeeds and one
does not. Same prompt, same code, different behaviour.

Sit with that for a moment. It is why Module 7 exists, and why "I tried it and it worked" is
not evidence about an agent.

---

## Lesson 3.7 — What a real agent product guards that your prototype does not

### What you have now

Rover reads, writes, edits, searches, and runs commands. It asks before doing anything with a
side effect. It cannot leave its folder.

For a personal tool on your own machine, that is a reasonable place to be. It is not what a
product does, and the gap is worth naming precisely — partly so you know what to build if you
need it, and partly so you can read someone else's agent and see what is missing.

### The gap

| Guard | What it stops | Where yours stands |
|---|---|---|
| Path confinement | Reading and writing outside the project | **Done** — Lesson 3.5 |
| Permission prompt | Silent side effects | **Done** — Lesson 3.4 |
| Timeout | A hung command hanging the agent | **Done** — Lesson 3.3 |
| Process isolation | Everything else `bash` can reach | Missing — needs a container or VM |
| Network egress limits | Data leaving, credentials being posted out | Missing |
| Secret redaction | Keys reaching the transcript, and the API | Missing |
| Audit log | Not knowing what it did an hour ago | Partly — Lesson 4.5 |
| Undo | A wrong edit being permanent | Missing — `git` is doing this for you |

Two of those deserve more than a table row.

### Isolation is the one that actually bounds the damage

Everything else on that list narrows what the agent is likely to do. Isolation changes what is
*possible*.

Run the agent in a container with the project mounted and nothing else, and the worst case
stops being "your machine" and becomes "this container". You have not made the agent better
behaved. You have made bad behaviour survivable, which is the only guarantee that does not
depend on your care.

This is why hosted agent platforms exist. Not because the loop is hard — you wrote the loop —
but because giving every session a clean, disposable, bounded machine is real infrastructure
work that nobody wants to do twice.

### Secrets are the one people discover too late

Your `.env` file is in the project folder. `safe_path` allows it — it is inside the root.

So Rover can read your API keys, and the moment it does, they are in the transcript. The
transcript is sent to the API on every subsequent turn, and it is probably in your logs.

Two habits, starting now:

**Refuse the obvious ones by name.** A deny-list of `.env`, `.pem`, `id_rsa`, `credentials`,
`.aws/` is not a security boundary, but it catches the accident, and the accident is the
common case.

**Never let a secret into the transcript.** Once it is in `messages`, it is resent every turn
for the rest of the session. There is no way to take it back out except starting again.

### The honest summary

You have built the mechanism correctly. What separates this from a product is not
sophistication in the loop — it is the boring, expensive work around it: isolation, egress
control, redaction, audit, undo.

That work is not more advanced than what you have done. It is just more of it.

> Your prototype is correct and unbounded. A product is the same loop with the blast radius
> made small on purpose.

### Try this before the next module

Add a deny-list to `safe_path` for `.env`, `.pem`, `id_rsa`, and anything under `.git/`.

Then ask Rover to "check the project configuration" and see whether it goes looking. Read the
refusal message you wrote. Would it tell a confused model what to do instead?

---

## Production notes (not for learners)

- **Two videos.** 3.3 — the bash tool, and the "clean up the folder" moment where the learner
  reads a proposed command and does not run it. 3.6 — the full self-edit, start to finish,
  including a failed run. Both under eight minutes.
- **3.6 must include a failure in the recording.** The half-finished edit with a confident
  summary is the single most important thing in the module, and it only lands if the viewer
  sees it happen rather than reading about it. If the take goes cleanly, keep filming and use
  a second take.
- **3.5 depends on the vulnerable `read_file` from Lesson 1.6 still being vulnerable.** If
  anyone "fixes" 1.6 during review, this lesson loses its opening and becomes a lecture. The
  exploit-first structure is the point.
- **Diagram (Lesson 3.4): the permission gate.** The Module 1 loop diagram with one new box
  between "model asks" and "your program acts", labelled with the four answers. Reuse the
  original artwork — the learner should recognise it instantly.
- **The prompt-injection paragraph in 3.3 is deliberately short.** It names the mechanism and
  moves on. If the Season 2 sketch turns into a full security module, this is where the
  forward reference goes; if not, consider expanding 3.3 into two lessons rather than adding
  a new one.
- **`is_relative_to` needs Python 3.9+.** The course requires 3.10+ for `anthropic[mcp]`, so
  this is fine, but do not let the requirement drift down.
- **Check before shipping:** the `text_editor_20250728` / `str_replace_based_edit_tool` pair
  and the `bash_20250124` type string, the text editor's four command names, and that
  Anthropic-defined tools still take no `input_schema`. Tool versions are dated and this is
  the module most exposed to that.
