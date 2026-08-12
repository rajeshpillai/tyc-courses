# Module 1 — An agent is a loop

*The whole mechanism, in one module. Everything after this is detail.*

By the end of this module you will have written a working agent. Not a toy that prints text —
a program that decides to use a tool, uses it, reads the result, and decides what to do next.

It is about sixty lines of Python. That is not a simplification. That is the actual size of
the idea.

You can do the whole course on a model running on your own laptop, for nothing. You can also
do it on a paid API. We will set it up so that choice is one line, and so that nothing else in
the course depends on which way you went.

---

## Lesson 1.1 — An agent is a loop, and it fits on one screen

### Try this first

Before you read on, write down your own answer to this question:

> When an AI coding tool reads a file from your project, who opens the file?

Take ten seconds. Write it down. We come back to this in Lesson 1.4.

### The shape of the thing

Here is the whole mechanism. Read it once. You will not understand every line yet, and that
is fine.

```python
messages = [{"role": "user", "content": "Read notes.txt and summarise it."}]

while True:
    reply = llm.send(messages, TOOLS)

    messages.append({"role": "assistant", "content": reply.text,
                     "tool_calls": reply.tool_calls})

    if not reply.wants_tool:
        break

    results = run_the_tools_it_asked_for(reply)
    messages.append({"role": "tool_results", "results": results})
```

That is an agent.

We send a message. The model replies. If the reply is "please run this tool", we run it, tell
the model what happened, and send everything again. If the reply is anything else, we stop.

### What is doing the work

Look at what is in that loop, and what is not.

There is no planning engine. There is no reasoning module. There is no framework. There is a
`while` loop, a list called `messages`, and one function call.

The intelligence is in the model. The *agency* — the ability to do things — is in these ten
lines. You are about to write them.

> An agent is a model, a list of tools, and a loop that runs until the model stops asking
> for tools.

### About that `llm.send`

You may have noticed `llm` and wondered where it comes from. We build it in Lesson 1.3, out
of the differences between two real providers, once you have seen those differences yourself.

It is about eighty lines and it is the only file in this course that knows the name of any
company. Everything else — every tool, every guard, every lesson from here to the end — works
the same whichever model you point it at.

### Why so many people find this surprising

Agent tools feel much more complicated than this when you use them. They show plans. They
show progress. They pause and ask permission. They remember your project.

All of that is real, and all of it is built on top of the loop above. Module 3 adds the
permission step. Module 6 adds the memory. Every one of them is an addition to this loop, not
a replacement for it.

That is why we start here. If you learn the loop properly, the rest of the course is small
changes to something you already understand.

### Try this before the next lesson

Pick a model to work with. Any of these is fine, and you can change your mind later:

| Option | Cost | Set up |
|---|---|---|
| **Local (Ollama)** | Free | Install Ollama, then `ollama pull gemma4`. Needs about 10 GB of disk |
| **Google Gemini** | Free tier | An API key from Google AI Studio |
| **OpenAI** | Paid | An API key, a few dollars covers the course |
| **Anthropic** | Paid | An API key, a few dollars covers the course |

Then install what you need:

```bash
pip install openai          # also drives a local Ollama model
pip install anthropic       # only if you chose Anthropic
pip install google-genai    # only if you chose Gemini
```

If you have no card and no key, take the local option. Everything in this course was tested
that way, and it costs nothing.

---

## Lesson 1.2 — One API call, and what comes back

### Try this first

Run this. It is the smallest useful program in the course.

If you are running a model locally, this works as written:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

response = client.chat.completions.create(
    model="gemma4",
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
    max_tokens=100,
)

