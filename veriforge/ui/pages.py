"""Six Streamlit pages required by specification §14 (Phase 8)."""

from __future__ import annotations

from pathlib import Path

from veriforge.fuzzer_suite import DEFAULT_MUTATION_SEED, mutation_categories
from veriforge.models import (
    BaselineId,
    CandidateDecision,
    ExportFormat,
    VerificationStatus,
)
from veriforge.ui.catalog import PAGE_NAMES
from veriforge.ui.actions import (
    audit_export,
    audit_history,
    audit_integrity,
    audit_replay,
    build_semantic_configuration,
    list_baseline_options,
    list_development_case_ids,
    load_research_metrics,
    measurements_to_json_rows,
    parse_for_workbench,
    persist_optimization_result,
    run_benchmark_lab,
    run_fuzz_lab,
    run_verification_explorer,
    run_workbench,
)
from veriforge.ui.components import (
    page_intro,
    render_semantic_banner,
    render_unavailable,
    render_verification_status,
    semantic_mode_selector,
)
from veriforge.ui.presentation import (
    counterexample_display_rows,
    feature_availability,
    format_verification_status,
    mutation_outcome_label,
    research_dashboard_state,
)
from veriforge.ui.visualizations import (
    render_benchmark_report_charts,
    render_metric_category_chart,
    render_timing_distribution,
)
from veriforge.version import __version__


def _st():
    import streamlit as st

    return st


def render_expression_workbench() -> None:
    st = _st()
    page_intro(
        "Expression Workbench",
        "Parse a supported arithmetic expression, apply the verification-guided "
        "optimizer, and inspect the transformation trace. Application logic "
        "runs in the engine modules; this page only presents results.",
    )
    mode, bit_width, timeout = semantic_mode_selector(key_prefix="wb")
    config = build_semantic_configuration(
        mode=mode, bit_width=bit_width, solver_timeout_seconds=timeout
    )
    render_semantic_banner(config)

    source = st.text_area(
        "Original expression",
        value="(x + 0) * 1",
        height=80,
        key="wb_source",
    )
    col_a, col_b = st.columns(2)
    validate_only = col_a.button("Validate parse", key="wb_parse")
    run_opt = col_b.button("Optimize (verification-guided)", key="wb_opt")

    if validate_only:
        outcome = parse_for_workbench(source, config)
        if outcome.ok:
            st.success("Parse accepted under the documented grammar.")
            st.code(outcome.rendered or "", language="text")
            st.write("Variables:", ", ".join(outcome.variables) or "(none)")
        else:
            st.error(outcome.error)

    if run_opt:
        result = run_workbench(source, config)
        if result.error:
            st.error(result.error)
            return
        assert result.optimization is not None
        opt = result.optimization
        st.subheader("Original representation")
        st.code(opt.original.source, language="text")
        st.subheader("Candidate / accepted expression")
        st.code(opt.accepted.source, language="text")
        st.caption(f"Correctness policy: `{opt.policy.value}`")

        st.subheader("Optimization trace")
        if not opt.trace:
            st.info("No applicable rewrite rules produced candidates.")
        for step in opt.trace:
            with st.expander(
                f"Step {step.step_index}: {step.rule_id} → {step.decision.value}",
                expanded=step.decision is CandidateDecision.ACCEPTED,
            ):
                st.markdown(f"**Rule:** {step.rule_name}")
                st.markdown(f"**Formal:** {step.formal_description}")
                st.markdown(
                    "**Preconditions:** "
                    + (", ".join(step.preconditions) or "(none)")
                )
                st.code(f"{step.before_source}  ⇒  {step.after_source}")
                if step.verification_result is not None:
                    render_verification_status(step.verification_result.status)
                if step.rejection_reason:
                    st.warning(step.rejection_reason)

        if st.checkbox("Persist optimization run to audit store", key="wb_persist"):
            record = persist_optimization_result(opt)
            st.success(
                f"Recorded run `{record.run_id}` "
                f"(fingerprint `{record.configuration_fingerprint[:12]}…`)"
            )


