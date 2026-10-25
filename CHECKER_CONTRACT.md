# Dashboard checker contract — kit 1.1.3 / schema 2

The Canvas Part C page contains the assignment requirements. This document explains the interface used by its 70-mark checker. Analytical quality and the truth of claims remain part of the marker's 30 marks; a passing automated report is not proof of a good analysis.

## Run the complete check

Use Python 3.11 for the supplied starter. Install its dependencies and the checker dependencies into the same environment. If you change the dashboard's Python version or dependencies, use a matching environment when checking it.

```bash
pip install -r starter/requirements.txt -r grader/requirements.txt
python grader/grade_submission.py path/to/dashboard --run-transform \
  --json-output grading-report.json --markdown-output grading-report.md
```

The CLI copies the submission to temporary storage before running the app. The transform is run in another disposable copy with every declared processed output removed. It must recreate the files within 30 seconds, without changing source samples, application code or other non-output files. Python/cache files in the excluded directories below are ignored. When rebuilding succeeds, the app is exercised in that rebuilt copy. C1–C3 validate both the sample and regenerated data; C4 checks regeneration. A do-nothing command cannot reuse submitted outputs. Omitting `--run-transform` leaves C4 untested and validates submitted processed files instead; such a report cannot be compiled into final marks.

Python network connections are blocked in the app and Python transform subprocess. This is an offline check, not a security sandbox for hostile code. Teaching staff must also isolate untrusted submissions at operating-system level.

## Manifest fields

Set `schema_version: 2`. Required keys are those listed by `required` in `schemas/dashboard.schema.json`; optional example keys are not mandatory. Unknown keys are rejected in structured blocks. The `topic_integrity` block intentionally accepts subject-specific keys: replace the WDI example with your own subject's `required_fields` from `config/topic_profiles.yml`, and use applicable `conditional_guidance`. Those conditional fields and the substance of integrity statements are reviewed by the marker.

Every dataset has a unique ID, sources, distinct `sample` and `processed_output` paths, declared columns and primary key. CSV, JSON and Parquet are supported. The sample is already in the shape consumed by the app. The pipeline's offline mode must regenerate processed data from that sample. The live pipeline may acquire and transform raw data differently.

Processed outputs must have the matching `.csv`, `.json` or `.parquet` extension and cannot alias any source sample, application page, pipeline/acquisition file or configuration file, including through `..`/equivalent paths. Offline mode writes only the declared processed outputs; acquisition and raw-data refresh belong in the separate live mode.

CSV values are interpreted using the declared column types. String identifiers retain leading zeros and literal values such as `NA`, `null` and `NaN`; only empty CSV fields are missing. JSON nulls and Parquet nulls are missing. Integers are exact, including nullable large integers. Numeric values must be finite. Preserve these semantics in your app and pipeline too, for example `pd.read_csv(path, dtype={"country_code": str}, keep_default_na=False, na_values=[""])`.

JSON may use a record array or a column-oriented object. Preserve nullable integers before DataFrame inference, for example construct object-typed columns from `json.load` rather than relying on `pd.read_json(dtype=False)`. Primary-key uniqueness follows declared types: integer `"01"` and `"1"` are the same key, and equivalent UTC instants are the same datetime key. They remain different identifiers if explicitly declared as strings.

A view must cite every source of its declared dataset in `source_ids`. It may cite additional contextual sources as well; all declared view sources must have their titles and publishers visibly attributed beside that view.

Declare `date_column` and `latest_observation` for time-based data. Use `date_minimum` and `date_maximum` for date bounds; numeric `minimum`/`maximum` describe measures. The sample's latest observation must match `latest_observation`. For a dataset without any observation date, omit both fields and display `Latest observation: not applicable`, explaining its coverage separately.

## Views and pages

Each view names its primary `dataset_id` and, optionally, its `page` relative to the dashboard root (defaults to `dashboard.entrypoint`). Additional pages must be listed in `dashboard.pages` and reachable through Streamlit navigation. Both `st.navigation` with file-based `st.Page` entries and conventional `pages/` navigation are supported. Define views on a file-based page, not an unaddressable navigation callback.

Wrap each principal view in a container whose key is the view ID:

```python
with st.container(key="population_trend"):
    render_population_view(data)
```

Put that view's title, unit, full source titles and publishers, latest-observation caption, controls and outputs inside the container. Repeated controls may share labels, but use distinct widget keys. The page heading may use `st.title`, `st.header`, `st.subheader`, a markdown heading, or an HTML `<h1>`–`<h6>` inside `st.markdown`.

Headings must contain visible, non-empty text. HTML headings require `unsafe_allow_html=True`; comments, code examples and explicitly hidden HTML do not establish a heading. External CSS and visual accessibility still require human inspection.

Declare `outputs` using the kinds actually rendered: `chart`, `metric`, `table`, `download`. At least one non-download output is required per view. This is a declaration of output kinds, not arbitrary names or a minimum chart count. The checker verifies real rendered elements inside the matching container. Images and text describing a chart do not count as a chart.

Supported charts are Streamlit native line/bar/area/scatter charts, Altair/Vega-Lite, Plotly, PyDeck and Graphviz. Tables are `st.dataframe` or `st.table`; metrics are `st.metric`. A static Matplotlib image does not satisfy a declared `chart` output. Additional illustrations/custom components are allowed alongside the assessable principal outputs.

