# Module 5 — MCP: the protocol under the tools

*The reason this course is worth taking now. Almost nobody teaches the mechanism.*

Every tool Rover has was written by you, in your file, in your loop. That does not scale. You
are not going to write a GitHub tool, a Slack tool, a Postgres tool, and a Jira tool, and then
maintain all four when their APIs change.

MCP is the standard that fixes this. Most explanations of it stop at "paste this config into
a JSON file". We are going to read the actual bytes on the wire, once, and after that you will
be able to debug an MCP server instead of restarting it and hoping.

---

## Lesson 5.1 — The problem MCP solves, in one picture

### Try this first

Count the tool definitions you would need for a genuinely useful assistant: files, git,
GitHub issues, Slack, a database, your calendar, your ticketing system.

Seven integrations. Now count them again for the *next* agent you build. Fourteen. Now
consider that your colleague is writing their own seven, for the same seven services.

### The shape of the problem

This is the M×N problem. M agents, N services, and without a standard you write M×N
integrations.

```
  before                         after

  agent A ──┬── GitHub           agent A ──┐
            ├── Slack                      ├── MCP ──┬── GitHub server
            └── Postgres                   │         ├── Slack server
                                agent B ──┘         └── Postgres server
  agent B ──┬── GitHub
            ├── Slack
            └── Postgres
```

With a standard, the GitHub people write **one** server. Every agent that speaks MCP can use
it. You write M + N instead of M×N, and you write the M part once.

That is the whole idea. MCP is a standard way to describe a menu of tools, so that a menu
written by someone else can be handed to a model by you.

### What MCP is not

Three things it is easy to assume and that are wrong:

**It is not an AI protocol.** There is no model in it. MCP describes tools and delivers
results. What you do with them is your business — you could drive an MCP server from a
command-line script with no model anywhere.

**It does not run the model, or make decisions.** Your loop from Module 1 is still the loop.
MCP just changes where the tool definitions come from and who executes them.

**It is not new machinery.** It is JSON-RPC over a pipe. You will see the whole thing in the
next lesson and it will be less than you expect.

### Where it sits in what you have

Go back to the four pieces of `agent.py` from Lesson 1.6:

| Piece | Without MCP | With MCP |
|---|---|---|
| Tool definitions | You write them | The server sends them |
| Tool implementation | Your functions | Runs in the server |
| The loop | Yours | **Still yours** |
| The transcript | Yours | **Still yours** |

Two of four change. The loop you spent Module 1 on is untouched, which is the reassuring part
of this module.

> MCP replaces the menu and the kitchen. It does not replace the loop, and the loop is what
> you built.

### Try this before the next lesson

List three services you would actually want an agent to reach. For each, write down the two
or three operations you would need.

Keep the list. In Lesson 5.4 you build a server, and it is more satisfying to build one you
would use.

---

## Lesson 5.2 — JSON-RPC over a pipe: the whole wire format, read once

### Try this first

Here is a complete MCP conversation. Not a simplified one — this is what actually travels.

```
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
     "protocolVersion":"2024-11-05",
     "capabilities":{},
     "clientInfo":{"name":"rover","version":"0.1"}}}

← {"jsonrpc":"2.0","id":1,"result":{
     "protocolVersion":"2024-11-05",
     "capabilities":{"tools":{}},
     "serverInfo":{"name":"notes","version":"0.1"}}}

→ {"jsonrpc":"2.0","method":"notifications/initialized"}

→ {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}

← {"jsonrpc":"2.0","id":2,"result":{"tools":[
     {"name":"add_note",
      "description":"Add a note to the notebook.",
      "inputSchema":{"type":"object",
                     "properties":{"text":{"type":"string"}},
                     "required":["text"]}}]}}

→ {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
     "name":"add_note","arguments":{"text":"Call the plumber"}}}

← {"jsonrpc":"2.0","id":3,"result":{
     "content":[{"type":"text","text":"Added note 1."}]}}
```

That is MCP. Read it twice. There is nothing else.

### What each part is doing

**It is JSON-RPC 2.0.** A forty-line specification from 2010. Every message has
`"jsonrpc":"2.0"`. Requests carry an `id` and a `method`; responses carry the same `id` and
either a `result` or an `error`. Messages without an `id` are notifications and get no reply.

**One JSON object per line**, over stdin and stdout. That is the default transport. The client
starts the server as a subprocess and they talk over pipes.