print(response)
```

If you are using OpenAI itself, delete the `base_url` line and use your real key and model
name. Nothing else changes. That is not a coincidence — Ollama deliberately copies OpenAI's
shape, which is why one adapter will later cover both.

Note that we print `response`, not the text. We want to see the whole thing before we start
picking pieces out of it.

### What came back

You did not get a string. You got an object, and the interesting part is that it has more in
it than the answer.

```python
print(response.choices[0].message.content)   # the text
print(response.choices[0].finish_reason)     # why it stopped
print(response.usage)                        # what it cost
```

Three things matter to us, and they will matter for the rest of the course:

| What | Why you care |
|---|---|
| The **text** | The answer |
| Why it **stopped** | This becomes the entire control flow — Lesson 1.5 |
| The **usage** | How the bill is calculated — Module 7 |

Run it again with a longer question and watch `usage` change. You are looking at the meter.

### The first thing that is not obvious

The reply is not simply a string, in any provider. It is a structure, because a reply can
contain more than words — it can contain a request to run a tool, and on some models it can
contain the model's reasoning as well.

That is why we print the whole object first, and why the course never writes
`response.choices[0].message.content` without knowing what else might be in there.

### Two parameters worth understanding now

**`model`.** Whichever you chose in Lesson 1.1. Nothing in this course depends on it.

**`max_tokens`.** A hard limit on how much the model may write in one reply. If the model hits
it, the reply is cut off mid-sentence — we handle that in Lesson 1.5. Keep it generous.

> A reply is a structure, not a string. Look at the whole thing before you reach into it.

### Try this before the next lesson

Ask for something long with `max_tokens=20`. Print the text and the finish reason together.

Look at exactly where the sentence stops. That ragged edge is what a truncated reply looks
like in production, and now you will recognise it.

---

## Lesson 1.3 — The same call somewhere else, and the three things that differ

### Try this first

Here is the same request, sent to Anthropic instead. Read it — you do not have to run it.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
)

print(response)
```

Same request. Same idea. Now compare what comes back with Lesson 1.2:

| | OpenAI and Ollama | Anthropic |
|---|---|---|
| The reply lives in | `choices[0].message.content` — a string | `content` — a **list of blocks** |
| Why it stopped | `finish_reason` | `stop_reason` |
| It wants a tool when | `finish_reason == "tool_calls"` | `stop_reason == "tool_use"` |
| Tool arguments arrive as | a **JSON string** you must parse | a **dict**, already parsed |
| Results go back as | one message per result, `role: "tool"` | all results in one `user` message |

Gemini differs again: replies are "parts", the assistant is called `model`, and tool results
are `function_response` objects.

### What you just did

You found the seam.

These are not different ideas. Every provider does the same three things — describes tools,
signals that it wants one, and accepts the result back. They just spell it differently.

So the differences are exactly three:

1. **How you describe a tool.**
2. **How you spot a tool request in the reply.**
3. **How you send the result back.**

That list is not a summary. It is a specification. Anything that handles those three things
can hide every provider behind one interface, and everything else you write can stop caring.

### The adapter

That is `llm.py`. The full version is in the course repository; here is its whole shape:

```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict          # always a dict, whoever sent it


@dataclass
class Reply:
    text: str
    tool_calls: list[ToolCall]
    stop: str                # the provider's own word, kept so you can see it
    usage: dict
    raw: object              # the untouched provider response

    @property
    def wants_tool(self):
        return bool(self.tool_calls)


def connect(spec):
    """connect("ollama:gemma4") / "openai:gpt-5" /
       "anthropic:claude-opus-5" / "gemini:gemini-2.5-flash" """
```

Each provider class does three small jobs — translate the tools going out, translate the
messages going out, translate the reply coming back. That is the entire file.

Use it like this:

```python
from llm import connect

llm = connect("ollama:gemma4")          # the only line that names a vendor
reply = llm.send(messages, TOOLS)
```

### Keep your own transcript

One decision inside the adapter matters enough to state plainly, because Lesson 1.6 depends
on it: **the conversation stays yours**, in one neutral shape:

```python
{"role": "user",         "content": "..."}
{"role": "assistant",    "content": "...", "tool_calls": [ToolCall, ...]}
{"role": "tool_results", "results": [{"id": ..., "content": ..., "is_error": False}]}
```

The adapter translates that into the provider's shape on every send. It never keeps a copy.
You still own the entire memory of your agent, which is the point of Lesson 1.6 and the reason
Module 6 is possible at all.

### Do not let the adapter hide the mechanism

An abstraction is useful and it is also a place to stop thinking. Two habits keep that from
happening:

**`reply.stop` keeps the provider's own word.** When your loop stops unexpectedly, print it.
`"tool_calls"`, `"tool_use"`, `"length"`, `"stop"` — these are real values from real
providers and you should recognise them.

**`reply.raw` is the untouched response.** Any time you wonder what really came back, look at
it. The adapter is eighty lines you can read, not a wall.

> Providers differ in exactly three places: describing a tool, spotting a tool request, and
> sending the result back. Everything else about an agent is the same everywhere.

