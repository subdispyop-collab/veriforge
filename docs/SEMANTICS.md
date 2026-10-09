# Semantics

This document is the correctness contract for expression meaning. Phase 1 implements parsing, semantic configuration, and the reference evaluator for the initial grammar below. Solver translation, optimization, and verification are not part of Phase 1.

Source of the contract: sections 3, 5, and 6 of the controlling specification, plus the locked Phase 1 decisions of 2026-10-09.

## Selection

Every expression is interpreted in one explicitly selected mode. The active mode is part of the meaning. The interface, when it exists, must show the mode, the bit width where it applies, and the assumptions in force.

The two modes are not interchangeable. A result, rule, or counterexample from one mode is not a result about the other.

## Mode A — mathematical integers

Specified meaning:

- Each value is an unbounded mathematical integer.
- Binary addition, binary subtraction, and binary multiplication are the mathematical operations on those integers.
- Unary plus leaves the integer unchanged. Unary minus is mathematical negation.
- No fixed-width overflow is part of this mode.
- An optimization preserves meaning only when, for every assignment of integers to the variables, the original and the candidate denote the same integer.
- The specified solver encoding is a Z3 integer sort, not a bit-vector sort (Phase 2).

Phase 1 status: implemented by the reference evaluator under `SemanticMode.MODE_A`.

## Mode B — fixed-width bit-vectors

Locked decisions (2026-10-09):

- Width is configurable. Initial default is **32** bits.
- Arithmetic is modular fixed-width bit-vector wrap. The reference evaluator matches that contract; Z3 bit-vector sorts are reserved for Phase 2 verification.
- Values are interpreted as **unsigned** integers in the closed range `[0, 2^w - 1]`.
- Integer literals outside that range are **rejected** (fail closed). They are **not** reduced modulo `2^w`.
- Unary minus is **bit-vector negation** after a legal literal or subexpression has been converted into the width: `(-x) ≡ (2^w - x) mod 2^w` for `x` already in range (equivalently, modular wrap of mathematical negation).
- Signed interpretation is **not** used for Mode B in this contract. Signedness for later operators remains a future decision if those operators are added.

Also specified:

- The initial language has no per-variable widths and no casts. Until casts exist, one width applies to the whole expression, and mixed widths are unsupported.
- The specified solver encoding is a Z3 bit-vector sort of that width, not an integer sort (Phase 2).
- Bitwise operations and shifts are not in the initial grammar. When they are added later, they follow the bit-vector contract written at that time. They are rejected until then.
- Operations whose signedness or language-specific behavior is not specified precisely are rejected. They are not given a silent default.

Phase 1 status: implemented by the reference evaluator under `SemanticMode.MODE_B`.

## Integer and bit-vector separation

- Mode A and Mode B are selected explicitly. Nothing switches mode by guessing from the expression text.
- Unbounded integer arithmetic is not a stand-in for wrapping arithmetic.
- A Z3 integer encoding is not a stand-in for a bit-vector encoding, or the reverse.
- A rule validated in one mode is not thereby validated in the other.
- Display of a Mode B value must show the unsigned interpretation and the width. It must not present the vector as an unbounded integer.

## Initial grammar

The initial language is only:

- Integer literals.
- Named symbolic variables.
- Parenthesized expressions.
- Binary addition (`+`).
- Binary subtraction (`-`).
- Binary multiplication (`*`).
- Unary plus (`+`) and unary minus (`-`).

The following are later extensions. They are outside the initial grammar and must be rejected, not rewritten into something else: integer division and remainder, bitwise operations, left and right shifts, comparisons and Boolean expressions, and explicit fixed-width casts. Exponentiation is also absent and must be rejected.

Parsing uses Python's `ast` module and does not execute the input. `eval` and `exec` are forbidden. A name is a symbolic variable. It must not be looked up as a Python object.

Because that parser is Python's `ast` parser, precedence and associativity for the operators above are Python's rules for those operators:

- Unary plus and unary minus bind more tightly than multiplication.
- Multiplication binds more tightly than binary addition and subtraction.
- Binary `+`, `-`, and `*` are left-associative.
- Unary operators apply to the operand immediately following them, so repetition such as `--x` is repetition of the specified unary operations, not a new operator.
- Parentheses group. A trailing comma, as in `(x,)`, is a tuple, not a grouping, and is rejected.