## Controls, downloads and empty states

Each control declares its Streamlit `key`, `type`, visible `label`, and a `test_value` different from its initial state. `default_value` is optional, but is checked when supplied. `expected_text` is optional supplementary evidence; it cannot substitute for a change in a real chart, metric, table or download payload.

The checker verifies that the control's actual state changes and compares output against a no-interaction baseline rerun. A clock or other unstable output does not establish an interaction. Keep at least one relevant assessed output deterministic for the same selection. Reordering the same multiselect choices is not a different selection.

Represent range defaults/tests as YAML lists and dates as quoted ISO strings, for example `["2019-01-01", "2023-12-31"]`. Equivalent list/tuple and native date representations are accepted for defaults. Date/datetime sliders also accept ISO test strings. A button's `test_value` must be `true`, meaning a click. Controls and downloads must be enabled for their tested states; a disabled download is not usable evidence for D4/D5.

For a record filter, also declare its column and operation:

```yaml
filter:
  column: country
  operator: isin
```

Supported operations are `isin` (selected list), `equals` (single value), `range` (inclusive lower/upper pair), and `contains` (literal case-sensitive text). Multiple filters on a view combine with AND. A view's filters must be inside its container. Controls that change a measure or chart presentation may omit `filter`; they still must change an actual output.

Provide a CSV download of the view's filtered record-level dataset, retaining all the columns in that dataset. Chart aggregations may use those records differently. Declare `download` among the view's outputs. The checker reads the actual download bytes and compares rows and values with the selected sample records, ignoring row/column ordering. Strings and integers compare exactly; declared `number` fields allow floating-point tolerance (`rel_tol=1e-10`, `abs_tol=1e-10`). Invalid numeric text does not count as missing. Renamed or derived download columns belong in a declared derived dataset with its own sample and processed output. The manifest's `download_label` must match the download button label.

Only buttons with that exact `download_label` inside the view are assessed as CSV downloads. Optional exports (for example JSON) are allowed with different labels and do not affect CSV or interaction marks. If multiple buttons share the assessed label, all must be enabled and export the correct CSV records. A differently labelled export cannot substitute for the required CSV.

Include at least one record-filter control with `empty_test_value` and `empty_expected_text`. Choose an empty selection that really yields zero records. Its message must appear only when empty; hide the chart/table/metric outputs for that state and retain a header-only CSV download. The checker confirms the expected zero rows, message transition, absence of stale outputs and empty download. An always-visible “no data” message does not pass.

The relevant marks are D1 outputs (4), D2 controls execute (3), D3 outputs change (4), D4 empty state (3), D5 filtered CSV download (3). With no controls, D2–D4 cannot be earned; with no CSV download, D5 and the verified empty-download part of D4 cannot be earned.

## Final submission

Submit one ZIP with three dashboard folders for three distinct subjects and one completed `AI_DECLARATION.md` at the ZIP root. Each folder includes its app, pipeline, views, manifest, sample, processed data, README, and pinned dependency/Python declarations. Do not submit virtual environments, symlinks, credentials or data you may not redistribute.

Keep supporting files inside their dashboard folders; do not add unrelated top-level directories. The compiler holds present folders without a manifest for structural review rather than silently treating them as absent. macOS `__MACOSX` packaging metadata is ignored. An entirely absent dashboard still scores zero.

Keep checker/portfolio reports outside the submitted dashboard and extracted submission. Final compilation verifies the dashboard path, a fingerprint of all submitted regular files, the installed grader/configuration fingerprint, complete requested checks and consistent score totals. File changes require regrading. Fingerprints ignore `.git`, `.venv`, `venv`, `__pycache__`, `.pytest_cache` and `.DS_Store`; application/data files must not be placed there. This is stale-report protection, not a cryptographic signature: markers must generate their own reports, never trust student-supplied report JSON.

Dependency declarations may use exactly pinned requirements with blank lines, full-line/inline comments and backslash continuations. More elaborate pip installer options are not part of this requirements-file interface; use `pyproject.toml` for the project's dependency declarations.

If both `pyproject.toml` and `requirements.txt` are supplied, the requirements file must install all active project dependencies and requested extras with agreeing exact pins. It may include additional pinned packages. Environment markers are evaluated for the grading environment; inactive platform/version branches do not conflict. Contradictory pins, including duplicates within a file, fail A2. Missing project dependencies or conflicting files raise `DEPENDENCY DECLARATION CONFLICT`, which must be resolved before final compilation. Install application and checker requirements together so an installer conflict is reported instead of silently replacing one set of versions.

An environment template may contain empty values, comments, external references such as `${API_TOKEN}`, or explicit placeholders such as `your_token_here`, `your_api_key_here`, `your_password_here`, `replace_me` and `changeme`. These values do not trigger credential deductions. Template filenames do not exempt real secrets: a non-placeholder credential assignment or recognized private-key/token pattern still zeroes F1/F2. The scanner is heuristic, not proof that a submission contains no secrets; markers must review flags and students remain responsible for removing credentials.

Run the full checker separately for each dashboard. The sample is a small real-data subset sufficient to exercise every principal view, filter and test selection. The marker reruns the same released checker version in an appropriate clean environment, verifies the declaration, assesses the analysis and confirms caps.
