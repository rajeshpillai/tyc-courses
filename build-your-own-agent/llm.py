"""llm.py — one small adapter so the same agent loop runs on any provider.

Providers differ in exactly three places:

  1. how you describe a tool
  2. how you spot a tool request in the reply
  3. how you send the result back

Everything else about an agent is the same everywhere. This file holds those
three differences and nothing else, so the rest of the course never mentions a
vendor.

Usage:

    llm = connect("ollama:gemma4")        # or anthropic:… / openai:… / gemini:…
    reply = llm.send(messages, TOOLS)
    if reply.wants_tool:
        ...

The transcript stays yours, in one neutral shape:

    [{"role": "user",         "content": "..."},
     {"role": "assistant",    "content": "...", "tool_calls": [ToolCall, ...]},
     {"role": "tool_results", "results": [{"id": ..., "content": ..., "is_error": False}]}]
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    raw: object = None
    # `raw` holds the provider's own representation of this call. Most providers
    # do not need it. Gemini does: its function-call parts carry an opaque
    # thought_signature that must be sent back unchanged, so we replay the
    # original part rather than rebuilding one from the fields above.


@dataclass
class Reply:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop: str = ""            # the provider's own word, kept for teaching
    usage: dict = field(default_factory=dict)
    raw: object = None        # escape hatch: the untouched provider response

    @property
    def wants_tool(self) -> bool:
        return bool(self.tool_calls)


# --------------------------------------------------------------------------
# Anthropic
# --------------------------------------------------------------------------
class AnthropicProvider:
    def __init__(self, model):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model

    def _tools(self, tools):
        # Already the neutral shape.
        return tools

    def _messages(self, messages):
        out = []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks = []
                if m.get("content"):
                    blocks.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls", []):
                    blocks.append({"type": "tool_use", "id": tc.id,
                                   "name": tc.name, "input": tc.arguments})
                out.append({"role": "assistant", "content": blocks})
            elif m["role"] == "tool_results":
                out.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": r["id"],
                     "content": r["content"], "is_error": r.get("is_error", False)}
                    for r in m["results"]]})
        return out

    def send(self, messages, tools=None, system=None, max_tokens=8000):
        kw = {"model": self.model, "max_tokens": max_tokens,
              "messages": self._messages(messages)}
        if tools:
            kw["tools"] = self._tools(tools)
        if system:
            kw["system"] = system
        r = self.client.messages.create(**kw)
        calls = [ToolCall(b.id, b.name, b.input) for b in r.content
                 if b.type == "tool_use"]
        text = "".join(b.text for b in r.content if b.type == "text")
        return Reply(text, calls, r.stop_reason,
                     {"in": r.usage.input_tokens, "out": r.usage.output_tokens}, r)


# --------------------------------------------------------------------------
# OpenAI — also drives Ollama and anything else OpenAI-compatible
# --------------------------------------------------------------------------
class OpenAIProvider:
    def __init__(self, model, base_url=None, api_key=None):
        import openai
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key or os.environ.get("OPENAI_API_KEY") or "not-needed",
        )
        self.model = model
        # Older models take max_tokens; newer ones reject it and want
        # max_completion_tokens. We do not know which this is until we ask, so
        # start with the old name and switch permanently on the first refusal.
        self._token_param = "max_tokens"

    def _tools(self, tools):
        return [{"type": "function",
                 "function": {"name": t["name"],
                              "description": t["description"],
                              "parameters": t["input_schema"]}}
                for t in tools]

    def _messages(self, messages, system=None):
        out = [{"role": "system", "content": system}] if system else []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                msg = {"role": "assistant", "content": m.get("content") or None}
                if m.get("tool_calls"):
                    msg["tool_calls"] = [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.name,
                                      "arguments": json.dumps(tc.arguments)}}
                        for tc in m["tool_calls"]]
                out.append(msg)
            elif m["role"] == "tool_results":
                # One message per result — this is OpenAI's shape, not a choice.
                for r in m["results"]:
                    out.append({"role": "tool", "tool_call_id": r["id"],
                                "content": str(r["content"])})
        return out

    def send(self, messages, tools=None, system=None, max_tokens=8000):
        kw = {"model": self.model, "messages": self._messages(messages, system)}
        if tools:
            kw["tools"] = self._tools(tools)

        try:
            r = self.client.chat.completions.create(
                **kw, **{self._token_param: max_tokens})
        except Exception as e:
            if "max_completion_tokens" not in str(e):
                raise
            self._token_param = "max_completion_tokens"
            r = self.client.chat.completions.create(
                **kw, **{self._token_param: max_tokens})
        choice = r.choices[0]
        calls = []
        for tc in (choice.message.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(tc.id, tc.function.name, args))
        usage = {}
        if r.usage:
            usage = {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}
        return Reply(choice.message.content or "", calls,
                     choice.finish_reason, usage, r)


# --------------------------------------------------------------------------
# Google Gemini
# --------------------------------------------------------------------------
class GeminiProvider:
    def __init__(self, model):
        from google import genai
        self.genai = genai
        self.client = genai.Client()
        self.model = model

    def _tools(self, tools):
        from google.genai import types as gt
        return [gt.Tool(function_declarations=[
            gt.FunctionDeclaration(name=t["name"],
                                   description=t["description"],
                                   parameters=t["input_schema"])
            for t in tools])]

    def _contents(self, messages):
        from google.genai import types as gt
        out = []
        for m in messages:
            if m["role"] == "user":
                out.append(gt.Content(role="user",
                                      parts=[gt.Part(text=m["content"])]))
            elif m["role"] == "assistant":
                parts = []
                if m.get("content"):
                    parts.append(gt.Part(text=m["content"]))
                for tc in m.get("tool_calls", []):
                    if tc.raw is not None:
                        parts.append(tc.raw)      # keeps thought_signature intact
                    else:
                        parts.append(gt.Part(function_call=gt.FunctionCall(
                            name=tc.name, args=tc.arguments)))
                out.append(gt.Content(role="model", parts=parts))
            elif m["role"] == "tool_results":
                out.append(gt.Content(role="user", parts=[
                    gt.Part(function_response=gt.FunctionResponse(
                        name=r["id"], response={"result": str(r["content"])}))
                    for r in m["results"]]))
        return out

    def send(self, messages, tools=None, system=None, max_tokens=8000):
        from google.genai import types as gt
        cfg = gt.GenerateContentConfig(
            max_output_tokens=max_tokens,
            system_instruction=system or None,
            tools=self._tools(tools) if tools else None,
        )
        r = self.client.models.generate_content(
            model=self.model, contents=self._contents(messages), config=cfg)
        calls, text = [], ""
        cand = (r.candidates or [None])[0]
        if cand and cand.content and cand.content.parts:
            for i, part in enumerate(cand.content.parts):
                if getattr(part, "function_call", None):
                    fc = part.function_call
                    # Gemini has no call id; the name is the handle. Keep the
                    # whole part so it can be replayed with its signature.
                    calls.append(ToolCall(fc.name, fc.name, dict(fc.args or {}), raw=part))
                elif getattr(part, "text", None):
                    text += part.text
        return Reply(text, calls, str(getattr(cand, "finish_reason", "")), {}, r)


# --------------------------------------------------------------------------
def connect(spec: str):
    """connect("anthropic:claude-opus-5") / "openai:gpt-5" /
       "gemini:gemini-2.5-flash" / "ollama:gemma4" """
    provider, _, model = spec.partition(":")
    provider = provider.lower()
    if provider == "anthropic":
        return AnthropicProvider(model)
    if provider == "openai":
        return OpenAIProvider(model)
    if provider == "gemini":
        return GeminiProvider(model)
    if provider == "ollama":
        return OpenAIProvider(model, base_url="http://localhost:11434/v1",
                              api_key="ollama")
    raise ValueError(f"Unknown provider {provider!r}. "
                     "Use anthropic, openai, gemini or ollama.")


DEFAULT = os.environ.get("ROVER_LLM", "ollama:gemma4")