Python has no negative integer token. The text `-1` is unary minus applied to the integer literal `1`. The same holds for `+1` and unary plus.

Each occurrence of a name in one expression denotes the same variable. There are no bindings in this grammar. Assignments are rejected. The variable's domain is the domain of the selected mode: all mathematical integers in Mode A; unsigned values in `[0, 2^w - 1]` in Mode B.

### Integer literals (locked)

Accepted spellings are those accepted by Python's `ast` for integer constants:

- Decimal
- Hexadecimal (`0x` / `0X`)
- Binary (`0b` / `0B`)
- Octal (`0o` / `0O`)
- Underscore separators

`True` and `False` are rejected. They are not integer literals under this grammar. Floats, complex numbers, strings, bytes, `None`, and other non-integer constants are not integer literals.

In Mode A, an accepted integer literal denotes that mathematical integer, subject to the configured Mode A integer-literal bit-length limit.

In Mode B, an accepted integer literal must lie in `[0, 2^w - 1]`. Out-of-range literals are rejected; they are not reduced modulo `2^w`.

## Fail-closed rules

Unsupported syntax fails closed. It is not repaired, not executed, and not translated into a different operation.

The parser rejects:

- Function calls.
- Attribute access.
- Imports.
- Comprehensions.
- Assignments.
- Arbitrary statements. The input is one expression, not a module and not a statement list.
- File access.
- Network operations.
- Reflection.
- Unapproved AST node types. The expression itself may contain only integer constants that are not Booleans, names, parentheses used as grouping, binary `+`, `-`, and `*`, and unary `+` and `-`.
- Expressions that exceed a configured complexity limit.

Examples of unapproved forms, all rejected: calls, attributes, subscripts, slices, comparisons, Boolean operations, conditional expressions, lambdas, lists, dicts, sets, tuples, f-strings, walrus assignment, starred expressions, `await`, and operators other than the initial `+`, `-`, and `*`.

### Resource limits (locked defaults)

All limits are configurable, documented, and enforced. Locked Phase 1 defaults:

| Limit | Default |
| --- | --- |
| Source length | 4096 characters |
| AST node count | 256 |
| Nesting depth | 32 |
| Mode A integer-literal bit length | 4096 |
| Solver timeout | 5 seconds (configuration only in Phase 1; solver is Phase 2) |

Also fail closed, from the result contract in section 6 (for later phases):

- Unsupported expression: no verification claim.
- Translation failure: verification was not performed.
- UNKNOWN, timeout, or interruption: equivalence is not established.
- A counterexample the reference evaluator cannot check is not a confirmed counterexample.

Solver UNSAT means equivalence inside the encoded model and the stated assumptions. It does not mean the parser, translator, optimizer, or application is correct.

## Specified verification reading

This reading is part of the contract for later phases. It is not a verifier. Phase 1 does not implement Z3 translation.

For an original expression `E_o` and a candidate `E_c`, the specified query is whether a valid input exists such that `E_o(x) != E_c(x)`, under the selected mode.

| Condition | Required state | Claim allowed |
| --- | --- | --- |
| Solver UNSAT | `EQUIVALENT_WITHIN_MODEL` | Equivalent within the encoded model and assumptions |
| Solver SAT, and the reference evaluator confirms differing outputs | `COUNTEREXAMPLE_FOUND` | A counterexample exists within the encoded model |
| Solver UNKNOWN | `UNKNOWN` | Equivalence undetermined |
| Timeout or interruption | `TIMEOUT` | Verification incomplete |
| Expression outside the grammar or the mode | `UNSUPPORTED` | No verification claim |
| Input rejected by syntax or limits | `INVALID_INPUT` | No verification claim |
| Translation could not be built | `TRANSLATION_ERROR` | Verification was not performed |
| Any other verifier failure | `VERIFICATION_ERROR` | No equivalence claim |

These states stay separate. They are not a Boolean.

## Phase 1 implementation mapping

| Contract element | Module |
| --- | --- |
| Semantic mode and width | `veriforge.config.SemanticConfiguration` |
| Resource limits | `veriforge.config.ResourceLimits` |
| Safe parse | `veriforge.parser_engine.parse_expression` |
| Mode helpers / literal checks | `veriforge.semantics` |
| Reference evaluation | `veriforge.reference_evaluator.evaluate` |
| Classified errors | `veriforge.exceptions` |
