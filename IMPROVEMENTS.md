# gallium_extractor.py — Refactoring Progress

Total file size at start: **~10,962 lines**

Each phase is committed separately. Check marks indicate completed work.

---

## Phase 1 — Bug Fixes

| # | Note | Description | Status |
|---|------|-------------|--------|
| 1 | IMPROVE-24 | Fix float-to-minutes rounding in `parse_eobhrmin` (use `round()` not `int()`) | ✅ |

---

## Phase 2 — Move imports to top

| # | Note | Description | Status |
|---|------|-------------|--------|
| 2 | IMPROVE-18 / IMPROVE-09 | Move `statistics`, `re`, `hashlib`, `stat`, `traceback`, `time`, `datetime/timedelta` from inside methods to top-level imports | ⬜ |

---

## Phase 3 — Extract small helpers

| # | Note | Description | Status |
|---|------|-------------|--------|
| 3 | IMPROVE-11 | Add `_to_date()` module-level helper; replace ~15 date-normalisation blocks | ⬜ |
| 4 | IMPROVE-14 | Add `_fmt_date_str()` helper; replace repeated date→string pattern in `count_sf_references` | ⬜ |
| 5 | IMPROVE-04 | Add `_fmt_bo()` staticmethod; replace ~25 inline BO-formatter expressions | ⬜ |

---

## Phase 4 — Merge near-duplicate methods

| # | Note | Description | Status |
|---|------|-------------|--------|
| 6 | IMPROVE-01 | Merge 4 `connect_*` methods into `_connect_access_db(path, attr, label)` | ⬜ |
| 7 | IMPROVE-02 | Merge `extract_gallium_opbrengsten_data` + `extract_indium_opbrengsten_data` into `_extract_opbrengsten(table_name)` | ⬜ |
| 8 | IMPROVE-03 | Merge `get_efficiency_last_year_average` + `get_efficiency_last_3months_average` into `_efficiency_average_since(days)` | ⬜ |
| 9 | IMPROVE-16 | Merge `get_within_spec_last_year_average` + `get_within_spec_last_3months_average` into `_within_spec_average_since(days)` | ⬜ |

---

## Phase 5 — Consolidate loops

| # | Note | Description | Status |
|---|------|-------------|--------|
| 10 | IMPROVE-13 | Extract `_convert_isotope_to_gantt(data, product_code, cutoff_date)` and call for Ga/Rb/In/Tl | ⬜ |
| 11 | IMPROVE-15 | Replace 5 per-isotope loops in `calculate_within_spec_percentage` with a single loop over `ISOTOPE_DATASETS` | ⬜ |
| 12 | IMPROVE-14 | Replace 5 per-isotope blocks in `count_sf_references` with a single loop | ⬜ |

---

## Phase 6 — Promote inner functions to static methods

| # | Note | Description | Status |
|---|------|-------------|--------|
| 13 | IMPROVE-12 | Move `parse_eobhrmin`, `map_cyclotron_name`, `calculate_start_time`, `get_eob_time`, `create_end_datetime` out of `convert_bestralingen_to_gantt_format` to `@staticmethod`s | ⬜ |
| 14 | IMPROVE-10 | Move `get_*_color` helpers inside `generate_dashboard` to `@staticmethod`s | ⬜ |

---

## Phase 7 — Refactor `store_in_sqlite`

| # | Note | Description | Status |
|---|------|-------------|--------|
| 15 | IMPROVE-19 | Define `_TABLE_SCHEMAS` registry dict; generate CREATE/UPDATE/INSERT SQL from it to eliminate 4 parallel if/elif branches | ⬜ |

---

## Phase 8 — Code hygiene

| # | Note | Description | Status |
|---|------|-------------|--------|
| 16 | IMPROVE-17 | Replace bare `except:` / `except Exception: pass` with specific types + logging | ⬜ |
| 17 | IMPROVE-20 | Remove ~40 commented-out debug `# print(...)` blocks | ⬜ |

---

## Phase 9 — Architecture

| # | Note | Description | Status |
|---|------|-------------|--------|
| 18 | IMPROVE-23 | Extract 9 hardcoded path defaults from `__init__` into a `DEFAULT_PATHS` config dict at module level | ⬜ |
| 19 | IMPROVE-08 | Simplify `close()` with a single loop over connection attributes | ⬜ |
| 20 | IMPROVE-21 | Add `reset()` method to `IsotopeDashboardGenerator`; reuse single instance in `__main__` instead of recreating every 60 s | ⬜ |

---

## Phase 10 — Dashboard deduplication

| # | Note | Description | Status |
|---|------|-------------|--------|
| 21 | IMPROVE-05 | Extract `_build_week_table_rows(records, *, with_onclick)` shared by abbreviated + full dashboards | ⬜ |
| 22 | IMPROVE-06 | Extract `_fmt_rb_cell(record, *, with_onclick)` used in 4 places | ⬜ |
| 23 | IMPROVE-07 | Wrap HTML-write file-protection in `@contextmanager _writable_output(html_path, hash_path)` | ⬜ |
| 24 | IMPROVE-22 | Extract static CSS + JS from `generate_gantt_chart_html` into module-level string constants | ⬜ |

---

## Line Count Progress

| After phase | Lines | Δ lines |
|-------------|-------|---------|
| Baseline    | 10,962 | — |
| Phase 1 | 11,070 | +108 (notes added earlier) |
| Phase 2 | | |
| Phase 3 | | |
| Phase 4 | | |
| Phase 5 | | |
| Phase 6 | | |
| Phase 7 | | |
| Phase 8 | | |
| Phase 9 | | |
| Phase 10 | | |