def render_verification_explorer() -> None:
    st = _st()
    page_intro(
        "Verification Explorer",
        "Compare an original expression to a candidate under the selected "
        "semantic model. UNKNOWN and timeout are never labeled equivalent.",
    )
    mode, bit_width, timeout = semantic_mode_selector(key_prefix="vx")
    config = build_semantic_configuration(
        mode=mode, bit_width=bit_width, solver_timeout_seconds=timeout
    )
    render_semantic_banner(config)

    original = st.text_input("Original expression", value="x + 1", key="vx_orig")
    candidate = st.text_input("Candidate expression", value="x + 2", key="vx_cand")
    if st.button("Verify equivalence", key="vx_run"):
        outcome = run_verification_explorer(original, candidate, config)
        if outcome.error:
            st.error(outcome.error)
            return
        assert outcome.timed is not None
        timed = outcome.timed
        result = timed.result
        st.subheader("Formal result status")
        render_verification_status(result.status)
        st.markdown(f"**Solver status string:** `{result.solver_status}`")
        if result.reason:
            st.markdown(f"**Detail:** {result.reason}")

        st.subheader("Solver timing (separate from expression execution)")
        st.write(
            {
                "parsing_seconds": timed.parsing_seconds,
                "translation_seconds": timed.translation_seconds,
                "solver_seconds": timed.solver_seconds,
                "end_to_end_seconds": timed.end_to_end_seconds,
            }
        )

        st.subheader("Counterexample")
        rows = counterexample_display_rows(result)
        if rows is None:
            st.info("No counterexample recorded for this outcome.")
        else:
            for row in rows:
                confirmed = row["confirmed"]
                if confirmed:
                    st.error("Confirmed counterexample (reference evaluator agrees).")
                else:
                    st.warning(
                        "Counterexample recorded but not confirmed "
                        f"(validation_status={row['validation_status']})."
                    )
                st.json(row)

        st.subheader("Limitations and assumptions")
        st.markdown(
            "- Equivalence means UNSAT for `exists x: E_o(x) != E_c(x)` "
            "under the encoded model.\n"
            "- A solver result does not prove the application stack correct.\n"
            f"- Active label when equivalent: "
            f"`{format_verification_status(VerificationStatus.EQUIVALENT_WITHIN_MODEL)}`\n"
            f"- UNKNOWN label: `{format_verification_status(VerificationStatus.UNKNOWN)}`\n"
            f"- Timeout label: `{format_verification_status(VerificationStatus.TIMEOUT)}`"
        )


def render_fuzzing_mutation_lab() -> None:
    st = _st()
    page_intro(
        "Fuzzing and Mutation Lab",
        "Generate **synthetic artificial mutations** and measure whether the "
        "verification pipeline detects them. These are not real-world defects.",
    )
    mode, bit_width, timeout = semantic_mode_selector(key_prefix="fz")
    config = build_semantic_configuration(
        mode=mode, bit_width=bit_width, solver_timeout_seconds=timeout
    )
    render_semantic_banner(config)

    source = st.text_input(
        "Seed expression",
        value="(x + 0) * (y - 0)",
        key="fz_source",
    )
    seed = int(
        st.number_input(
            "Reproducible seed",
            value=DEFAULT_MUTATION_SEED,
            step=1,
            key="fz_seed",
        )
    )
    max_mut = int(
        st.number_input(
            "Maximum mutations (run size)",
            min_value=1,
            max_value=200,
            value=16,
            key="fz_max",
        )
    )
    all_cats = [c.value for c in mutation_categories()]
    selected = st.multiselect(
        "Supported mutation categories",
        options=all_cats,
        default=all_cats,
        key="fz_cats",
    )
    st.info(
        "Synthetic mutations are isolated from production optimizer rules. "
        "They never bypass the verification gate and are never accepted into "
        "the production path (`accepted_into_production` is always False)."
    )

    if st.button("Run mutation campaign", key="fz_run"):
        progress = st.progress(0, text="Starting…")
        outcome = run_fuzz_lab(
            source,
            config,
            seed=seed,
            max_mutations=max_mut,
            category_values=selected,
        )
        progress.progress(100, text="Complete")
        if outcome.error:
            st.error(outcome.error)
            return
        st.subheader("Outcomes")
        detected = 0
        failed_rows = []
        export_rows = []
        for index, analysis in enumerate(outcome.analyses, start=1):
            status = analysis.verification_result.status
            label = mutation_outcome_label(
                detected_as_non_equivalent=analysis.detected_as_non_equivalent,
                status=status,
                artificial=analysis.mutation.artificial,
            )
            if analysis.detected_as_non_equivalent:
                detected += 1
            else:
                failed_rows.append(
                    {
                        "mutation_id": analysis.mutation.mutation_id,
                        "category": analysis.mutation.category.value,
                        "status": status.value,
                        "label": label,
                    }
                )
            export_rows.append(
                {
                    "mutation_id": analysis.mutation.mutation_id,
                    "category": analysis.mutation.category.value,
                    "generation_method": analysis.mutation.generation_method,
                    "seed": analysis.mutation.seed,
                    "original_source": analysis.mutation.original_source,
                    "mutated_source": analysis.mutation.mutated_source,
                    "artificial": analysis.mutation.artificial,
                    "verification_status": status.value,
                    "detected_as_non_equivalent": analysis.detected_as_non_equivalent,
                    "accepted_into_production": analysis.accepted_into_production,
                    "label": label,
                }
            )
            st.markdown(f"{index}. `{analysis.mutation.mutation_id}` — {label}")
        total = len(outcome.analyses)
        st.metric("Mutations analyzed", total)
        st.metric("Detected as non-equivalent", detected)
        if failed_rows:
            st.subheader("Failed / undetected cases")
            st.dataframe(failed_rows, use_container_width=True)
        st.download_button(
            "Export regression-case JSON",
            data=__import__("json").dumps(export_rows, indent=2, sort_keys=True),
            file_name="veriforge-mutation-regression.json",
            mime="application/json",
            key="fz_export",
        )