### Try this before the next lesson

Get `llm.py` from the course repository and run the Lesson 1.2 request through it:

```python
from llm import connect
llm = connect("ollama:gemma4")
reply = llm.send([{"role": "user", "content": "Say hello in one short sentence."}])
print(reply.text, "|", reply.stop, "|", reply.usage)
```

Then open `llm.py` and read the class for the provider you are using. It is about twenty-five
lines. You should be able to point at all three translations.

---

## Lesson 1.4 — The model cannot do anything — it can only ask

### Try this first

Remember the question from Lesson 1.1: when an AI coding tool reads a file, who opens the
file?

Here is the answer, and it is the most important sentence in this module.

**You do.** Your program does. The model never touches your computer.

Let us prove it.

### Give it a tool it cannot use

We will tell the model about a tool, then deliberately not write the tool.

```python
from llm import connect

llm = connect("ollama:gemma4")

TOOLS = [
    {
        "name": "get_time",
        "description": "Get the current time on this computer.",
        "input_schema": {"type": "object", "properties": {}},
    }
]

reply = llm.send([{"role": "user", "content": "What time is it?"}], TOOLS)

print("stop:", reply.stop)
for call in reply.tool_calls:
    print("  it wants to call:", call.name, "with", call.arguments)
```

Run it. You will see it asking for `get_time`.

Now look at your clock. Nothing happened. No time was fetched. There is no `get_time`
function anywhere in that file — we never wrote one.

### What you just did

You handed the model a menu. It pointed at an item. That is all a tool call is: a pointer at
a menu item, plus the arguments it would like you to use.

The model produced some text that says *"I would like `get_time` to run"*. It cannot run it.
It has no hands. It is a program that produces text, and a tool call is a specially shaped
piece of that text.

Everything an agent does to your machine, your files, and your network is done by **your
code**, because you chose to run something when you saw that request.

> The model asks. Your program acts. Nothing happens that you did not write the code to do.

### Why this matters more than it sounds

Hold on to this, because three later modules grow out of it.

**Module 3 (permissions)** exists because your code is the thing that acts. You can put an
`if` statement in front of the action. The model cannot go around it, because it was never
doing the action in the first place.

**Module 4 (recovery)** exists because your code sees the result first. When a command fails,
you decide what the model gets told about the failure.

**Module 5 (MCP)** is a standard way of describing the menu, so that a menu written by
somebody else can be handed to a model by you.

This is also why the provider does not matter much. Every model in this course asks. None of
them act. The thing you are building is the part that acts.

### Try this before the next lesson

Change the tool description to something vague, like `"A useful tool."`, and ask the same
question. Then make it precise again.

Watch whether the model still asks for the tool. You have just done, by accident, the
experiment that Module 2 is built on: the description is not documentation. It is the
instruction the model is following.

---

## Lesson 1.5 — "It wants a tool" is the one signal your loop turns on

### Try this first

Look back at the loop from Lesson 1.1 and find the line that decides whether to keep going:

```python
if not reply.wants_tool:
    break
```

One question. That is the entire control flow of an agent.

### What is underneath it

`wants_tool` is true when the reply **contains at least one tool call**. Read that again,
because it is deliberately not the obvious implementation.

Each provider also reports a reason it stopped, and the adapter keeps that word in
`reply.stop` so you can see it:

| `reply.stop` | Provider | What happened |
|---|---|---|
| `tool_calls` | OpenAI, Ollama | It wants a tool run |
| `tool_use` | Anthropic | The same thing |
| **`STOP`** | **Gemini** | **Also the same thing — see below** |
| `stop` / `end_turn` | OpenAI / Anthropic | It finished naturally |
| `length` / `max_tokens` | OpenAI / Anthropic | **It hit your output limit mid-sentence** |
| `refusal` | Anthropic | It declined the request |

### Why the loop does not check the stop word

Look at the Gemini row. When Gemini asks for a tool, it reports `FinishReason.STOP` — the
same value it uses for a perfectly ordinary finished answer. There is no special word.

So an agent written like this:

```python
if reply.stop in ("tool_calls", "tool_use"):    # looks sensible, silently wrong
    run_the_tools()
```

works on two providers and quietly breaks on a third. It never runs a tool, never errors, and
the model appears to ignore the tools you gave it.

The reliable question is not *"what word did it stop with?"* but *"did it ask for anything?"*:

```python
if reply.tool_calls:        # what wants_tool actually does
    run_the_tools()
```

This is worth more than the portability. Even on one provider, the stop word is a *report
about the conversation* and the tool calls are *the request itself*. Check the request.

Two other rows deserve attention now, because ignoring them produces bugs that look like
something else.

### The truncation trap

If the model runs out of output budget, you still get a normal-looking reply with
normal-looking text in it. The text is just cut off.

Code that only asks "does it want a tool?" treats that truncated text as a finished answer.
The learner then spends an hour wondering why the model "forgot" the end of its own sentence.
It did not forget. You cut it off.

```python
if reply.stop in ("length", "max_tokens"):
    print("Warning: the reply was cut off. Raise max_tokens.")
```

### The one that will bite you in Module 4

A reply that does not want a tool means the model *stopped talking*. It does not mean the job
is done.

Read that again, because it is the failure that Module 4 is built around. The model can write
"I have updated the file and everything is working" and stop, having written nothing to disk.
The stop signal is correct. The claim is wrong.

Stop signals tell you about the conversation. They tell you nothing about the world. Checking
the world is your job, and we build that check in Module 4.

> The stop signal tells you why the model stopped talking. It never tells you whether the work
> got done.

### Try this before the next lesson

Set `max_tokens=20` and ask something that needs a long answer.

Print `reply.text` and `reply.stop` together. Then look up your provider's word for
truncation in the table above and confirm you got it. That is the value your loop has to
handle, and now you have seen it with your own model.

---

## Lesson 1.6 — The transcript is the state, and you own all of it

### Try this first

Run this and predict the answer before you look.

```python
from llm import connect

llm = connect("ollama:gemma4")

llm.send([{"role": "user", "content": "My name is Priya."}])
second = llm.send([{"role": "user", "content": "What is my name?"}])

print(second.text)
```

It does not know. It has no idea who Priya is.

### What you just did

You made two separate calls, and the second one had no connection to the first.

These APIs are **stateless**. There is no conversation stored on a server somewhere with an ID
you are attached to. Each call is complete and independent. The model remembers nothing
between calls, because there is nothing to remember with.

So how does a conversation work? You send the whole thing, every time.

```python
messages = [
    {"role": "user", "content": "My name is Priya."},
    {"role": "assistant", "content": "Nice to meet you, Priya."},
    {"role": "user", "content": "What is my name?"},
]
```

That list is the memory. You hold it. You append to it. If you drop it, the conversation is
gone.

### Appending correctly

In our loop there are exactly two things to append.

**The assistant's reply, including the tool calls.**

```python
messages.append({"role": "assistant", "content": reply.text,
                 "tool_calls": reply.tool_calls})
```

Both parts. If you append only the text, you throw away the record of what the model asked
for, and it loses track of its own request. The next call then fails, or behaves strangely,
and the cause is three lines further up than where the error appears.

**The tool results, matched by id.**

```python
messages.append({
    "role": "tool_results",
    "results": [{"id": call.id, "content": "the output, as a string", "is_error": False}],
})
```

The `id` must match the `id` on the tool call you are answering. That is how the model knows
which request this result belongs to, and it matters as soon as there is more than one call in
flight.

### Why this shape and not the provider's

You may have noticed that `tool_results` is not a role any provider actually has. OpenAI wants
one message per result with `role: "tool"`. Anthropic wants all results inside a single `user`
message. Gemini wants `function_response` parts.

We keep a neutral shape and let the adapter translate. That is not tidiness — it is what makes
Module 6 possible. When you start clearing old results and summarising history, you will be
editing this list directly, and you want to be editing something you designed rather than a
provider's wire format.

### The cost consequence

Every turn resends the entire list. Turn twenty sends turns one to nineteen along with it.

This is why a long agent session gets slower and more expensive as it goes, even when the
individual messages stay short. You are not paying for the last message. You are paying for
all of them, again.

Module 6 is entirely about this problem. For now, just know why it happens.

> The API remembers nothing. The `messages` list is the entire memory of your agent, and
> every call resends all of it.

### Try this before the next lesson

Fix the two-call program above. Build a `messages` list, append the assistant's reply, then ask
the follow-up question.

Then print `len(messages)` and `reply.usage` after each turn. Watch both numbers climb
together. That relationship is the whole of Module 6.

---

