# Semantics

This document is the specified contract for Phase 1. It is not implemented behavior. No parser, evaluator, or solver translation exists in this repository. Where the specification leaves a choice that would change meaning, this file records the gap and does not fill it.

Source of the contract: sections 3, 5, and 6 of the controlling specification. No operators are added beyond that text.

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
- The specified solver encoding is a Z3 integer sort, not a bit-vector sort.

Not implemented.

## Mode B — fixed-width bit-vectors

Specified meaning:

- Values are fixed-width bit-vectors.
- The width is configurable. The initial width is 32 bits.
- The initial language has no per-variable widths and no casts. Casts are a later extension. Until they exist, one width applies to the whole expression, and mixed widths are unsupported.
- The specified solver encoding is a Z3 bit-vector sort of that width, not an integer sort.
- Wrapping arithmetic and conversion into the bit-vector width must be defined explicitly before any Mode B evaluation is implemented.
- Bitwise operations and shifts are not in the initial grammar. When they are added later, they follow the bit-vector contract written at that time. They are rejected until then.
- Operations whose signedness or language-specific behavior is not specified precisely are rejected. They are not given a silent default.

Unresolved, and intentionally not decided in this document:

- Whether bit-vectors are interpreted as signed, unsigned, or only as bit patterns with no integer reading.
- How an integer literal is converted into a vector of the configured width, including literals that do not fit in that width and literals that appear under unary minus.

Those choices change which values exist and which expressions are legal. Phase 1 must not encode Mode B literal conversion or a signed reading until they are decided. Modular bit-vector addition, subtraction, and multiplication do not answer the signedness or literal-range questions.

Not implemented.

## Integer and bit-vector separation

- Mode A and Mode B are selected explicitly. Nothing switches mode by guessing from the expression text.
- Unbounded integer arithmetic is not a stand-in for wrapping arithmetic.
- A Z3 integer encoding is not a stand-in for a bit-vector encoding, or the reverse.
- A rule validated in one mode is not thereby validated in the other.
- Display of a Mode B value, once an interpretation exists, must show that interpretation and the width. It must not present the vector as an unbounded integer.

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

Parsing, when it is implemented, must use Python's `ast` module and must not execute the input. `eval` and `exec` are forbidden. A name is a symbolic variable. It must not be looked up as a Python object.

Because that parser is Python's `ast` parser, precedence and associativity for the operators above are Python's rules for those operators:

- Unary plus and unary minus bind more tightly than multiplication.
- Multiplication binds more tightly than binary addition and subtraction.
- Binary `+`, `-`, and `*` are left-associative.
- Unary operators apply to the operand immediately following them, so repetition such as `--x` is repetition of the specified unary operations, not a new operator.
- Parentheses group. A trailing comma, as in `(x,)`, is a tuple, not a grouping, and is rejected.

This precedence is a consequence of the required parser. It is not a second grammar and it is not implemented here.

Python has no negative integer token. The text `-1` is unary minus applied to the integer literal `1`. The same holds for `+1` and unary plus.

Each occurrence of a name in one expression denotes the same variable. There are no bindings in this grammar. Assignments are rejected. The variable's domain is the domain of the selected mode: all mathematical integers in Mode A; the configured bit-vector width in Mode B, once conversion and interpretation are defined.

Boolean constants are not integer literals. In Python, `bool` is a subclass of `int`, so an implementation that accepts every constant whose Python type is `int` would accept `True` and `False`. The contract forbids that. Floats, complex numbers, strings, bytes, `None`, and other non-integer constants are not integer literals.

Which non-decimal spellings count as integer literals is unresolved. Python's parser accepts decimal, binary (`0b`), octal (`0o`), hexadecimal (`0x`), and underscore spellings as integer constants. The specification says "integer literals" and does not list spellings. This contract does not choose a subset.

In Mode A, an accepted integer literal denotes that mathematical integer, subject to the configured literal-size limit. The numeric value of that limit is not specified yet. In Mode B, the denotation of a literal is the unresolved conversion rule above.

## Fail-closed rules

Unsupported syntax fails closed. It is not repaired, not executed, and not translated into a different operation.

When parsing exists, it must reject:

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

Limits required by the specification, all configurable, documented, and enforced once an implementation exists:

- Source length.
- AST node count.
- Nesting depth.
- Integer-literal size.
- Solver runtime.
- Other relevant resource consumption.

No numeric default is set in this phase. Until a limit is configured and enforced, an implementation must not claim that resource bounds exist.

Also fail closed, from the result contract in section 6:

- Unsupported expression: no verification claim.
- Translation failure: verification was not performed.
- UNKNOWN, timeout, or interruption: equivalence is not established.
- A counterexample the reference evaluator cannot check is not a confirmed counterexample.

Solver UNSAT means equivalence inside the encoded model and the stated assumptions. It does not mean the parser, translator, optimizer, or application is correct.

## Specified verification reading

This reading is part of the contract for later phases. It is not a verifier.

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

## Not a description of this repository

No expression can be parsed, evaluated, optimized, or verified by the code in this repository, because that code does not exist. Examples in this file illustrate the specified contract only.