**`initialize` is a handshake**, and it is where version and capability negotiation happens. It
comes first, always. The `notifications/initialized` that follows is the client saying "I am
ready" — no reply expected.

**`tools/list` is the menu.** Look closely at what comes back: `name`, `description`,
`inputSchema`. That is the same three fields you wrote by hand in Module 2. MCP did not
invent a new way to describe a tool. It standardised where the description comes from.

**`tools/call` is the execution**, and the result is a list of content blocks — the same
shape as the tool results you have been building since Lesson 1.5.

### The one mapping you need

Put the two side by side:

| Our tool, since Module 2 | MCP tool, on the wire |
|---|---|
| `name` | `name` |
| `description` | `description` |
| `input_schema` | `inputSchema` |

Snake case on one side, camel case on the other. That is the entire translation, and you write
it yourself in Lesson 5.5 — it is six lines.

Once you have seen that, MCP stops being a new concept. It is your Module 2 tool definition,
sent over a pipe by a program you did not write.

### Errors

Failures come back as JSON-RPC errors, or as a result marked as an error:

```
← {"jsonrpc":"2.0","id":3,"error":{"code":-32602,"message":"Missing required argument: text"}}
```

`-32602` is "invalid params", from the JSON-RPC spec. You will also see `-32601` (no such
method) and `-32700` (bad JSON). When an MCP server "does not work", these are what you are
looking for — and now you can read them.

> MCP is JSON-RPC 2.0 over stdin and stdout: a handshake, a menu, and a call. If you can read
> those three messages, you can debug any MCP server.

### Try this before the next lesson

Find any MCP server on your machine or install one. Run it directly in a terminal and paste
the `initialize` message from above into stdin, followed by Enter.

You will get a JSON response back. You are speaking the protocol by hand. Do it once and it
stops being magic permanently.

---

## Lesson 5.3 — Tools, resources, prompts: the three things a server offers

### Try this first

You have seen `tools/list`. A server can also answer `resources/list` and `prompts/list`.

Three menus, not one. Most tutorials only mention the first, which is why most people's mental
model of MCP is smaller than MCP.

### The three

| Kind | What it is | Who decides to use it | Analogy |
|---|---|---|---|
| **Tool** | An action the model can take | The **model** | A function call |
| **Resource** | Data the client can read | The **application** | A file |
| **Prompt** | A template the user can invoke | The **user** | A slash command |

The middle column is the real distinction, and it is the one worth remembering. All three
deliver something useful. They differ in *who chooses*.

### Tools — model-controlled

What you already know. The model reads the description and decides to call it.

```
tools/call  {"name": "add_note", "arguments": {"text": "..."}}
```

Side effects live here. If it changes something, it is a tool.

### Resources — application-controlled

A resource is data with a URI, that your application reads and puts into context because *it*
decided to.

```
resources/list  → [{"uri": "notes://all", "name": "All notes", "mimeType": "text/plain"}]
resources/read  {"uri": "notes://all"}  → the contents
```

The model does not ask for a resource. Your code fetches it and includes it, the way an IDE
plugin includes the open file without the model requesting it.

The distinction matters because it changes who is responsible. A tool call is the model's
decision, and it can be wrong. A resource is your application's decision, and it is
predictable.

### Prompts — user-controlled

A prompt is a named template the server offers and the user picks — the thing behind a `/`
command in a chat interface.

```
prompts/list  → [{"name": "summarise_week", "description": "Summarise this week's notes"}]
prompts/get   {"name": "summarise_week"}  → a ready-made message list
```

The server author knows how to ask their own service a good question. A prompt is how they
ship that knowledge alongside the tools.

### Why this is worth knowing

Two reasons.

**Reading other people's servers.** A server offering only tools is doing the minimum. One
that offers resources and prompts is a more complete integration, and knowing the difference
tells you what you are looking at.

**Designing your own.** The common mistake is to make everything a tool. If your server
exposes read-only data that the application should always include, that is a resource, and
making it a tool means hoping the model remembers to ask.

Our server in the next lesson offers tools and one resource. Prompts we will mention and skip
— they are the least used of the three, and the concept is now in your head, which is what
matters.

> Tools are chosen by the model, resources by the application, prompts by the user. Three
> menus, three decision-makers.

### Try this before the next lesson

Take the three services you listed in 5.1. For each, sort what you want into the three
categories.

