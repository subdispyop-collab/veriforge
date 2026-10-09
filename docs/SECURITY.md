# Security and resilience

Phase 9 documents the threat model, enforced controls, dependency review, and
remaining limitations for VERIFORGE. **This document does not claim resistance
to every attack.**

Controlling requirements: master specification §15 and Phase 9.

## Threat model

### Assets

- Integrity of parse → optimize → verify results (no silent wrong acceptance).
- Confidentiality of secrets that must never enter audit/export artifacts.
- Availability of the local research workflow (bounded resource use).
- Integrity of filesystem stores under `experiments/` and `datasets/`.

### Trust boundary

| Zone | Trust |
| --- | --- |
| Local operator / researcher | Trusted to run the process and supply expressions |
| Expression / dataset text | **Untrusted** |
| Imported JSON/CSV audit payloads | **Untrusted** until validated |
| Pinned Python packages (`z3-solver`, Streamlit stack, pytest, hypothesis) | Trusted as installed artifacts; still part of the TCB |
| Operating system, Python runtime, Z3 native library | Outside VERIFORGE’s control (TCB) |

### In-scope adversary goals (research prototype)

1. Cause arbitrary code execution via expression or dataset input.
2. Bypass AST allowlisting / smuggle unsupported constructs.
3. Exhaust resources (huge source, deep nesting, huge literals, unbounded solver).
4. Write audit/export files outside controlled directories (path traversal).
5. Persist or display secrets (tokens, passwords, key material) via errors or exports.
6. Trick the UI into labeling UNKNOWN/TIMEOUT as equivalence (honesty, not classic RCE).

### Out of scope for this prototype

- Multi-tenant remote hosting, authentication, authorization, and network attack surface beyond local Streamlit bind.
- Supply-chain compromise of already-installed OS packages outside the pinned lock.
- Side-channel, speculative-execution, or Z3 implementation vulnerabilities.
- Guaranteeing availability under deliberate OS-level resource exhaustion (OOM killer, disk full).
- Resistance to a malicious local user with write access to the repository or Python environment.

## Controls enforced (§15)

| Control | Mechanism | Primary location |
| --- | --- | --- |
| Strict AST validation | Allowlist of node types; fail closed | `veriforge/parser_engine.py` |
| No arbitrary code execution | No `eval`/`exec` on user input; IR evaluation only | parser, `reference_evaluator`, optimizer, fuzzer |
| Input-size restrictions | Configurable `max_source_length` (default 4096) | `ResourceLimits` |
| Resource limits | AST node count, nesting depth, Mode A literal bit length | `ResourceLimits` + parser |
| Solver timeouts | Configurable `solver_timeout_seconds` (default 5s) on every check | `verifier_engine` |
| Safe / controlled file handling | Exports confined under `experiments/exports/`; derived summaries under `experiments/reports/` with safe names | `veriforge/security.py`, `audit_engine`, `repositories` |
| Robust exception handling | Classified `VeriforgeError` hierarchy; unexpected errors mapped to `[unexpected]` | `exceptions.py`, `security.user_facing_error` |
| Clear errors without secret leakage | `sanitize_error_text` / `user_facing_error`; audit `redact_secrets` | `security.py`, `audit_engine.py` |
| Unsupported syntax | Rejected; never silently rewritten | parser |
| Dependency awareness | Locked pins recorded; review snapshot in `dependency_review_snapshot()` | `requirements.lock`, this doc |

UI actions (`veriforge/ui/actions.py`) surface `user_facing_error` for classified and unexpected failures so Streamlit pages do not print raw tracebacks or secret-shaped substrings.

## Dependency review (locked versions)

Pins selected for this line (from `pyproject.toml` / `requirements.lock`):

| Package | Locked version | Notes |
| --- | --- | --- |
| z3-solver | 5.1.0.0 | Native SMT solver; TCB for equivalence claims |
| streamlit | 1.41.1 | Local UI; bind to loopback by default in `scripts/run_ui.py` |
| plotly | 5.24.1 | Charts only from completed-run data |
| pandas | 2.2.3 | Tabular display helpers |
| pytest | 9.1.1 | Dev |
| hypothesis | 6.168.5 | Dev property tests |

**Install verification:** on hosts where HTTPS to `pypi.org` / `files.pythonhosted.org` is blocked (`SSLEOFError` / `UNEXPECTED_EOF_WHILE_READING`), a clean reinstall cannot be performed. The review above is based on the **locked versions actually selected in-tree**, not on a fresh `pip install` attestation on every agent VM. When egress is available, reinstall with `python3 -m pip install -e ".[dev]"` and re-run `python3 -m pytest`.

Transitive Streamlit/plotly/pandas pins may be incomplete in `requirements.lock` when egress blocked lock refresh (noted since Phase 8). That is a packaging gap, not a claim that those packages are free of vulnerabilities.

No automated CVE scanner was run in Phase 9. Vulnerability awareness here means: pins are explicit, surface is documented, and upgrades require a deliberate lock change.

## Remaining security limitations

- Local Streamlit is not a hardened multi-user service. Do not expose it to untrusted networks without additional controls outside this repository.
- Resource limits bound parser/solver configuration; they do not prove immunity to all denial-of-service strategies (e.g. pathological Z3 instances that finish just under timeout repeatedly).
- Secret redaction is pattern-based (keys and common value shapes). It can miss novel secret formats.
- Path confinement applies to VERIFORGE export/derived helpers; callers that bypass those APIs can still write arbitrary paths.
- The trusted computing base includes CPython, Z3, and pinned third-party wheels. Bugs there are outside VERIFORGE’s proof obligation.
- Passing adversarial tests is evidence of the controls exercised, not a certificate of total security.

See also `docs/LIMITATIONS.md` for scientific and semantic limits.

## Related tests

- `tests/unit/test_security.py`
- `tests/adversarial/test_security_resilience.py`
- `tests/unit/test_parser.py` (rejection + limits)
- `tests/unit/test_no_eval_exec.py`
- `tests/unit/test_audit_engine.py` (redaction + export)
