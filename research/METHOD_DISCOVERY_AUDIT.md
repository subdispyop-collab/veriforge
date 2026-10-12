# Method-discovery audit

Audit time: `2026-10-12T13:11:06Z`. Starting commit: `8ad58149d1ee1fcf7248cbf4d9e7618e66daec14` on `cursor/research-hardening-7f34`. This work is on `cursor/method-discovery-7f34`. Software version remains `1.0.0`. `datasets/held_out/cases.jsonl` has 8 lines and was not rewritten.

## Environment actually observed

Commands run for this audit:

```text
git rev-parse HEAD
python3 --version
PYTHONPATH=/home/ubuntu/py-z3:/workspace Z3_LIBRARY_PATH=/home/ubuntu/al-root/usr/lib64 LD_LIBRARY_PATH=/home/ubuntu/al-root/usr/lib64 python3 -c "import z3; print(z3.get_version_string())"
/home/ubuntu/solvers/usr/lib64/ld-linux-x86-64.so.2 --library-path /home/ubuntu/solvers/usr/lib/x86_64-linux-gnu:/home/ubuntu/solvers/lib/x86_64-linux-gnu:/home/ubuntu/solvers/usr/lib64 /home/ubuntu/solvers/usr/bin/cvc5 --version
```

Python 3.12.3. Z3 4.8.17. cvc5 version line `This is cvc5 version 1.3.2`. Alive2 is not installed. mutmut is not installed. The pins `z3-solver==5.1.0.0` and `hypothesis==6.168.5` are not installed. The suite that was run earlier used pytest 9.1.1 and Debian Hypothesis 6.155.7. That suite was not rerun for this audit.

## What the implementation does

The production language is literals, names, parentheses, binary `+` `-` `*`, and unary `+` `-`. Mode A is unbounded integer arithmetic. Mode B is unsigned wrap modulo `2^w`. Literals outside `[0, 2^w-1]` are rejected in Mode B.

`veriforge/polynomial_oracle.py` expands both sides to a map from monomials to integer coefficients, within a term budget of 4096. Identical expansions are equivalent over the integers. A differing expansion yields a witness. The file states that equal polynomials imply equal wraparound functions, but unequal polynomials may still agree modulo `2^w`. Budget overflow is `not_computed`, not equivalence. This procedure does not call Z3.

`veriforge/exhaustive_oracle.py` enumerates the Mode B domain `2^(w*k)` only when that size is at most 65536. Otherwise the label is `not_computed`. A sample is not called exhaustive.

`veriforge/verifier_engine.py` `verify_equivalence_timed` translates both sides with `translate_to_z3` and calls `solver.check()` on their inequality. Mode A is integer arithmetic. Mode B is unsigned bit-vectors. `COUNTEREXAMPLE_FOUND` is kept only after `reference_evaluator.evaluate` confirms the model. Timeout and unknown stay non-equivalent.

`veriforge/independent_encoder.py` builds a second Z3 encoding and does not call `translate_to_z3`. The two encodings share Z3. `veriforge/assurance.py` combines polynomial or exhaustive evidence with that encoder and the production SMT path. An uncertain solver status is not promoted to equivalence.

The second-solver script encodes the same semantics for the cvc5 and Bitwuzla command-line binaries. On the 463-pair census, cvc5 1.3.2 matched Z3 4.8.17. Bitwuzla 0.8.2 rejected `QF_NIA`. Those counts are historical measurements, not a new experiment.

## Historical results versus confirmatory results

Exploratory for 1.0.0: the n=8 file `experiments/reports/phase10-held-out-evaluation.md`. The published 4/4 is two unique non-equivalent cases, each under two SMT baselines. Software was 0.10.0.

Confirmatory for the testing baseline, not for a new algorithm: dataset 1.1.0, 463 pairs, protocol hash `3e2f3c81d58e70bc789c8470f82865bd8bbcf8027a96ec7ffdc6c4081a60aa13`. H_test was not supported: 0/54 false equivalences at budgets 10 and 10,000.

Confirmatory for false equivalence of the existing solvers, not for a new method: protocol `veriforge-confirmatory-v2`, hash `1d991b3c444f3a93b531196b4da4a9794937d697212b4e45d285cf8f0f6c498b`. Z3 and cvc5 false equivalence 0/33, Mode A 0/12, Mode B 0/21. H3 stayed unresolved because the Spearman interval contained 0 and the uniform equivalent class had one family.

## Claims that are not supported

No new decision procedure. No speedup over Z3 or cvc5. No population false-equivalence rate. No Alive2 score. No IRIS score. Solver agreement with the project's own polynomial or exhaustive labels is not an external proof. The 463-pair Z3/cvc5 census was not rerun here.

## Incomplete work already on the branch

mutmut never ran. `z3-solver==5.1.0.0` and `hypothesis==6.168.5` were not fetched. Aliyun, Tsinghua, GitLab, PyPI, and GitHub TLS failed as recorded in `research/PART15_AUDIT.md`. The offline Podman image build and run exited 0. GitHub Actions was not executed.

## Research question this audit starts from

On expressions built from `+`, `-`, `*`, and unary `+`/`-`, under either unbounded integers or unsigned wrap, can a procedure that does not call Z3, does not call cvc5, and does not use the existing polynomial expansion as its decision establish a measured advantage over those baselines? The later gate answers that no such candidate is defensible as a new method.
