"""The Bedrock provider must route, parse and price responses without touching the network."""

from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

from aeotools import llm


class FakeClaude:
    def __init__(self):
        self.messages = self
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text="Try Acme.")],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=200), stop_reason="end_turn")


class FakeRuntime:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def converse_reply(text, pin=900, pout=150):
    return {"output": {"message": {"content": [{"reasoningContent": {"reasoningText": {"text": "Acme?"}}},
                                               {"text": text}]}},
            "usage": {"inputTokens": pin, "outputTokens": pout}, "stopReason": "end_turn"}


def client_error(code, message):
    return ClientError({"Error": {"Code": code, "Message": message}}, "Converse")


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setattr(llm, "_converse_fixes", {})

    def install(*responses):
        fake = FakeRuntime(responses)
        monkeypatch.setattr(llm, "_bedrock_runtime_client", lambda: fake)
        return fake
    return install


def test_claude_goes_through_the_messages_api(monkeypatch):
    fake = FakeClaude()
    monkeypatch.setattr(llm, "_bedrock_claude_client", lambda: fake)
    res = llm.complete("bedrock:anthropic.claude-opus-5-5", "sys", "Which tool?", max_tokens=4000)
    assert res.text == "Try Acme." and res.error is None
    assert fake.calls[0]["model"] == "anthropic.claude-opus-5-5"
    assert "temperature" not in fake.calls[0] and fake.calls[0]["output_config"] == {"effort": "low"}
    assert res.cost_usd == pytest.approx((1000 * 4.40 + 200 * 22.00) / 1e6)


def test_other_models_use_converse_and_drop_reasoning(runtime):
    fake = runtime(converse_reply("<think>maybe Acme</think>Brightly is best."))
    res = llm.complete("bedrock:openai.gpt-oss-120b-1:0", "sys", "Which tool?", max_tokens=4000)
    assert res.text == "Brightly is best."
    assert (res.input_tokens, res.output_tokens, res.stop_reason) == (900, 150, "end_turn")
    sent = fake.calls[0]
    assert sent["modelId"] == "openai.gpt-oss-120b-1:0" and sent["system"] == [{"text": "sys"}]
    assert sent["inferenceConfig"] == {"maxTokens": 4000, "temperature": 0.0}
    assert "additionalModelRequestFields" not in sent and res.notes == ""


def test_gpt_models_run_at_low_effort_and_remember_refused_settings(runtime):
    fake = runtime(client_error("ValidationException", "temperature is not supported with this model."),
                   converse_reply("Acme."), converse_reply("Brightly."))
    first = llm.complete("bedrock:global.openai.gpt-6.1-sol", "sys", "Which tool?")
    second = llm.complete("bedrock:global.openai.gpt-6.1-sol", "sys", "Which tool?")
    assert (first.text, second.text) == ("Acme.", "Brightly.")
    assert len(fake.calls) == 3  # the refused setting is dropped for later calls too
    assert fake.calls[0]["additionalModelRequestFields"] == {"reasoning": {"effort": "low"}}
    assert "temperature" not in fake.calls[2]["inferenceConfig"]
    assert first.notes == second.notes == "default temperature"
    assert llm.price("bedrock:global.openai.gpt-6.1-sol") == (2.20, 11.00)


def test_models_without_system_prompts_get_it_in_the_user_turn(runtime):
    fake = runtime(client_error("ValidationException", "This model doesn't support system messages."),
                   converse_reply("Acme."))
    res = llm.complete("bedrock:mistral.mistral-7b-instruct-v0:2", "sys", "Which tool?")
    assert res.text == "Acme." and len(fake.calls) == 2
    assert "system" not in fake.calls[1]
    assert fake.calls[1]["messages"][0]["content"][0]["text"] == "sys\n\nWhich tool?"


def test_errors_are_recorded_not_raised(runtime):
    runtime(client_error("AccessDeniedException", "You don't have access to the model."))
    res = llm.complete("bedrock:meta.llama4-maverick-17b-instruct-v1:0", "sys", "Which tool?")
    assert res.error.startswith("AccessDeniedException") and res.text == "" and res.cost_usd == 0


def test_bedrock_prices_are_ceilings_with_a_pessimistic_default():
    assert llm.price("bedrock:anthropic.claude-haiku-5-5") == (0.11, 0.55)
    assert llm.price("bedrock:us.deepseek.v3-v1:0") == (1.05, 3.03)
    assert llm.price("bedrock:writer.palmyra-vision-7b") == llm.DEFAULT_PRICE
    assert llm.price("anthropic:claude-haiku-5-5") == (0.10, 0.50)
