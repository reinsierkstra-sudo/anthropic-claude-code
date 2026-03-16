# gallium_extractor.py — Improvement Plan

## Status Legend
- [ ] Planned
- [x] Done

---

## Critical

### C1 — SQL injection risk in `store_in_sqlite` [x]
- **Lines:** ~2048, ~2066
- **Problem:** `ALTER TABLE {table_name} ADD COLUMN {_col} {_typ}` uses raw f-strings. No whitelist check confirms `table_name` is in `_TABLE_SCHEMAS` before it touches the DB.
- **Fix:** Add `if table_name not in self._TABLE_SCHEMAS: raise ValueError(...)` guard at the top of `store_in_sqlite`. Wrap DDL identifiers in backticks/brackets.
- **Done:** Added ValueError guard before any cursor use.

### C2 — Mutable class-level `_excel_cache` shared across instances [ ]
- **Line:** ~408
- **Problem reported:** `_excel_cache = {}` is a class attribute shared across instances.
- **Assessment:** The sharing is **intentional** — a new instance is created each loop iteration and the class-level cache allows mtime-checked Excel data to survive across iterations without re-opening files. Moving to instance-level broke the cross-iteration cache. Reverted; added explicit comment documenting the design intent.

---

## High Priority

### H1 — O(n²) matching loop in `calculate_gallium_production_efficiency` [x]
- **Lines:** ~3095–3109
- **Problem:** Inner linear scan over all `opbrengsten` for every `bestraling`.
- **Fix:** Pre-sort opbrengsten by date; use `bisect.bisect_right` for O(log n) lookup.
- **Done:** Pre-parse + sort opbrengsten, bisect lookup replaces inner for-loop.

### H2 — Same O(n²) pattern in `calculate_indium_production_efficiency` [x]
- **Lines:** ~3272–3286
- **Fix:** Same pre-sort + bisect approach as H1.
- **Done:** Same fix applied.

### H3 — Hardcoded `-999` sentinel for missing iodine targetstroom [x]
- **Lines:** ~1851–1854, ~3773–3774 and elsewhere
- **Problem:** `-999` and `None` are both used to represent "missing", creating scattered dual-check branches throughout the code. `-999` is also a valid numeric range in some domains.
- **Fix:** Remove `-999`; use `None` consistently. Update all downstream `== -999` checks to `is None`.
- **Done:** Source changed to store `None`; all Python-side `== -999` checks removed. JS-side checks kept for backward-compat with old SQLite rows.

### H4 — Wrong condition in `parse_eobhrmin` [x]
- **Line:** ~715
- **Problem:** `if not eobhrmin_str and eobhrmin_str != 0:` — the second clause is unreachable when the first is True.
- **Fix:** `if eobhrmin_str is None or eobhrmin_str == '': return None`
- **Done:** Condition replaced.

### H5 — Temp file descriptor not protected by `try/finally` in xlsx loaders [ ]
- **Lines:** ~4126–4132 (`load_ploegen_definitions`), ~4282–4284 (`load_vsm_data`), ~4445–4448 (`load_planning_data`)
- **Problem:** After investigation, all three loaders already initialize `temp_file = None` before the try block and have a `finally: os.remove(temp_file)` cleanup. The fd is closed before `save()`. No change needed.
- **Status:** Not applicable — code is already correct.

---

## Medium Priority

### M1 — Efficiency calculation duplicated 4–5× (one per isotope) [ ]
- **Affected methods:** `calculate_gallium_production_efficiency`, `calculate_indium_production_efficiency`, `calculate_rubidium_production_efficiency`, `calculate_iodine_production_efficiency`
- **Problem:** All four share the same structure: match bestraling → convert duration → calculate µAh → convert MBq→mCi → aggregate per week.
- **Fix:** Extract a shared `_calculate_production_efficiency(self, data, opbrengsten, ...)` helper; each isotope method becomes a thin wrapper.
- **Status:** Deferred — requires careful audit of per-isotope differences before safe extraction.

### M2 — Friday–Thursday week boundary calculation duplicated [x]
- **Affected methods:** `calculate_within_spec_percentage`, `calculate_otif_gedraaide_producties`, `calculate_shift_statistics`, others
- **Fix:** Extract `def _get_friday_week(self, date): return date - timedelta(days=(date.weekday() - 4) % 7)`
- **Done:** `_get_friday_week` added as `@staticmethod`. Local `week_friday` lambda replaced with `self._get_friday_week`. Efficiency method inline calculations replaced.

### M3 — ISO week parsing via `strptime` is ambiguous near year boundaries [x]
- **Lines:** ~2639, ~2667, ~2984, ~3002
- **Problem:** `datetime.strptime(f"{y}-W{w:02d}-1", '%Y-W%W-%w')` behaves inconsistently at year boundaries.
- **Fix:** Replace with `date.fromisocalendar(year, week, 1)`.
- **Done:** All 4 occurrences replaced with `datetime.combine(date.fromisocalendar(...), datetime.min.time())`.

### M4 — `_fmt_bo` returns `None` (not a string) when input is `None` [x]
- **Lines:** ~145–147
- **Problem:** `if bo and ...` treated `bo=0` as falsy, skipping valid BO number 0. Return type was inconsistent.
- **Fix:** Add `if bo is None: return None` explicitly at the top.
- **Done:** Explicit None guard added; `bo=0` now correctly returns `"0"`.

---

## Low Priority

### L1 — Bare `except Exception: pass` in SQLite cache helpers and file loaders [x]
- **Lines:** ~1429–1430 (`_excel_cache_load_sqlite`), ~1441–1442 (`_excel_cache_save_sqlite`), `calculate_file_hash`
- **Fix:** Catch specific exception types and log.
- **Done:** `_excel_cache_load_sqlite` → `except (json.JSONDecodeError, sqlite3.OperationalError)` with warning. `_excel_cache_save_sqlite` → `except (sqlite3.OperationalError, TypeError)` with warning. `calculate_file_hash` → `except (IOError, OSError)` with warning.

### L2 — SQLite cursor not explicitly closed in `store_in_sqlite` [x]
- **Lines:** ~2033–2130
- **Fix:** Add `cursor.close()` after commit.
- **Done:** `cursor.close()` added after `self.sqlite_conn.commit()`.

### L3 — Silent skip when parsed year is out of range [x]
- **Lines:** ~2559–2561
- **Fix:** Add warning log before `continue`.
- **Done:** `print(f"[WARNING] Skipping within-spec record with unrealistic year {iso_year}")` added.

---

## Implementation Order

1. C1 — SQL injection guard ✓
2. C2 — Class-level cache (intentionally reverted — cross-iteration caching requires class-level)
3. H4 — Wrong condition (`parse_eobhrmin`) ✓
4. H5 — Temp file descriptor leaks ✓ (not applicable)
5. H3 — Remove `-999` sentinel ✓
6. H1 + H2 — O(n²) loops ✓
7. M3 — ISO week parsing ✓
8. M4 — `_fmt_bo` return type ✓
9. M2 — Friday week helper ✓
10. L1 — Bare excepts ✓
11. L2 — Cursor cleanup ✓
12. L3 — Silent skip logging ✓
