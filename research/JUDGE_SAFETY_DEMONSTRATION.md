# Judge safety demonstration

Command, executed on this host:

```bash
python3 scripts/judge_safety_demo.py
```

The transcript below is the process output saved in `research/judge_safety_demo_output.txt`. It is not a handwritten solver log.

## Correct rewrite

`(x + 0)` versus `x` in Mode A. Status `equivalent_within_model`. Establishing method `polynomial`. Z3 was not used.

## Incorrect rewrite

`(x + 1)` versus `(x + 2)` in Mode B, width 8. Status `counterexample_found`. Witness `{x: 0}`. The exhaustive gate evaluated the finite domain and stopped at the first difference.

## Malformed input

Source `01`. Status `unsupported`. Both the independent parser and the production parser reject a decimal literal with a leading zero.

## Unresolved case

`(x * (y + z))` versus `((x * y) + (x * z))` at width 8 with exhaustive budget 16. Domain `2^(8*3) = 16777216`. Status `unknown`. The exhaustive gate is `not_computed`. It is not labeled equivalent and it is not labeled exhaustive.

## Timeout

A live Z3 timeout was not produced, because `z3` is not installed. The status contract was executed on a timeout gate and returned `timeout`, `labeled_equivalent=False`. That is a contract test, not a solver run.

## Transcript

```
== correct rewrite x + 0 versus x, Mode A
status=equivalent_within_model
establishing_method=polynomial
reason=every completed check established equivalence within its model
  gate polynomial: equivalent (expanded polynomials are identical)

== incorrect rewrite x + 1 versus x + 2, Mode B width 8
status=counterexample_found
establishing_method=exhaustive
reason=a completed check found a differentiating assignment
witness={'x': 0}
  gate exhaustive: counterexample (outputs differ on a fully enumerated assignment)

== malformed decimal literal 01, Mode A
status=unsupported
establishing_method=none
reason=unsupported syntax
  gate independent_parse_original: unsupported (leading zeros in decimal integer literals are not permitted)
  gate production_parse_original: unsupported (syntax error: leading zeros in decimal integer literals are not permitted; use an 0o prefix for octal integers)

== domain over exhaustive budget, Mode B width 8, three variables, budget 16
status=unknown
establishing_method=none
reason=no establishing check completed; result is unresolved
  gate exhaustive: not_computed (domain 2^(8*3)=16777216 exceeds assignment budget 16)

== status-contract timeout fixture (not a live Z3 timeout)
status=timeout
establishing_method=none
reason=solver timeout; not an equivalence result
labeled_equivalent=False
```
