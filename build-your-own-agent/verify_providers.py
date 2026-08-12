#!/usr/bin/env python3
"""Round-trip every provider through llm.py and report what actually works.

Tests each provider whose key is present. Skips the rest. Never prints a key.

    python3 verify_providers.py

Env vars used (any subset):
    OPENAI_API_KEY      ANTHROPIC_API_KEY      GOOGLE_API_KEY / GEMINI_API_KEY
Local Ollama is tried automatically if the daemon answers.

Each provider gets three checks:
    1. plain call          — does a bare request work at all
    2. tool request        — does it ask for the tool, with usable arguments
    3. result round trip   — does it accept the result back and answer
"""
import os
import sys
import traceback

from llm import connect

TOOLS = [{
    "name": "read_file",
    "description": (
        "Return the full text contents of a file. "
        "Use this when you need to know what is written inside a file."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "File to read"}},
        "required": ["path"],
    },
}]

NOTES = "Buy milk. Call the plumber. Finish the report by Friday."


def check(spec):
    """Return (results dict, error string or None)."""
    r = {"plain": False, "tool_request": False, "round_trip": False}
    try:
        llm = connect(spec)

        # 1. plain call
        reply = llm.send([{"role": "user", "content": "Say OK and nothing else."}])
        r["plain"] = bool(reply.text)
        r["_stop_plain"] = reply.stop

        # 2. tool request
        messages = [{"role": "user",
                     "content": "What is in notes.txt? Summarise it in one line."}]
        reply = llm.send(messages, TOOLS)
        r["_stop_tool"] = reply.stop
        if not reply.wants_tool:
            return r, "model did not ask for the tool (may be a weak model, not a bug)"
        call = reply.tool_calls[0]
        r["tool_request"] = (call.name == "read_file"
                             and isinstance(call.arguments, dict)
                             and "path" in call.arguments)
        r["_args"] = call.arguments

        # 3. send the result back and get a final answer
        messages.append({"role": "assistant", "content": reply.text,
                         "tool_calls": reply.tool_calls})
        messages.append({"role": "tool_results",
                         "results": [{"id": call.id, "content": NOTES,
                                      "is_error": False}]})
        final = llm.send(messages, TOOLS)
        r["round_trip"] = bool(final.text) and not final.wants_tool
        r["_answer"] = (final.text or "").strip()[:90]
        return r, None
    except Exception as e:
        return r, f"{type(e).__name__}: {e}"


def suggest_models(provider):
    """If a model name is stale, show what this key can actually reach."""
    try:
        if provider == "openai":
            import openai
            names = [m.id for m in openai.OpenAI().models.list()]
            return sorted(n for n in names if n.startswith("gpt"))[:12]
        if provider == "gemini":
            from google import genai
            names = [m.name for m in genai.Client().models.list()]
            return [n for n in names if "gemini" in n][:12]
        if provider == "anthropic":
            import anthropic
            return [m.id for m in anthropic.Anthropic().models.list()][:12]
        if provider == "ollama":
            import json
            import urllib.request
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as f:
                return [m["name"] for m in json.load(f).get("models", [])]
    except Exception as e:
        return [f"(could not list models: {type(e).__name__})"]
    return []


def ollama_up():
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


def main():
    targets = []
    if os.environ.get("OPENAI_API_KEY"):
        targets.append(("openai", os.environ.get("VERIFY_OPENAI_MODEL", "gpt-4o-mini")))
    if os.environ.get("ANTHROPIC_API_KEY"):
        targets.append(("anthropic", os.environ.get("VERIFY_ANTHROPIC_MODEL", "claude-opus-5")))
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        targets.append(("gemini", os.environ.get("VERIFY_GEMINI_MODEL", "gemini-2.5-flash")))
    if ollama_up():
        targets.append(("ollama", os.environ.get("VERIFY_OLLAMA_MODEL", "gemma4")))

    if not targets:
        print("No provider keys found and no local Ollama. Nothing to test.")
        print("Set one of OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY.")
        return 1

    print(f"Testing {len(targets)} provider(s). Keys are never printed.\n")
    failures = 0
    for provider, model in targets:
        spec = f"{provider}:{model}"
        print(f"--- {spec}")
        r, err = check(spec)
        for step in ("plain", "tool_request", "round_trip"):
            print(f"      {'PASS' if r[step] else 'FAIL'}  {step}")
        if r.get("_stop_tool"):
            print(f"      stop word on tool turn: {r['_stop_tool']!r}")
        if r.get("_args"):
            print(f"      arguments parsed as: {r['_args']}")
        if r.get("_answer"):
            print(f"      final answer: {r['_answer']}")
        if err:
            print(f"      NOTE: {err}")
            if not r["plain"]:
                avail = suggest_models(provider)
                if avail:
                    print(f"      models this key can reach: {', '.join(map(str, avail))}")
                    print(f"      re-run with: VERIFY_{provider.upper()}_MODEL=<name>")
        if not all(r[s] for s in ("plain", "tool_request", "round_trip")):
            failures += 1
        print()

    print(f"{len(targets) - failures}/{len(targets)} provider(s) fully round-tripped.")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