def render_benchmark_lab() -> None:
    st = _st()
    page_intro(
        "Benchmark Lab",
        "Configure and run **development-partition** engine validation. "
        "Results are not research conclusions. Solver latency and expression "
        "execution time remain separate.",
    )
    baselines = list_baseline_options()
    baseline_labels = {
        f"{row['name']} [{row['status']}]": row["id"] for row in baselines
    }
    chosen_label = st.selectbox(
        "Baseline selection",
        options=list(baseline_labels.keys()),
        index=2 if len(baseline_labels) > 2 else 0,
        key="bm_baseline",
    )
    baseline_id = BaselineId(baseline_labels[chosen_label])
    st.caption(
        next(r["description"] for r in baselines if r["id"] == baseline_id.value)
    )

    try:
        case_ids = list(list_development_case_ids())
    except Exception as exc:  # noqa: BLE001 — surface as unavailable
        render_unavailable(
            feature_availability(
                "benchmark_dataset_selection",
                available=False,
                reason_if_unavailable=f"Development dataset unavailable: {exc}",
            )
        )
        return

    selected_cases = st.multiselect(
        "Dataset selection (development partition)",
        options=case_ids,
        default=case_ids[: min(3, len(case_ids))],
        key="bm_cases",
    )
    trials = int(
        st.number_input("Trials per case", min_value=1, max_value=50, value=2, key="bm_trials")
    )
    warmups = int(
        st.number_input("Warmup trials", min_value=0, max_value=20, value=1, key="bm_warm")
    )
    seed = int(
        st.number_input("Random seed", value=20261009, step=1, key="bm_seed")
    )
    timeout = float(
        st.number_input(
            "Solver timeout (seconds)",
            min_value=0.1,
            max_value=60.0,
            value=5.0,
            key="bm_timeout",
        )
    )

    if st.button("Run benchmark", key="bm_run"):
        outcome = run_benchmark_lab(
            case_ids=selected_cases,
            trials_per_case=trials,
            warmup_trials=warmups,
            random_seed=seed,
            solver_timeout_seconds=timeout,
            baseline_id=baseline_id,
            save_config_dir=Path("experiments/configurations"),
        )
        if outcome.error:
            st.error(outcome.error)
            return
        assert outcome.report is not None
        report = outcome.report
        st.success(
            f"Run `{outcome.run_id}` complete — "
            f"**not** a research conclusion "
            f"(is_research_conclusion={report.is_research_conclusion})."
        )
        st.subheader("Timeout / UNKNOWN / completion rates")
        rates = report.rates
        st.write(
            {
                "sample_count": rates.sample_count,
                "timeout_rate": rates.timeout_rate,
                "unknown_rate": rates.unknown_rate,
                "completion_rate": rates.completion_rate,
                "rejection_rate": rates.rejection_rate,
                "counterexample_rate": rates.counterexample_rate,
            }
        )
        render_benchmark_report_charts(report)
        solver_vals = [
            m.solver_seconds
            for m in outcome.measurements
            if not m.is_warmup and m.solver_seconds is not None
        ]
        render_timing_distribution(
            solver_vals,
            title="Solver seconds (non-warmup trials)",
            feature_id="benchmark_solver_distribution",
        )
        st.download_button(
            "Export raw measurements (JSON)",
            data=measurements_to_json_rows(outcome.measurements),
            file_name=f"veriforge-benchmark-{outcome.run_id}.json",
            mime="application/json",
            key="bm_export",
        )
        if outcome.config_path:
            st.markdown(
                f"**Saved configuration for reproduction:** `{outcome.config_path}`"
            )
            st.code(
                "python3 scripts/run_benchmarks.py --help\n"
                "# or reload the saved configuration via "
                "rerun_benchmark_from_saved_configuration(...)",
                language="bash",
            )


