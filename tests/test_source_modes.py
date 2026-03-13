# -*- coding: utf-8 -*-
"""Test: Style A source position modes and COS_Sparker vs Head_Buoy.

Three test cases:
  1. front_gps mode + Head_Buoy (current default) → ~25m gap
  2. front_gps mode + COS_Sparker → ~11m gap (improved)
  3. track_sou mode → 0m gap (exact match)

Then compare all three against Style B.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.pipeline import ConversionPipeline
from p190converter.engine.qc.comparison import compare_p190_files, format_comparison_report
from p190converter.models.survey_config import SurveyConfig, MarineGeometry, CRSConfig

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'
STYLE_B = 'test_output/2/M1406_B_S_M1406_B.p190'
OUTPUT_DIR = 'test_output/3'

os.makedirs(OUTPUT_DIR, exist_ok=True)

geom = MarineGeometry(
    source_dx=2.2547, source_dy=60.535,
    rx1_dx=-1.2453, rx1_dy=69.7075,
    n_channels=16, rx_interval=1.0,
    cable_depth=0.0, interp_method="linear",
)
crs = CRSConfig.from_zone(51, "N")

test_cases = [
    {
        "name": "A1_HeadBuoy",
        "front_gps": "Head_Buoy",
        "tail_gps": "Tail_Buoy",
        "source_mode": "front_gps",
        "description": "Front GPS=Head_Buoy (current default)",
    },
    {
        "name": "A2_COS_Sparker",
        "front_gps": "COS_Sparker",
        "tail_gps": "Tail_Buoy",
        "source_mode": "front_gps",
        "description": "Front GPS=COS_Sparker (improved)",
    },
    {
        "name": "A3_TrackSOU",
        "front_gps": "Head_Buoy",
        "tail_gps": "Tail_Buoy",
        "source_mode": "track_sou",
        "description": "Track SOU_X/SOU_Y (=RadExPro match)",
    },
]

results = []
for tc in test_cases:
    print(f"\n{'='*60}")
    print(f"  {tc['name']}: {tc['description']}")
    print(f"{'='*60}")

    config = SurveyConfig(
        style="A",
        npd_file=NPD,
        track_file=TRACK,
        line_name=f"M1406_{tc['name']}",
        output_dir=OUTPUT_DIR,
        front_gps_source=tc["front_gps"],
        tail_gps_source=tc["tail_gps"],
        geometry=geom,
        crs=crs,
        source_position_mode=tc["source_mode"],
    )

    pipeline = ConversionPipeline()
    pipeline.set_log_callback(lambda level, msg: print(f"  [{level}] {msg}"))

    try:
        output_path = pipeline.run_style_a(config)
        print(f"\n  Output: {output_path}")

        # Compare with Style B
        result = compare_p190_files(output_path, STYLE_B)
        print(f"\n  vs Style B:")
        print(f"    Source mean:  {result.source_dist_mean:.2f}m")
        print(f"    Source max:   {result.source_dist_max:.2f}m")
        print(f"    Source p95:   {result.source_dist_p95:.2f}m")
        print(f"    RX mean:     {result.rx_dist_mean:.2f}m")
        print(f"    Heading diff: {result.heading_diff_mean:.1f} deg")

        results.append({
            "name": tc["name"],
            "desc": tc["description"],
            "src_mean": result.source_dist_mean,
            "src_max": result.source_dist_max,
            "rx_mean": result.rx_dist_mean,
            "hdg_diff": result.heading_diff_mean,
        })
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()

# Summary
print(f"\n{'='*70}")
print(f"  SUMMARY: Style A modes vs Style B")
print(f"{'='*70}")
print(f"{'Name':>20s}  {'SRC Mean':>8s}  {'SRC Max':>8s}  {'RX Mean':>8s}  {'Hdg Diff':>8s}")
print(f"{'-'*60}")
for r in results:
    print(f"{r['name']:>20s}  {r['src_mean']:8.2f}  {r['src_max']:8.2f}  "
          f"{r['rx_mean']:8.2f}  {r['hdg_diff']:8.1f}")
