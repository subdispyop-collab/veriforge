"""Guard: parsing and evaluation must not use eval or exec on user input."""

from __future__ import annotations

import builtins

import pytest

from veriforge import SemanticConfiguration, SemanticMode, evaluate, parse_expression


def test_parse_and_evaluate_without_eval_exec(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("eval/exec must not be called")

    monkeypatch.setattr(builtins, "eval", boom)
    monkeypatch.setattr(builtins, "exec", boom)

    cfg = SemanticConfiguration(mode=SemanticMode.MODE_A)
    expression = parse_expression("(x + 2) * 3", cfg)
    assert evaluate(expression, {"x": 4}, cfg) == 18

    cfg_b = SemanticConfiguration(mode=SemanticMode.MODE_B, bit_width=8)
    expression_b = parse_expression("200 + 100", cfg_b)
    assert evaluate(expression_b, {}, cfg_b) == 44