You will find most things are tools, one or two are resources, and prompts are rare. That
ratio is normal, and now you know it is a choice rather than a limit.

---

## Lesson 5.4 — Lab: write an MCP server in one file

### The plan

A notes server. Three tools and one resource, in one file, in about sixty lines.

```bash
pip install mcp
```

### The server

Save as `notes_server.py`:

```python
import json
from pathlib import Path

from mcp.server import MCPServer

mcp = MCPServer("notes")
NOTES = Path("notes.json")


def load():
    return json.loads(NOTES.read_text()) if NOTES.exists() else []


def save(notes):
    NOTES.write_text(json.dumps(notes, indent=2))


@mcp.tool()
def add_note(text: str) -> str:
    """Add a note to the notebook.

    Use this when the user wants something written down for later.

    Args:
        text: The note to save.
    """
    notes = load()
    notes.append(text)
    save(notes)
    return f"Added note {len(notes)}: {text}"


@mcp.tool()
def list_notes() -> str:
    """List every note in the notebook, numbered.

    Use this when the user asks what has been written down.
    """
    notes = load()
    if not notes:
        return "The notebook is empty."
    return "\n".join(f"{i}. {n}" for i, n in enumerate(notes, 1))


@mcp.tool()
def delete_note(number: int) -> str:
    """Delete one note by its number.

    Use this only when the user explicitly asks to remove a note.

    Args:
        number: The note's number, as shown by list_notes.
    """
    notes = load()
    if not 1 <= number <= len(notes):
        return f"There is no note {number}. There are {len(notes)} notes."
    removed = notes.pop(number - 1)
    save(notes)
    return f"Deleted: {removed}"


@mcp.resource("notes://all")
def all_notes() -> str:
    """The full contents of the notebook."""
    return "\n".join(load()) or "(empty)"


if __name__ == "__main__":
    mcp.run()
```

### Read what you just wrote

Notice how little of this is MCP.

Three functions with docstrings and type hints. The decorator turns the type hints into
`inputSchema` and the docstring into `description` — the same two jobs you did by hand in
Module 2, done by a library.

And notice that Lessons 2.2 and 2.3 still apply in full. `"Use this when the user wants
something written down for later"` is a trigger sentence. `"Use this only when the user
explicitly asks to remove a note"` is a boundary on a destructive action. The library writes
the schema. It does not write your descriptions, and descriptions are still where failures
live.

### Talk to it by hand

Before connecting an agent, drive it yourself. This is the payoff for Lesson 5.2:

```bash
python3 notes_server.py
```

It waits on stdin. Paste this and press Enter:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"me","version":"1"}}}
```

You get a result back. Then:

```json
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

There is your menu, with the schemas generated from your type hints. Then call one:

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"add_note","arguments":{"text":"Call the plumber"}}}
```

Check `notes.json`. Your note is there.

You just used an MCP server with no model, no agent, and no client library. That is worth
sitting with — it is the clearest possible demonstration that MCP is a plain protocol and not
an AI thing.

### Try this before the next lesson

Add a `search_notes` tool. Write the docstring before the code, and give it a trigger
sentence.

Then check it appears in `tools/list` by hand. Getting used to inspecting the menu directly
will save you an hour the first time a real server misbehaves.

---

## Lesson 5.5 — Lab: make Rover an MCP client

### The plan

Rover connects to the notes server, gets its menu, and uses it — alongside its own file tools.

```bash
pip install mcp
```

The MCP client library needs Python 3.10 or newer, which is why the course asked for it.

### The client

MCP's Python client is asynchronous, so this file is `async`. Save as `rover_mcp.py`:

```python
import asyncio
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from llm import connect

llm = connect("ollama:gemma4")


def to_our_shape(mcp_tool):
    """An MCP tool description, in the shape our tools have used since Module 2."""
    return {
        "name": mcp_tool.name,
        "description": mcp_tool.description or "",
        "input_schema": mcp_tool.input_schema,
    }


