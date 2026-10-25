# A2 Part C starter files — 1.1.3

The Part C assignment page on Canvas contains the assessment brief. Start with `starter/` and read `CHECKER_CONTRACT.md` for the manifest and automated checks.

- `starter/`: complete working example; copy it for each dashboard.
- `schemas/dashboard.schema.json`: manifest schema, version 2.
- `config/topic_profiles.yml`: subject-specific integrity fields.
- `grader/`: the same checker used by teaching staff.

Use Python 3.11 for the starter. From this extracted folder:

```bash
pip install -r starter/requirements.txt -r grader/requirements.txt
python grader/grade_submission.py starter --run-transform \
  --json-output grading-report.json --markdown-output grading-report.md
```

Replace `starter` with the path to each of your dashboards. Install any extra pinned dependencies they require. The supplied example should receive 70/70 automated marks. It illustrates the technical contract, not the analytical ambition required for a strong final submission.

Keep `requirements.txt` and `pyproject.toml` consistent when supplying both. Install dashboard and checker dependencies together; resolve installation, dependency-declaration or grading-environment conflicts before relying on a report. See the contract for date/range defaults, button tests and safe environment placeholders.

Write reports outside each submitted dashboard and keep them outside the final ZIP. Reports record the submitted files' fingerprints; any application, pipeline, data or dependency change requires a new run. CSV string identifiers are preserved exactly (including leading zeros and literal `NA`); only empty CSV fields count as missing. Use explicit string dtypes when loading identifiers in your own app and pipeline too.

The report is advisory; the official run uses this release in a matching clean environment. Manual assessment and caps still apply. See `starter/README.md` to run the app and pipeline.
