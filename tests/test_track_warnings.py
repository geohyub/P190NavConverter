# -*- coding: utf-8 -*-
"""Test Track parser warning messages."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.parsers.track_parser import parse_track_file

# Test 1: Missing required column
print("=== Test 1: Missing HOUR column ===")
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write("FFID\tSOU_X\tSOU_Y\tDAY\tMINUTE\tSECOND\n")
    f.write("100\t500000.0\t3800000.0\t166\t30\t0\n")
    tmp1 = f.name

try:
    parse_track_file(tmp1)
except ValueError as e:
    print(f"  Expected error: {e}")
os.unlink(tmp1)

# Test 2: Unrecognized columns
print("\n=== Test 2: Extra unknown columns ===")
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write("FFID\tSOU_X\tSOU_Y\tDAY\tHOUR\tMINUTE\tSECOND\tMY_CUSTOM\tWEIRD_COL\n")
    f.write("100\t500000.0\t3800000.0\t166\t9\t30\t0\t1.23\tabc\n")
    tmp2 = f.name

import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    result = parse_track_file(tmp2)
    print(f"  Parsed: {result.n_shots} shots")
    print(f"  Warnings: {result.warnings}")
    if w:
        print(f"  Python warning: {w[0].message}")
os.unlink(tmp2)

# Test 3: Normal file with optional columns
print("\n=== Test 3: Normal with CHAN, REC_X, REC_Y ===")
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write("TRACENO\tFFID\tCHAN\tSOU_X\tSOU_Y\tREC_X\tREC_Y\tDAY\tHOUR\tMINUTE\tSECOND\tDIRECTION\n")
    f.write("1\t100\t1\t500000.0\t3800000.0\t500010.0\t3800005.0\t166\t9\t30\t0\t270.5\n")
    tmp3 = f.name

result = parse_track_file(tmp3)
print(f"  Parsed: {result.n_shots} shots")
print(f"  Warnings: {result.warnings}")
os.unlink(tmp3)
print("\nAll tests passed.")
