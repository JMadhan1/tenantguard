"""Model prices ($ per 1M tokens) to turn token usage into a cost per fix."""

PRICES = {
    "claude-opus-5-5":   {"input": 4.00, "output": 20.00},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00},
    "claude-haiku-5-5":  {"input": 0.10, "output": 0.50},
}
_DEFAULT = {"input": 2.00, "output": 10.00}


def cost_usd(model, input_tokens, output_tokens):
    p = PRICES.get(model, _DEFAULT)
    return round(input_tokens / 1e6 * p["input"] + output_tokens / 1e6 * p["output"], 6)