async def main():
    # sys.executable, not "python3": the server must run on the same interpreter
    # you installed mcp into, not whichever python happens to be on PATH.
    server = StdioServerParameters(command=sys.executable, args=["notes_server.py"])

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()                      # the handshake from 5.2

            listed = await session.list_tools()             # tools/list from 5.2
            print("The server offers:", [t.name for t in listed.tools])

            TOOLS = [to_our_shape(t) for t in listed.tools]

            messages = [{"role": "user", "content":
                         "Note that the report is due Friday, then list my notes."}]

            for _ in range(10):
                reply = llm.send(messages, TOOLS)
                if reply.text:
                    print(reply.text)

                messages.append({"role": "assistant", "content": reply.text,
                                 "tool_calls": reply.tool_calls})
                if not reply.wants_tool:
                    break

                results = []
                for call in reply.tool_calls:
                    print(f"[{call.name} {call.arguments}]")
                    out = await session.call_tool(call.name, call.arguments)  # tools/call
                    text = "".join(c.text for c in out.content
                                   if getattr(c, "text", None))
                    results.append({"id": call.id, "content": text,
                                    "is_error": bool(out.is_error)})

                messages.append({"role": "tool_results", "results": results})


asyncio.run(main())
```

### What each step is

Four lines carry the whole idea:

```python
async with stdio_client(server) as (read, write):     # start it, get the pipes
    async with ClientSession(read, write) as session:  # wrap them in the protocol
        await session.initialize()                     # the handshake from 5.2
        listed = await session.list_tools()            # tools/list from 5.2