def render_research_dashboard() -> None:
    st = _st()
    page_intro(
        "Research Dashboard",
        "Displays **only** measurements from completed runs. Charts are never "
        "populated with fabricated data.",
    )
    run_ids, metrics, dataset_versions = load_research_metrics()
    state = research_dashboard_state(
        completed_run_ids=run_ids,
        metrics=metrics,
        dataset_versions=dataset_versions,
    )
    st.markdown("**Uncertainty and limitations**")
    for line in state.limitations:
        st.markdown(f"- {line}")

    if not state.has_completed_runs:
        render_unavailable(
            feature_availability(
                "research_dashboard_measurements",
                available=False,
                reason_if_unavailable=state.unavailable_reason
                or "No completed runs.",
            )
        )
        st.caption(f"VERIFORGE version `{__version__}`")
        return

    st.metric("Evaluation sample size (observations)", state.sample_size)
    st.markdown("**Run identifiers**")
    st.code("\n".join(state.run_ids) or "(none)")
    st.markdown("**Dataset versions**")
    st.write(list(state.dataset_versions) or ["(not recorded on loaded runs)"])

    assert state.metrics is not None
    overall = state.metrics.overall
    st.subheader("Correctness and error-detection metrics (from stored observations)")
    st.write(
        {
            "sample_count": overall.sample_count,
            "detected_count": overall.detected_count,
            "undetected_count": overall.undetected_count,
            "detection_rate": overall.detection_rate,
            "timeout_rate": overall.timeout_rate,
            "unknown_rate": overall.unknown_rate,
            "equivalent_count": overall.equivalent_count,
            "counterexample_count": overall.counterexample_count,
        }
    )
    st.subheader("Results by category")
    render_metric_category_chart(state.metrics)
    st.subheader("Verification overhead / execution performance")
    render_unavailable(
        feature_availability(
            "research_overhead_comparison",
            available=False,
            reason_if_unavailable=(
                "Cross-baseline overhead and execution-performance comparisons "
                "require completed Phase 10 held-out evaluation runs. Those "
                "measurements are not present; no chart is fabricated."
            ),
        )
    )


def render_audit_reproducibility() -> None:
    st = _st()
    page_intro(
        "Audit and Reproducibility",
        "Inspect run history, configuration fingerprints, software versions, "
        "exports, replay, and integrity checks.",
    )
    st.caption(f"Software version: `{__version__}`")

    if st.button("Refresh run history", key="au_hist"):
        st.session_state["au_history"] = list(audit_history())
    history = st.session_state.get("au_history")
    if history is None:
        history = list(audit_history())
        st.session_state["au_history"] = history
    st.subheader("Run history")
    if not history:
        st.info("No optimization or experiment runs recorded yet.")
    else:
        st.dataframe(history, use_container_width=True)

    st.subheader("Export")
    fmt = st.selectbox("Export format", options=["json", "csv"], key="au_fmt")
    run_filter = st.text_input(
        "Optional run_id filter (comma-separated)",
        value="",
        key="au_runs",
    )
    if st.button("Export audit records", key="au_export"):
        run_ids = (
            [part.strip() for part in run_filter.split(",") if part.strip()]
            or None
        )
        result = audit_export(
            format=ExportFormat.JSON if fmt == "json" else ExportFormat.CSV,
            run_ids=run_ids,
        )
        st.success(
            f"Export `{result['export_id']}` → `{result['filesystem_path']}` "
            f"({result['record_count']} records)"
        )

    st.subheader("Experiment replay")
    replay_id = st.text_input("Optimization run_id to replay", key="au_replay_id")
    if st.button("Replay optimization", key="au_replay"):
        try:
            result = audit_replay(replay_id.strip())
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
        else:
            st.success(
                f"Replay accepted expression: `{result.accepted.source}` "
                f"(policy `{result.policy.value}`)"
            )

    st.subheader("Integrity check")
    if st.button("Verify storage integrity", key="au_integrity"):
        report = audit_integrity()
        if report["passed"]:
            st.success(
                f"Integrity passed — runs={report['runs_checked']}, "
                f"observations={report['observations_checked']}, "
                f"events={report['audit_events_checked']}"
            )
        else:
            st.error("Integrity failed")
            st.json(report["issues"])

    st.subheader("Error records")
    error_rows = [
        row
        for row in history
        if str(row.get("notes", "")).lower().find("error") >= 0
        or row.get("kind") == "error"
    ]
    if error_rows:
        st.dataframe(error_rows, use_container_width=True)
    else:
        st.info(
            "No dedicated error-history rows in the current run history view. "
            "Integrity and export paths surface error records when present."
        )


def render_page(name: str) -> None:
    """Dispatch to one of the six specified pages."""

    mapping = {
        "Expression Workbench": render_expression_workbench,
        "Verification Explorer": render_verification_explorer,
        "Fuzzing and Mutation Lab": render_fuzzing_mutation_lab,
        "Benchmark Lab": render_benchmark_lab,
        "Research Dashboard": render_research_dashboard,
        "Audit and Reproducibility": render_audit_reproducibility,
    }
    renderer = mapping.get(name)
    if renderer is None:
        st = _st()
        st.error(f"Unknown page: {name}")
        return
    renderer()