## Lesson 1.7 — Lab: Rover reads one file and tells you what is in it

This is the lesson where everything so far becomes one working program. Type it out rather
than copying it. You want the loop in your fingers.

### Set up

Make a folder, put `llm.py` in it, and give Rover something to read:

```bash
mkdir rover && cd rover
cp /path/to/llm.py .
echo "Buy milk. Call the plumber. Finish the report by Friday." > notes.txt
```

### The whole agent

Save this as `agent.py`:

```python
from llm import connect

llm = connect("ollama:gemma4")          # the only line that names a provider

# 1. The menu we hand to the model.
TOOLS = [
    {
        "name": "read_file",
        "description": (
            "Return the full text contents of a file. "
            "Use this whenever you need to know what is inside a file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The name of the file, for example notes.txt",
                }
            },
            "required": ["path"],
        },
    }
]


# 2. The code that actually does the thing. This is the part the model cannot do.
def read_file(path):
    with open(path) as f:
        return f.read()


def run_tool(name, arguments):
    if name == "read_file":
        return read_file(arguments["path"])
    return f"No tool named {name}."


# 3. The loop.
def main():
    messages = [
        {"role": "user", "content": "What is in notes.txt? Summarise it in one line."}
    ]

    for turn in range(10):
        reply = llm.send(messages, TOOLS)

        if reply.text:
            print(reply.text)

        # Keep the reply whole: the text and the tool calls.
        messages.append({"role": "assistant", "content": reply.text,
                         "tool_calls": reply.tool_calls})

        if reply.stop in ("length", "max_tokens"):
            print("[reply was cut off — raise max_tokens]")
            break

        if not reply.wants_tool:
            break

        # Run every tool it asked for, and collect the results.
        results = []
        for call in reply.tool_calls:
            print(f"[running {call.name} with {call.arguments}]")
            output = run_tool(call.name, call.arguments)
            results.append({"id": call.id, "content": output, "is_error": False})

        messages.append({"role": "tool_results", "results": results})


if __name__ == "__main__":
    main()
```

Run it:

```bash
python3 agent.py
```

### What you should see

Something close to this:

```
[running read_file with {'path': 'notes.txt'}]
The notes contain three tasks: buy milk, call the plumber, and finish the report by Friday.
```

Look at the order. The model asked for the file *before* it answered. Nobody told it to do
that. It read the tool description, decided the tool was relevant to the question, and asked.

That decision is the thing you just built.

### Read your own program again

Four pieces, and you now know why each one is there:

1. **`TOOLS`** — the menu. Lesson 1.4.
2. **`run_tool`** — your code, doing the work the model cannot do. Lesson 1.4.
3. **`messages`** — the memory, appended to whole. Lesson 1.6.
4. **`reply.wants_tool`** — the control flow. Lesson 1.5.

And one line naming a provider. Change it to `connect("anthropic:claude-opus-5")` or
`connect("gemini:gemini-2.5-flash")` and everything else runs unchanged. Try it if you have a
second option available — watching the identical program run on a different company's model is
worth the thirty seconds.

### One honest warning

`read_file` will open any file your user account can open. Ask Rover about `/etc/passwd` and
it will read it out.

That is a genuine security hole, and we do not fix it here. We fix it in Lesson 3.5, where
you will get to exploit it first and then close it. Keep this code in a folder you do not
mind poking at until then.

### Every agent product you have used is this loop wearing a coat

Sixty lines. A model, a menu, and a loop. Now think about the agent tools you have actually
used. They feel enormously bigger than what you just wrote. Here is what the difference is
made of:

| What the product does | What that actually is | Where we build it |
|---|---|---|
| Reads, writes, edits, searches your project | More entries in `TOOLS` | Module 3 |
| Runs terminal commands | One more tool, and a lot of care | Module 3 |
| Asks "allow this?" before acting | An `if` before you call the function | Module 3 |
| Recovers when a command fails | Sending the error back as a result | Module 4 |
| Stops when it goes in circles | A counter on the loop | Module 4 |
| Connects to Slack, GitHub, your database | Somebody else's menu, in a standard shape | Module 5 |
| Stays sharp in a two-hour session | Managing the `messages` list | Module 6 |
| Remembers your project between sessions | Writing notes to a file | Module 6 |

Not one row on that list is a different mechanism. Every row is an addition to the loop in
`agent.py`.

