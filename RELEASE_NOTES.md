# Kit 1.1.3 — 10 September 2026

Addresses all eight findings from the third and fourth Part C adversarial reviews:

- JSON records and column-oriented objects preserve nullable exact integers before inference. Native Parquet nullable integers use lossless Arrow-backed loading too.
- Primary-key uniqueness uses declared typed values, including composite keys, numeric aliases and equivalent UTC instants; string identifiers remain distinct.
- D3 requires a real control-state change and stable output evidence against a no-interaction rerun. Reordering multiselect choices is not a state change.
- Heading evidence requires non-empty visible text, excluding comments, code examples and explicitly hidden HTML while retaining genuine HTML headings.
- Malformed YAML title/subject metadata produces explanatory reports instead of failing JSON serialization.
- Optional exports with different labels do not invalidate the assessed CSV export or supply interaction evidence. Every button sharing the assessed CSV label is still validated.
- The supplied CI dependency installer supports either permitted dependency file, or both, and resolves app/checker pins together without building the submitted project.
- Both marking CLIs reject colliding JSON/Markdown output paths before writing, including resolved aliases and existing hard links.

Manifest schema **2**, assessment weights and Canvas scaling are unchanged. Regenerate reports with **1.1.3**; distribute the same release to students and markers. A passing automated result is still not proof of analytical quality or safety of arbitrary submitted code.

## Kit 1.1.2 — 10 September 2026

Fixes the three confirmed Part C findings from the final review and four additional defects found in the follow-up adversarial pass:

- Correct range/date defaults compare by value across YAML lists, native tuples and ISO date representations; incorrect defaults remain failures with clearer evidence.
- Explicit environment placeholders, empty values and variable references do not trigger secret deductions. Real secrets remain detectable in example files, including quoted/exported assignments.
- All supplied dependency declarations are checked. Conflicting pins or omitted project dependencies are flagged and prevent final compilation; extra compatible pinned packages remain supported. A Python major-only wildcard such as `==3.*` does not count as a minor-version pin. Installation examples resolve application/checker dependencies together.
- Floating-point tolerance no longer scrambles record alignment; exact identifiers, duplicate counts and one-to-one tolerant matching are preserved.
- Date/datetime sliders accept ISO test values as well as ISO defaults.
- Disabled downloads no longer earn usable-download or empty-download credit.
- Button tests must declare `test_value: true`; the checker does not silently substitute a click for a contradictory declared value.

Schema **2**, assessment weights and Canvas scaling are unchanged. Generate fresh reports using **1.1.2**; do not mix earlier reports or checker versions. A kit-level pytest configuration keeps the full suite's test cache outside the starter fixture.

## Kit 1.1.1 — 9 September 2026

Corrects all seven confirmed findings in the independent release audit, plus the output-path concern:

- Final marks require complete requested checks, consistent totals, an unchanged submitted-file fingerprint and the current installed grader/schema/topic-profile fingerprint.
- Present folders without manifests and malformed subject blocks are held for structural review, not silently scored as absent.
- Declared string IDs survive CSV inference; missing-value semantics are explicit across samples, regenerated outputs and downloads.
- Integers compare exactly, failed numeric conversions cannot become missing values, and only floating-point measures use tolerance.
- View attribution must include its dataset's sources; additional contextual sources remain permitted.
- Pinned requirements accept inline comments and continuations.
- Processed paths cannot alias code or inputs; offline transforms cannot modify protected files. The app is tested against the successfully rebuilt copy.
- Controls are resolved inside their declared view containers. Reports must be written outside the submission.

Schema version remains **2**, and the 70 automated / 30 manual marks and Canvas scaling are unchanged. Rerun old reports with this release; 1.1.0 reports cannot be used for final compilation. Preserve previous archives for audit, but distribute only the current release.

## Kit 1.1.0 — 8 September 2026

This release replaces 1.0.0 before publication. Its manifest uses schema 2. The scoring weights remain 70 automated plus 30 marker points per dashboard.

- Rebuilds processed data without stale outputs and validates sample plus regenerated datasets.
- Verifies real scoped outputs, payload changes and CSV content; rejects text-only substitutes and always-visible empty messages.
- Supports file-based page navigation and widget lookup by key.
- Reports malformed manifest errors without continuing into invalid structures.
- Accepts all documented heading forms, including all-HTML headings.
- Separates observation dates from retrieval dates and checks actual sample dates.
- Aligns example pipeline validation with its manifest and replaces stale README commands.
- Documents required/optional keys and subject-specific integrity blocks.
- Adds submission-level checks for the AI declaration, distinct subjects, missing dashboards, matching grader versions and Canvas scaling.
- Records grader version, Python version and code fingerprint in reports; marker and student releases are built from the same source.

Python socket restrictions aid offline testing. OS isolation and human verification of claims/provenance remain necessary when marking untrusted submissions.
