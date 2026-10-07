from chat import build_system_prompt, refusal_for, respond
from conftest import sample_analysis
from schemas import ChatMessage, ChatRequest


def _request(message: str, prior: int = 0) -> ChatRequest:
    history = []
    for index in range(prior):
        history.append(ChatMessage(role="user", content=f"Question {index}"))
        history.append(ChatMessage(role="assistant", content="A short note."))
    return ChatRequest(analysis=sample_analysis(), messages=history, user_message=message)


def test_system_prompt_is_limited_to_the_analysis_json():
    prompt = build_system_prompt(sample_analysis())
    assert 'say "I don\'t have that information."' in prompt
    assert "Never give financial or legal advice" in prompt
    assert "8000000" in prompt
    assert "flood" in prompt.casefold()
    assert "123456" not in prompt


def test_flood_and_loan_questions_are_refused_without_a_model():
    flood = respond(_request("Is it safe from floods?"))
    assert flood.refused is True
    assert flood.text == "I don't have that information."
    loan = respond(_request("Should I take this loan?"))
    assert loan.refused is True
    assert "financial or legal advice" in loan.text
    assert refusal_for("Should I buy this?") is not None


def test_missing_key_disables_ordinary_questions(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    reply = respond(_request("What is the verdict?"))
    assert reply.disabled is True
    assert "ANTHROPIC_API_KEY" in reply.text


def test_session_stops_at_twelve_user_messages():
    reply = respond(_request("What is the mid estimate?", prior=12))
    assert reply.capped is True
    assert "12" in reply.text


def test_mocked_client_only_receives_the_analysis(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    seen = {}

    def client(system, messages):
        seen["system"] = system
        seen["messages"] = messages
        return "The mid estimate in this analysis is Rs 80.00 lakh."

    reply = respond(_request("Why is the verdict fair?"), client=client)
    assert reply.disabled is False
    assert "80.00 lakh" in reply.text
    assert "8000000" in seen["system"]
    assert seen["messages"][-1]["content"] == "Why is the verdict fair?"