What is genuinely hard is not the loop. It is deciding what the agent is **allowed** to do,
knowing whether it actually did the job, keeping it useful in a long session, and knowing
whether your change made it better. Those are Modules 3, 4, 6 and 7 — and they are the course.

> There is no second, more advanced kind of agent. There is this loop, and there is everything
> people have carefully built around it.

### Try this before the next module

Three experiments, in order:

1. Ask a question that needs no file at all: `"What is 12 times 12?"` A strong model answers
   directly. A small local model may call `read_file` anyway — that is a real limitation and
   we deal with it properly in Module 2.
2. Ask about a file that does not exist. Watch it crash, and read the traceback. That crash is
   Lesson 2.5.
3. Add a `write_file` tool by copying the shape of `read_file`. Ask Rover to write a summary
   into `summary.txt`. You now have an agent that changes your disk.

Then answer this in one sentence: *what does the model do that your code cannot, and what does
your code do that the model cannot?* If you can answer that cleanly, you understand agents
better than most people using them.

---

## Production notes (not for learners)

- **Verified by execution, not documentation.** The Lesson 1.7 lab was run end to end against
  `ollama:gemma4` on 2026-08-12: one `read_file` call, correct one-line summary, loop exits on
  the second turn. The adapter's message translation was unit-checked against all three hosted
  providers (Anthropic `tool_use`/`tool_result` blocks, OpenAI JSON-string arguments and
  `role: "tool"`, Gemini `model` role and `function_response`).
- **Gemini is now round-trip verified too** (2026-08-12, `gemini-flash-latest`): plain call,
  tool request with correctly parsed arguments, and result accepted back. Two findings came
  out of that run and are baked into the lessons above. First, Gemini's function-call parts
  carry an opaque `thought_signature` that must be replayed unchanged — the adapter now keeps
  the original part on `ToolCall.raw` instead of rebuilding one, and without it the second
  turn fails with a 400. Second, **Gemini reports `FinishReason.STOP` when asking for a
  tool**, which is why 1.5 now teaches checking `reply.tool_calls` rather than the stop word.
- **Still unverified:** live calls to Anthropic and OpenAI. Translation shapes are confirmed
  correct and the Anthropic block shapes were unit-checked; the round trip is not done. Needs
  one key each and about five minutes.
- **Model names rot fast.** `gemini-2.5-flash` is still *listed* by the API but returns 404
  "no longer available to new users" — so a course pinned to it breaks for exactly the new
  learners it is aimed at. Use the floating aliases (`gemini-flash-latest`) in lesson text,
  and re-check the setup table at every ship.
- **The derivation order in 1.2 → 1.3 is the whole design.** The learner sees a raw call, then
  a second provider, then builds the adapter from the differences. Do not "simplify" this by
  introducing `llm.py` in 1.1 — an abstraction handed over before the thing it abstracts is
  exactly the failure mode this ordering exists to avoid.
- **1.2 uses the OpenAI shape via local Ollama on purpose.** It is free, needs no card, and the
  same code reaches OpenAI proper by deleting one line. That gets the learner to a working call
  with no signup, which matters more for retention than which vendor they meet first.
- **1.7 is the retention point.** It must run first try, in one sitting, with `pip install
  openai` and a local model. If a copy-paste of that file does not work on a clean machine, the
  whole course leaks here.
- **The `read_file` hole in 1.7 is intentional and must stay.** Lesson 3.5 depends on the
  learner already having written the vulnerable version. Flag it honestly, as done. Do not fix
  it early.
- **The over-triggering note in "try this" is a measured result, not a hedge.** `gemma4` called
  `read_file` for "what is 12 times 12?" in testing while correctly discriminating between four
  similar tools 3/3. Module 2 needs to state this capability floor explicitly.
- **Diagram 1 (Lesson 1.1): the loop.** Four boxes — your program, the model, the tool menu,
  the transcript. One arrow leaving the model labelled "asks", one leaving your program
  labelled "acts". Reused in 1.7, 3.1 and 5.1.
- **Diagram 2 (Lesson 1.3): the seam.** Two provider replies side by side with the three
  differences marked, and `llm.py` sitting underneath both. This is the image that justifies
  the adapter.
- **Check before shipping:** that Ollama still exposes `/v1/chat/completions`, the model names
  in the setup table, and the `reply.stop` value table in 1.5 against each provider.