```

Then the translation, which is the whole point of the lesson:

```python
def to_our_shape(mcp_tool):
    return {"name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "input_schema": mcp_tool.input_schema}
```

Three fields in, three fields out. Look at how little happens there. An MCP tool description
and the tool dictionaries you have been writing since Module 2 are **the same thing**, and
this function is the proof.

Two details worth noticing:

**The loop is unchanged.** It is the loop from Lesson 1.7, line for line. The only difference
is where `TOOLS` came from and that `run_tool` has been replaced by `session.call_tool`. An
MCP tool is not a special kind of tool — it is a tool whose implementation happens to live in
another process.

**On the wire it is `inputSchema`; in Python it is `input_schema`.** Lesson 5.2 showed you the
camelCase JSON, because that is what actually travels. The Python library renames it to suit
Python. Both are correct, and knowing that the wire and the binding can differ will save you
confusion the first time you compare a packet capture with your code.

Some providers ship a helper that skips this translation for you. You have now written it, so
you know exactly what such a helper does — about six lines.

### Watch it happen

Run it:

```bash
python3 rover_mcp.py
```

You should see the server's tool names, then Rover adding a note and listing them. Check
`notes.json`.

Two processes. Your agent asked a separate program to do something, over a pipe, in a format
either of them could have implemented from the spec.

### Both menus at once

The real payoff is mixing. Rover's own file tools plus the server's:

```python
TOOLS = [read_file_tool, list_files_tool] + [to_our_shape(t) for t in listed.tools]
```

Now ask: *"Read notes.txt and save each line as a separate note."*

Rover uses its own tool to read the file and the server's tool to store each line. It has no
idea some tools are local and some are a subprocess. It sees one menu, because that is all a
menu ever was.

### The other kind of MCP client — provider-specific

There is a second way, worth knowing about even though it is not portable.

Some providers will connect to a hosted MCP server **for** you. You name the server in the
request, the provider's infrastructure speaks MCP to it, and you never run a subprocess or
touch a client library. Anthropic's version looks like this:

```python
# Anthropic-specific. Other providers have their own version, or none.
response = client.beta.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    betas=["mcp-client-2025-11-20"],
    mcp_servers=[{"type": "url", "name": "notes", "url": "https://example.com/mcp"}],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "notes"}],
    messages=[{"role": "user", "content": "What notes do I have?"}],
)
```

Both parts are required there: `mcp_servers` says where the server is, and the `mcp_toolset`
entry in `tools` says to actually use it. Sending the first without the second is rejected — a
common first-try error.

**Which to use:**

| Situation | Route |
|---|---|
| The server touches your machine | The subprocess client you just wrote |
| You want it to work on any provider | The subprocess client |
| A hosted server, and your provider offers this | Either — theirs is less code |

Note what the hosted route costs you. Your conversation and the server's responses pass
through the provider's infrastructure, and the feature exists on their timetable, not yours.
The client you wrote in this lesson works with every provider in this course and with any
future one, because it only depends on the protocol.

> An MCP client is four calls: start it, handshake, list, translate. The helper does the
> translation you could now write yourself.

### Try this before the next lesson

Give Rover both menus and ask for something that needs both.

Then stop the server file from existing — rename `notes_server.py` — and run again. Read the
error. Knowing what a dead MCP server looks like is worth the thirty seconds.

---

## Lesson 5.6 — stdio or HTTP: transports, and which one you actually want

### Try this first

Look at what `stdio_client` did: it started `python3 notes_server.py` as a **subprocess** of
your agent.

That has a consequence people miss. The server runs on your machine, as your user, with your
permissions, and it dies when your agent does.

### The two transports

| | **stdio** | **HTTP** |
|---|---|---|
| Where the server runs | Your machine, as a subprocess | Anywhere |
| Who starts it | Your client | Already running |
| Lifetime | Dies with the client | Long-lived |
| Users | One | Many |
| Authentication | None — it is already you | Needed |
| Good for | Local files, git, databases on your box | Hosted services, shared teams |

### stdio is the right default for local work

If the server touches your machine — your files, your git repo, your local database — stdio is
correct. There is no network, no port, no auth to configure, and no way for anyone else to
reach it.

The lifetime property is genuinely useful: one client, one server process, no shared state to
get confused about, and everything is cleaned up when you exit.

### HTTP is for servers you did not start

A hosted service cannot be a subprocess of your agent. It is running somewhere, serving many
clients, and it needs to know who you are.

That last point is the real difference. With stdio, authentication is meaningless — the server
is already running as you. With HTTP, every request needs credentials, and you now have a
secret to store, rotate, and keep out of your transcript.

That is not a small step up in complexity. It is most of the reason hosted MCP has more moving
parts than local MCP.

### The security shift

Worth stating plainly, because it changes what you are responsible for:

**stdio:** the server has your permissions. Its capabilities are bounded by your account, and
you are trusting the server's code the way you trust anything you `pip install`.

**HTTP:** you send a credential to somebody else's machine, and their server acts on your
behalf. You are trusting their code, their operations, and their retention policy. What you
send them leaves your machine.

Neither is safer in the abstract. They fail differently, and you should know which failure you
are signing up for.

### Choosing

A short decision:

- Does it touch the machine the agent runs on? → **stdio**
- Do you run it yourself, for yourself? → **stdio**
- Is it a service for many people? → **HTTP**
- Did somebody else already host it? → **HTTP**, and you had no choice

Most servers you write will be stdio. Most servers you consume from vendors will be HTTP.

> stdio means the server is you. HTTP means the server is someone else, and everything about
> credentials and trust follows from that one difference.

### Try this before the next lesson

Look at the MCP servers you already have configured, in whatever agent tool you use. For each,
work out which transport it uses and what permissions it therefore has.

If any of them is stdio and you have not read what it does, that is a `pip install` you made
without looking.

---

## Lesson 5.7 — Publishing a server other people can trust

### The situation

Your notes server works. You want to share it, or you want to evaluate somebody else's before
running it. Same checklist either way.

### What "trust" means for a stdio server

A stdio MCP server runs as a subprocess with your permissions. Installing one is exactly as
consequential as installing any other package, and rather more than most people treat it.

Before you run one:

| Check | Why |
|---|---|
| Read the tool list | The menu is the capability list. Surprises live here |
| Look for shell execution | A server with a shell tool is a shell tool |
| Check what it reads | Anything in the file system, or a scoped folder? |
| Check the network | Does it phone anywhere? With what? |
| Look at dependencies | Same supply chain as any package |

That is not paranoia. It is the same reading you would do before adding a dependency, applied
to something that will be handed to a model and invoked automatically.

### What makes a server good to publish

Six things, roughly in order of how much they help the person using it:

**1. Descriptions with trigger sentences.** Everything in Module 2. Your descriptions are the
entire interface for the model, and the person installing your server cannot fix them without
forking you.

**2. A narrow scope.** A notes server should touch notes. A server that adds "and also runs
shell commands, for convenience" is now a shell server with a notes feature.

**3. Useful errors.** Lesson 2.5, over a pipe. `"There is no note 7. There are 3 notes."`
saves a turn every time.

**4. Read-only where possible.** Split reading from writing. If someone only needs to query,
do not make them accept a server that can also delete.

**5. Honest names.** `delete_note` deletes a note. Do not call a destructive tool
`update_note` because it sounds gentler — the model reads the name too.

**6. A README that says what it touches.** Which files, which network hosts, which
credentials. Three lines, and it is the thing every careful person looks for and rarely finds.

### Confirmation belongs to the client

You may be tempted to build "are you sure?" into your server. Do not.

The permission layer belongs in the client, where the human is — that is Lesson 3.4, and it is
the right place because the client knows the user, the interface, and the policy. Your server
cannot prompt anybody; it is talking down a pipe.

What you can do is make it obvious which tools need care: name them clearly, describe the
consequence in the description, and keep destructive operations separate from safe ones so a
client can treat them differently.

### Versioning the menu

The tool list is your API. Removing a tool or renaming an argument breaks every agent using
you, and it breaks in a particularly annoying way — the model calls a tool that no longer
exists and improvises around the failure.

Add rather than change. If you must change, keep the old name working for a while. The
protocol has a version field, but your *menu* is the contract, and nothing enforces it but
you.

> A stdio MCP server runs with the user's permissions. Publishing one is a promise, and the
> tool list is the promise you are making.

### Try this before the next module

Write a README for your notes server. Three sections: what it does, what it touches, how to
run it.

Then read it as somebody who has never seen it. Would you run this on your own machine? If
not, fix the server, not the README.

---

## Production notes (not for learners)

- **5.4 is now verified by execution** (2026-08-12, `mcp` 2.0.0). The server was extracted
  verbatim from the lesson, driven by hand with the exact JSON-RPC from 5.2, and answered
  `initialize` → `tools/list` (all three tools) → `tools/call` (wrote `notes.json`). That run
  validates 5.2's wire format at the same time.
- **⚠️ Version-sensitive: this lesson requires `mcp` 2.x.** It was first drafted against 1.x,
  where the server class was `FastMCP` in `mcp.server.fastmcp`; in 2.0 that module does not
  exist and the class is `MCPServer` in `mcp.server`. The decorators (`@mcp.tool()`,
  `@mcp.resource()`) and `mcp.run()` are unchanged. Pin `mcp>=2` in the course requirements
  and re-check on any major bump — this is the fastest-moving dependency in the course.
  Lesson 5.5's client imports (`ClientSession`, `stdio_client`, `StdioServerParameters`) were
  unaffected by the 1.x → 2.x move and are confirmed working.
- **5.2's wire format is the durable part.** JSON-RPC 2.0 with `initialize` / `tools/list` /
  `tools/call` is the protocol, not a library API, so it will outlive any package churn. If
  5.4 needs rewriting after a library change, 5.2 does not.
- **Two videos.** 5.4 — driving the server by hand, pasting JSON into stdin and watching
  `notes.json` change. That is the "it is just a protocol" moment and it is worth filming
  slowly. 5.5 — Rover using both menus at once, with the point made out loud that it cannot
  tell which tools are local.
- **Diagram (Lesson 5.1): M×N before and after.** Reuse the ASCII sketch as proper artwork.
  It is the only diagram most MCP explanations have, and ours is fine — the differentiation is
  in 5.2, not here.
- **The by-hand protocol exercise in 5.2 and 5.4 is the module's core teaching move.** If
  either gets cut for length, the module becomes another paste-this-config tutorial and the
  course loses its main claim. Protect both.
- **5.3 (resources and prompts) is the most cuttable lesson if the module runs long.** It is
  conceptually valuable and least used in practice. If cut, fold the tools/resources
  distinction into 5.1 as two paragraphs rather than dropping it entirely.
- **5.5 is now verified by execution too** (2026-08-12, `mcp` 2.0.0 + `ollama:gemma4`). The
  client was extracted verbatim from the lesson and run against the 5.4 server: it listed the
  three tools, called `add_note` then `list_notes` across two turns, answered correctly, and
  the server persisted `notes.json`. Both labs in this module are confirmed working on the
  free path.
- **`sys.executable` in 5.5 is a bug fix, not a style choice.** The first draft used
  `command="python3"` and the server died on launch with a bare `MCPError: Connection closed`
  — because PATH's python did not have `mcp` installed. That error names nothing useful, so a
  learner would have no idea why. Do not let anyone "simplify" it back.
- **`Tool.input_schema` is snake_case in the Python binding** while the wire format in 5.2 is
  `inputSchema`. Both are correct and the lesson now says so explicitly. Re-check on any major
  `mcp` bump, since this is exactly the sort of thing that gets renamed.
- **Check before shipping:** the `mcp-client-2025-11-20` beta flag and that the hosted
  connector still needs **both** `mcp_servers` and a matching `mcp_toolset` entry (both are
  Anthropic-specific and clearly marked as such in 5.5), plus the current MCP
  `protocolVersion` string in the 5.2 examples.
