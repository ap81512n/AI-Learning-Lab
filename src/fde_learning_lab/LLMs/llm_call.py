from fde_learning_lab.LLMs.adapater import build_model_adapter

adapter = build_model_adapter()

result = adapter.generate(
    instructions=(
        "Answer only from the supplied PDF excerpt. "
        "If the answer is missing, say you do not know."
    ),
    prompt=(
        "PDF text:System requires 2 approvals "
        "before release.\n"
        "Question: How many approvals are required?"
    ),
)

print(result.text)
print(result.input_tokens, result.output_tokens)
print(result.estimated_cost_usd)