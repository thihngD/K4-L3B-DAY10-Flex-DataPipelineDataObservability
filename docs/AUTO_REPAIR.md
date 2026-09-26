# B2: Automatic repair from the corrupted table

The bonus pipeline detects invalid data and repairs it using only the corrupted table
itself. It reads no snapshot, baseline, corruption log or network source, so it fixes
what the table still holds and reports what it cannot. The original required
baseline/corruption/raw-recovery flow remains available without the bonus flag.

## Run

From the project root, with the project environment installed:

```powershell
.\.venv\Scripts\python.exe script/run_corruption_flow.py --auto-repair
```

The input is `data/clean/papers_clean_corrupted.json`. Nothing else is read to repair it.

## Automatic decisions

1. Check the JSON structure, required fields and types, dates, and derived text fields.
2. If the schema is valid, run the existing eight GX expectations and freshness SLA.
   Freshness uses publication dates at the current run time, rather than trusting
   cached `age_days` values. Original input bytes remain unchanged.
3. If all checks pass, log `skipped_healthy`: nothing is repaired and no index is rebuilt.
4. On any schema or quality failure, repair each row from the values the table still holds:

   | Problem | Repair | Audit entry |
   |---|---|---|
   | `paper_id` already seen in an earlier row | Drop the later row | `dropped_duplicate` |
   | Noise token in the title or summary | Remove the token and its surrounding spaces | `repaired_field`, `strip_noise` |
   | `published` invalid, in the future, or earlier than `updated` | Copy `updated` | `repaired_field`, `from_updated` |
   | `updated` invalid | Copy `published` | `repaired_field`, `from_published` |
   | Title or summary missing or blank | Copy it from its line in `text_for_embedding` | `repaired_field`, `from_text_for_embedding` |
   | Authors or categories missing or not a list | Split `authors_joined` or `categories_joined` | `repaired_field`, `from_*_joined` |
   | Other text fields missing | Leave blank so cleaning fills its default | `repaired_field`, `cleaning_default` |
   | No `paper_id`, or a title, summary or date that cannot be recovered | Drop the row | `dropped_row` |
   | Title under 8 or summary under 50 characters after repair | Keep the row for retrieval and report it | `unrecoverable_field` |

   `updated` is the Crossref record date, which the parser also uses when a publication
   date is missing; in every clean record it equals `published`. Cleaning then
   recomputes the derived columns (`age_days`, joined fields, `summary_chars`,
   `text_for_embedding`) at the run timestamp.
5. Validate the candidate with the same schema and quality rules, without weakening
   thresholds, and decide:
   - every check passes → `completed`, published;
   - some failed checks are fixed and none newly fail → `partial`, published with its
     `remaining_failures`;
   - otherwise → `validation_failed` (or `repair_failed` when the input is not a JSON
     list), not published.
6. Build an isolated index for a published candidate. If the frozen evaluation set
   exists, copy it into the run directory and evaluate the candidate against that copy.
   Otherwise, explicitly log evaluation as skipped.
7. Atomically update `data/auto_repair/latest.json`, including `status` and
   `remaining_failures`, after indexing and any requested evaluation succeed.

## What the table cannot repair

- **Deleted rows** leave no trace, so `row_count` stays below its threshold.
- **Truncated titles and blank summaries** lose their text everywhere in the row,
  because corruption also rewrites `text_for_embedding`.
- **Noise inside a word** leaves the word split once the token is removed (for
  example `sema ntic`): the table cannot tell whether a space was there.
- **The date rule trusts `updated`.** A paper genuinely published before its Crossref
  record date would be moved forward.
- **Data that is simply old** has nothing to fix, so the run ends `validation_failed`.

## Artifacts and failure behavior

Every invocation creates `data/auto_repair/<run_id>/`. Depending on the stage reached,
it contains:

| Artifact | Evidence |
|---|---|
| `repair_log.json` | Input hash, trigger checks, every repair with before/after previews, counts per action and per field/method, row counts, remaining failures, evaluation, final status |
| `quality/` | Input and candidate schema, GX and freshness reports |
| `papers_clean_repaired.json`, `.csv` | Candidate data, including unpublished candidates retained for diagnosis |
| `papers_embeddings_repaired.json`, `chroma/` | Isolated index of a published candidate |
| `test_set.json`, `repaired_metrics.json`, `repaired_answers.json` | Frozen benchmark copy and actual evaluation results, when available |

Use `latest.json` to identify the latest published candidate and check its `status`;
a candidate file's existence alone does not mean it was published. `completed`,
`partial` and `skipped_healthy` exit with code 0. A failed repair, validation, index
build, evaluation or publication returns exit code 1 and leaves the previous manifest
and its index available. Logs identify the failed stage. A missing input file also
returns exit code 1.

Every candidate has its own collection and persistence directory. Existing raw,
baseline, corrupted, and required-flow artifacts are preserved. The latest manifest
is an entrypoint for consumers of the bonus index; this command does not change the
required lab agent's default collection.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests apply the lab's real corruption scenarios, then check exactly which rows are
fixed, dropped or reported and that the result is published as `partial`. They also
cover schema defects fixed from copies inside the row, rows without a `paper_id`,
input with nothing to repair, data that is too old, the frozen benchmark, exit codes,
and preservation of the previous index on failure. HTTP calls fail every auto-repair
test, and one test forbids reading the raw snapshots, the baseline clean file and the
corruption log. Only vector storage is mocked.

## Observed run: 2026-09-26

Run `20260926T154257352219Z-59897f5e` finished at 15:43:04 UTC with status `partial`.
Evaluation used `LLM_PROVIDER=mock`, `LLM_MODEL=mock`, and `RUN_RAGAS=0`, so the judge
fields come from the heuristic fallback; retrieval used the actual MiniLM/Chroma index.

| Measure | Corrupted input | Repaired |
|---|---:|---:|
| Rows | 21 | 16 |
| Quality checks passed | 3/9 | 7/9 |
| Stale rows | 6 | 1 |
| Retrieval hit rate | 0.8000 | 0.9000 |
| Mean token F1 | 0.8000 | 0.8000 |
| Judge accuracy (heuristic) | 0.8000 | 0.8000 |

The repair log records 2 dropped duplicates, 3 stripped noise tokens (2 summaries now
match the baseline exactly; one keeps `semantic` split as `sema ntic`), 6 publication
dates restored from `updated`, 3 rows dropped for blank summaries and 3 truncated
titles reported. `row_count` (16 rows) and `title_length` (3 rows) still fail. q03
and q05 remain wrong because they ask about two of the papers with truncated titles.

Evidence: [repair audit](../data/auto_repair/20260926T154257352219Z-59897f5e/repair_log.json),
[candidate quality](../data/auto_repair/20260926T154257352219Z-59897f5e/quality/repaired_quality_report.json),
and [evaluation metrics](../data/auto_repair/20260926T154257352219Z-59897f5e/repaired_metrics.json).

Two earlier approaches were replaced and their runs kept for comparison. A live
Crossref re-fetch (`20260926T143315418143Z-6059c4bf`) passed quality 9/9 but scored
0.0, because the committed snapshot is synthetic and none of its papers exist in
Crossref's live results. A repair from the raw snapshot
(`20260926T151303743236Z-7fa95ebe`) recovered everything, but it duplicated the
required flow's repair from raw.
