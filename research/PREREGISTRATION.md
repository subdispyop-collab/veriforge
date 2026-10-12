# Preregistration for the method-discovery gate

- Record id: `veriforge-method-discovery-nogo-v1`
- Software version: `1.0.0` (not bumped)
- Base commit inspected before this file: `8ad58149d1ee1fcf7248cbf4d9e7618e66daec14`
- Gate result locked by this file: **NO-GO**
- New confirmatory dataset: none. This file is the reason none is generated.

This file is hashed before any new expression pair is created and before any solver is run for a new method. There is no new method.

## Primary hypothesis

H_new: A procedure that does not call Z3, does not call cvc5, and does not use integer polynomial expansion as its decision has a lower false-equivalence count than `verify_equivalence_timed` on a frozen family-clustered set of `+` `-` `*` expressions, in a named mode, at the same 5 second budget.

Status locked here: **not tested**. The gate found no procedure that is distinct from prior work and allowed to return `EQUIVALENT`. Running H_new would measure an implementation of a known method, or an unsound test, and would be reported as novelty. That run is not authorized.

## Secondary hypotheses

None are authorized. In particular, this file does not reopen H3, H_test, or the 463-pair census.

## Units

If a later amendment authorizes an experiment, the independent unit remains the rewrite family. Pairs inside a family are repeats. This file does not create families.

## Inclusion and exclusion

No pairs are included. `datasets/held_out/cases.jsonl`, `datasets/assurance_v1/cases.jsonl`, and `datasets/confirmatory_v2/cases.jsonl` are not inputs to a new method. They are not rewritten.

## Sample size

Target for a new method: not applicable. Sample size is not chosen after seeing a rate, because there is no rate.

## Ground truth

Not collected. Exhaustive labels and polynomial labels remain the existing oracles for the old datasets only.

## Baselines

Z3 4.8.17 and cvc5 1.3.2 are available and are not rerun. The polynomial checker is not used as a new method. Alive2 is not comparable and is not installed. No baseline table is filled with new numbers.

## Analysis plan

There are no new rows. The script `scripts/method_discovery_analysis.py` must refuse to invent a rate. It prints the gate and stops. A Wilson interval is not computed on an empty denominator.

## Stopping rule

Stop at the gate. Do not add a candidate after this hash. Do not generate pairs because the gate was NO-GO. Do not retune a threshold. An amendment would be a new file with a new hash, written before any pairs exist.

## What would have counted as support

Support would have required a candidate that passed `research/CANDIDATE_METHODS.md` and then a preregistered confirmatory run showing the primary comparison in the stated direction, with no confirmed false equivalence. That conjunction did not occur. The hypothesis remains not tested, not supported, and not rejected by a measurement.
