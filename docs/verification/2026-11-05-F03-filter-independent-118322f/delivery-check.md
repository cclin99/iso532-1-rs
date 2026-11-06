# Delivery quality record

Numerical experiments and bilingual reports: Astra (`gpt-6-astra`). Claim/evidence review and final delivery checks: coordinating agent. Date: 2026-11-05, Asia/Taipei. Product snapshot: `118322f8300dc752f1d38a79db230a2db5ff2870`.

## Execution and scope

Fresh C CLI/DLL builds, 48 CLI cases, the Rust frontend experiment, direct-C controls, workbook extraction, and the decimal rounding audit completed. `tools.json`, `analysis-run.log`, the numerical JSON files, and the bilingual reports record the results. The initial Rust workspace-membership failure is preserved in `rust-build-initial-environment-failure.log`; adding `[workspace]` to the isolated harness resolved it. This repaired environment failure is distinct from the strict numerical claims that failed.

The report review caught and corrected the attribution label for a comparison that changed both frontend and RMS interval. The final `frontend_method_delta_sone` and `matched_skip_filter_effects` explicitly distinguish these comparisons. No product DSP, tests, coefficients, goldens, previous-round evidence, or release records were changed. No commit, push, tag, or remote build was performed. Full release/performance acceptance and theoretical ENBW remeasurement were not run.

## Delivery checks

The final commands are:

```text
python tools/redact_paths.py docs/verification/2026-11-05-F03-filter-independent-118322f
python tools/redact_paths.py --check docs/verification/2026-11-05-F03-filter-independent-118322f
python tools/doc_pairs.py --check
git diff --check
```

`delivery-audit.json` records the actual redaction output, post-redaction inspection of every delivered file, original-source/preregistration hash checks, local Markdown link checks, new-file whitespace inspection, and product working-tree status. The directory contains only UTF-8 text in formats covered by the redactor. System toolchain paths under Program Files are installation locations, not user-identifying paths; personal/workspace prefixes are replaced. The audit includes files beyond those that a tracked-only `git diff` would inspect because this delivery remains untracked.

The document-pair check retains ten pre-existing backlog warnings; these do not indicate missing pairs in this delivery. Original-source/input/binary hashes keep their original meaning. `delivery-integrity.json` is generated after all redaction and QA updates, hashes the delivered bytes, and excludes only itself. Its verification is performed after creation. No original raw/binary hash is replaced with a redacted-copy hash.
