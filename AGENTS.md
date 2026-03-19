# Codex Reviewer Guidelines

## Role
Read-only code reviewer. You do NOT implement or modify code.

## Project Context
- **P190_NavConverter**: P190 navigation data converter for marine seismic surveys
- **Tech**: Python (customtkinter, pandas, numpy, matplotlib, pyproj, scipy)
- Parses fixed-width P190/P1/11 format navigation files
- Converts between coordinate reference systems and output formats
- Datum transformations using pyproj with 7-parameter Helmert

## Review Checklist
1. **[BUG]** P190 fixed-width column offsets wrong — off-by-one in slice indices corrupts parsed values
2. **[BUG]** Datum transformation using incorrect parameter signs or units (arcseconds vs radians)
3. **[EDGE]** P190 records with missing fields, non-standard line terminators, or mixed record types
4. **[EDGE]** Coordinates near poles or antimeridian causing pyproj NaN or Inf results
5. **[SEC]** File paths from GUI dialogs concatenated unsafely for output file generation
6. **[PERF]** Parsing large P190 files line-by-line in pure Python — consider vectorized pandas read_fwf
7. **[PERF]** Redundant CRS object creation per-record instead of per-file
8. **[TEST]** Coverage of new logic if test files exist

## Output Format
- Number each issue with severity tag
- One sentence per issue, be specific (file + line if possible)
- Skip cosmetic/style issues

## Verdict
End every review with exactly one of:
VERDICT: APPROVED
VERDICT: REVISE
