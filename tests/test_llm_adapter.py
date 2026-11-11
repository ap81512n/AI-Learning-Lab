
from types import SimpleNamespace

from fde_learning_lab.LLMs.adapater import OpenAIModelAdapter


def test_adapter_tracks_usage_without_real_api(caplog):
    def fake_create(**kwargs):
        assert kwargs["model"] == "test-model"
        return SimpleNamespace(
            output_text="The PDF describes three steps.",
            model="test-model",
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=50,
            ),
        )

    fake_client = SimpleNamespace(
        responses=SimpleNamespace(create=fake_create)
    )

    adapter = OpenAIModelAdapter(
        model="test-model",
        input_rate=1.0,
        output_rate=2.0,
        client=fake_client,
    )

    with caplog.at_level("INFO"):
        result = adapter.generate(
            instructions="Answer using document text",
            prompt="CONFIDENTIAL_SAMPLE_DOCUMENT",
        )

    assert result.text == "The PDF describes three steps."
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.estimated_cost_usd == 0.0002
    assert result.latency_ms >= 0

    # Sensitive prompt contents should not enter logs.
    assert "CONFIDENTIAL_SAMPLE_DOCUMENT" not in caplog.text
