"""Second symbolic encoder for the independent expression IR.

This module does not call ``translate_to_z3`` or ``_translate_node``. When
``z3`` is installed it builds its own integer or bit-vector terms and asks
whether a differentiating model exists. When ``z3`` is absent the verdict is
``unavailable``.

Two encoders that share Z3 are not independent proofs. A shared solver bug
can still affect both.
"""

from __future__ import annotations

from dataclasses import dataclass

from veriforge.config import SemanticConfiguration
from veriforge.independent_parser import IBinary, IExpr, ILit, IUnary, IVar, variables_of
from veriforge.models import SemanticMode

try:
    import z3
except ImportError:
    z3 = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class EncoderResult:
    verdict: str
    detail: str
    witness: dict[str, int] | None = None
    elapsed_seconds: float | None = None


def z3_available() -> bool:
    return z3 is not None


def encode_difference(
    original: IExpr,
    candidate: IExpr,
    config: SemanticConfiguration,
) -> EncoderResult:
    """Encode both expressions independently and compare them with Z3."""

    if z3 is None:
        return EncoderResult(
            verdict="unavailable",
            detail="z3-solver is not installed; independent encoder did not run",
        )
    from time import perf_counter

    started = perf_counter()
    try:
        names = sorted(variables_of(original) | variables_of(candidate))
        env = {name: _symbol(name, config) for name in names}
        left = _encode(original, config, env)
        right = _encode(candidate, config, env)
        solver = z3.Solver()
        timeout_ms = max(1, int(config.limits.solver_timeout_seconds * 1000))
        solver.set("timeout", timeout_ms)
        solver.add(left != right)
        check = solver.check()
    except Exception as exc:  # noqa: BLE001
        return EncoderResult(
            verdict="translation_error",
            detail=f"independent encoder failed: {exc}",
            elapsed_seconds=perf_counter() - started,
        )
    elapsed = perf_counter() - started
    if check == z3.unsat:
        return EncoderResult(
            verdict="equivalent",
            detail="independent encoder: unsat",
            elapsed_seconds=elapsed,
        )
    if check == z3.unknown:
        reason = ""
        try:
            reason = solver.reason_unknown() or ""
        except Exception:  # noqa: BLE001
            reason = ""
        lowered = reason.lower()
        if any(marker in lowered for marker in ("timeout", "canceled", "cancelled", "interrupted")):
            return EncoderResult(
                verdict="timeout",
                detail=reason or "independent encoder timeout",
                elapsed_seconds=elapsed,
            )
        return EncoderResult(
            verdict="unknown",
            detail=reason or "independent encoder UNKNOWN",
            elapsed_seconds=elapsed,
        )
    if check == z3.sat:
        model = solver.model()
        witness: dict[str, int] = {}
        for name, symbol in env.items():
            value = model.eval(symbol, model_completion=True).as_long()
            if config.mode is SemanticMode.MODE_B:
                if value < 0 or value > config.max_unsigned:
                    return EncoderResult(
                        verdict="translation_error",
                        detail=f"encoder model value for {name} is outside unsigned range",
                        elapsed_seconds=elapsed,
                    )
            witness[name] = value
        return EncoderResult(
            verdict="counterexample",
            detail="independent encoder: sat",
            witness=witness,
            elapsed_seconds=elapsed,
        )
    return EncoderResult(
        verdict="verification_error",
        detail=f"unrecognized encoder result {check!r}",
        elapsed_seconds=elapsed,
    )


def _symbol(name: str, config: SemanticConfiguration):
    assert z3 is not None
    if config.mode is SemanticMode.MODE_A:
        return z3.Int(f"indy_{name}")
    if config.mode is SemanticMode.MODE_B:
        return z3.BitVec(f"indy_{name}", config.bit_width)
    raise ValueError(f"unsupported mode {config.mode}")


def _encode(node: IExpr, config: SemanticConfiguration, env: dict):
    assert z3 is not None
    if isinstance(node, ILit):
        if config.mode is SemanticMode.MODE_A:
            return z3.IntVal(node.value)
        if node.value < 0 or node.value > config.max_unsigned:
            raise ValueError(f"Mode B literal {node.value} out of range")
        return z3.BitVecVal(node.value, config.bit_width)
    if isinstance(node, IVar):
        return env[node.name]
    if isinstance(node, IUnary):
        operand = _encode(node.operand, config, env)
        if node.op == "+":
            return operand
        if node.op == "-":
            return -operand
        raise ValueError(node.op)
    if isinstance(node, IBinary):
        left = _encode(node.left, config, env)
        right = _encode(node.right, config, env)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        raise ValueError(node.op)
    raise ValueError(type(node).__name__)
