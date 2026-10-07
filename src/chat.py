"""Chat grounded in one analysis JSON. Advice and flood questions are refused in code."""

import json
import os
import re

from rates import CHAT_USER_MESSAGE_CAP, DEFAULT_ANTHROPIC_MODEL
from schemas import AnalysisResult, ChatRequest, ChatResponse

_ADVICE = re.compile(
    r"should i .*(loan|buy|sign|borrow|offer)|financial advice|legal advice|is it (safe|legal)",
    re.IGNORECASE,
)

_DISABLED = "The assistant is off until ANTHROPIC_API_KEY is set. Price and cost results above still stand."
_CAP = "This session has reached 12 questions. Start a new analysis to ask more."
_REFUSE_ADVICE = (
    "I can't give financial or legal advice. I can only explain the figures already in this analysis."
)
_NO_INFO = "I don't have that information."


def refusal_for(question: str) -> str | None:
    if "flood" in question.casefold():
        return _NO_INFO
    if _ADVICE.search(question):
        return _REFUSE_ADVICE
    return None


def build_system_prompt(analysis: AnalysisResult) -> str:
    payload = json.dumps(analysis.model_dump(mode="json"), indent=2)
    return (
        "You are HomeTruth's assistant. You explain one property analysis.\n"
        "Rules:\n"
        "- Use only numbers and facts present in the analysis JSON below.\n"
        '- If the user asks for something that is not in the JSON, say "I don\'t have that information."\n'
        "- Never give financial or legal advice. If asked whether to buy, borrow, or sign, refuse and point at the computed figures only.\n"
        "- Keep answers to a short paragraph.\n"
        "- Do not invent prices, distances, risks, flood data, legal status, or future returns.\n\n"
        "Analysis JSON:\n"
        f"{payload}"
    )


def _history_messages(request: ChatRequest) -> list[dict]:
    messages: list[dict] = []
    for item in request.messages:
        content = item.content.strip()
        if item.role not in {"user", "assistant"} or not content:
            continue
        if messages and messages[-1]["role"] == item.role:
            messages[-1]["content"] += "\n" + content
        else:
            messages.append({"role": item.role, "content": content})
    if messages and messages[0]["role"] != "user":
        messages = messages[1:]
    messages.append({"role": "user", "content": request.user_message.strip()})
    return messages


def _user_turns(request: ChatRequest) -> int:
    return sum(1 for item in request.messages if item.role == "user")


def respond(request: ChatRequest, client=None) -> ChatResponse:
    if _user_turns(request) >= CHAT_USER_MESSAGE_CAP:
        return ChatResponse(text=_CAP, capped=True)
    question = request.user_message.strip()
    if not question:
        return ChatResponse(text=_NO_INFO, refused=True)
    preset = refusal_for(question)
    if preset is not None:
        return ChatResponse(text=preset, refused=True)
    system = build_system_prompt(request.analysis)
    messages = _history_messages(request)
    if client is not None:
        text = client(system, messages)
        return ChatResponse(text=text or _NO_INFO)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return ChatResponse(text=_DISABLED, disabled=True)
    text = _anthropic_complete(system, messages)
    return ChatResponse(text=text or _NO_INFO)


def _anthropic_complete(system: str, messages: list[dict]) -> str:
    import anthropic

    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    api = anthropic.Anthropic()
    response = api.messages.create(model=model, max_tokens=400, system=system, messages=messages)
    parts = []
    for block in response.content:
        text = getattr(block, "text", "")
        if text:
            parts.append(text)
    return "\n".join(parts).strip()
