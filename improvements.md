# gallium_extractor.py — Improvement Plan

## Status Legend
- [ ] Planned
- [x] Done

---

## Critical

### C1 — SQL injection risk in `store_in_sqlite` [ ]
- **Lines:** ~2048, ~2066
- **Problem:** `ALTER TABLE {table_name} ADD COLUMN {_col} {_typ}` uses raw f-strings. No whitelist check confirms `table_name` is in `_TABLE_SCHEMAS` before it touches the DB.
- **Fix:** Add `if table_name not in self._TABLE_SCHEMAS: raise ValueError(...)` guard at the top of `store_in_sqlite`. Wrap DDL identifiers in backticks/brackets.

### C2 — Mutable class-level `_excel_cache` shared across instances [ ]
- **Line:** ~408
- **Problem:** `_excel_cache = {}` is a class attribute. All instances share the same dict; concurrent or sequential re-use corrupts cached data.
- **Fix:** Move to `__init__`: `self._excel_cache = {}`.

---

## High Priority

### H1 — O(n²) matching loop in `calculate_gallium_production_efficiency` [ ]
- **Lines:** ~3095–3109
- **Problem:** Inner linear scan over all `opbrengsten` for every `bestraling`.
- **Fix:** Pre-index `opbrengsten` into a dict keyed by date before the loop; O(1) lookup.

### H2 — Same O(n²) pattern in `calculate_indium_production_efficiency` [ ]
- **Lines:** ~3272–3286
- **Fix:** Same pre-index approach as H1.

### H3 — Hardcoded `-999` sentinel for missing iodine targetstroom [ ]
- **Lines:** ~1851–1854, ~3773–3774 and elsewhere
- **Problem:** `-999` and `None` are both used to represent "missing", creating scattered dual-check branches throughout the code. `-999` is also a valid numeric range in some domains.
- **Fix:** Remove `-999`; use `None` consistently. Update all downstream `== -999` checks to `is None`.

### H4 — Wrong condition in `parse_eobhrmin` [ ]
- **Line:** ~715
- **Problem:** `if not eobhrmin_str and eobhrmin_str != 0:` — the second clause is unreachable when the first is True.
- **Fix:** `if eobhrmin_str is None or eobhrmin_str == '': return None`

### H5 — Temp file descriptor not protected by `try/finally` in xlsx loaders [ ]
- **Lines:** ~4126–4132 (`load_ploegen_definitions`), ~4282–4284 (`load_vsm_data`), ~4445–4448 (`load_planning_data`)
- **Problem:** If `wb_original.save()` raises, `os.close(temp_fd)` is never called, leaking the file descriptor.
- **Fix:** Move `os.close(temp_fd)` into a `finally` block in all three loaders.

---

## Medium Priority

### M1 — Efficiency calculation duplicated 4–5× (one per isotope) [ ]
- **Affected methods:** `calculate_gallium_production_efficiency`, `calculate_indium_production_efficiency`, `calculate_rubidium_production_efficiency`, `calculate_iodine_production_efficiency`
- **Problem:** All four share the same structure: match bestraling → convert duration → calculate µAh → convert MBq→mCi → aggregate per week.
- **Fix:** Extract a shared `_calculate_production_efficiency(self, data, opbrengsten, ...)` helper; each isotope method becomes a thin wrapper.

### M2 — Friday–Thursday week boundary calculation duplicated [ ]
- **Affected methods:** `calculate_within_spec_percentage`, `calculate_otif_gedraaide_producties`, `calculate_shift_statistics`, others
- **Fix:** Extract `def _get_friday_week(self, date): return date - timedelta(days=(date.weekday() - 4) % 7)`

### M3 — ISO week parsing via `strptime` is ambiguous near year boundaries [ ]
- **Lines:** ~2639, ~2667, ~2984, ~3002
- **Problem:** `datetime.strptime(f"{y}-W{w:02d}-1", '%Y-W%W-%w')` behaves inconsistently at year boundaries.
- **Fix:** Replace with `date.fromisocalendar(year, week, 1)`.

### M4 — `_fmt_bo` returns `None` (not a string) when input is `None` [ ]
- **Lines:** ~145–147
- **Problem:** Return type is inconsistent — callers using the result in f-strings get `"None"` as a string silently.
- **Fix:** Add `if bo is None: return None` explicitly at the top, or always return `str`.

---

## Low Priority

### L1 — Bare `except Exception: pass` in SQLite cache helpers and file loaders [ ]
- **Lines:** ~1429–1430 (`_excel_cache_load_sqlite`), ~1441–1442 (`_excel_cache_save_sqlite`), ~4120, ~4201, ~4274, ~4398, ~4436
- **Fix:** Catch specific exception types and log at minimum: `except (json.JSONDecodeError, sqlite3.OperationalError) as e: print(f"[WARNING] ...")`

### L2 — SQLite cursor not explicitly closed in `store_in_sqlite` [ ]
- **Lines:** ~2033–2130
- **Fix:** Add `cursor.close()` after commit, or use cursor as context manager.

### L3 — Silent skip when parsed year is out of range [ ]
- **Lines:** ~2559–2561
- **Fix:** Add `print(f"[WARNING] Skipping date with year {iso_year}")` before `continue`.

---

## Implementation Order

1. C1 — SQL injection guard
2. C2 — Class-level cache
3. H4 — Wrong condition (`parse_eobhrmin`)
4. H5 — Temp file descriptor leaks
5. H3 — Remove `-999` sentinel
6. H1 + H2 — O(n²) loops
7. M3 — ISO week parsing
8. M4 — `_fmt_bo` return type
9. M1 + M2 — Deduplication
10. L1 — Bare excepts
11. L2 — Cursor cleanup
12. L3 — Silent skip logging
