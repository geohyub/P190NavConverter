# -*- coding: utf-8 -*-
"""Style A v2: Track SOU_X/Y as source + RadExPro geometry values."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.pipeline import ConversionPipeline
from p190converter.models.survey_config import SurveyConfig, MarineGeometry, CRSConfig

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'

# RadExPro Marine Geometry 값 (vessel 기준) — 스크린샷 그대로 입력
config = SurveyConfig(
    style='A',
    npd_file=NPD,
    track_file=TRACK,
    line_name='M1406_A',
    output_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_output'),
    front_gps_source='Head_Buoy',
    tail_gps_source='Tail_Buoy',
    geometry=MarineGeometry(
        source_dx=2.2547,        # RadExPro Source cross-track (vessel 기준)
        source_dy=60.535,        # RadExPro Source along-track (vessel 기준)
        rx1_dx=-1.2453,          # RadExPro RX1 cross-track (vessel 기준)
        rx1_dy=69.7075,          # RadExPro RX1 along-track (vessel 기준)
        n_channels=16,
        rx_interval=1.0,
        cable_depth=0.0,         # 2D — no depth
        interp_method='linear',
    ),
    crs=CRSConfig.from_zone(51, 'N'),
)

os.makedirs(config.output_dir, exist_ok=True)
pipeline = ConversionPipeline()
pipeline.set_log_callback(lambda level, msg: print(f'[{level}] {msg}'))

output_a = pipeline.run_style_a(config)
print(f'\n=== Style A output: {output_a} ===')

# --- Compare with Style B ---
style_b = os.path.join(config.output_dir, 'M1406_S_M1406.p190')
if not os.path.exists(style_b):
    print(f'Style B not found at {style_b}, skipping comparison')
else:
    from p190converter.engine.qc.comparison import compare_p190_files, format_comparison_report
    result = compare_p190_files(output_a, style_b)
    print(format_comparison_report(result))

    # Sample: first 3 shots detail
    print('\n--- First 3 shots detail ---')
    with open(output_a) as f:
        a_lines = f.readlines()
    with open(style_b) as f:
        b_lines = f.readlines()

    a_s = [l for l in a_lines if l.startswith('S')][:3]
    b_s = [l for l in b_lines if l.startswith('S')][:3]
    a_r = [l for l in a_lines if l.startswith('R')][:6]
    b_r = [l for l in b_lines if l.startswith('R')][:6]

    print('Style A S records:')
    for s in a_s:
        print(f'  {s.rstrip()}')
    print('Style B S records:')
    for s in b_s:
        print(f'  {s.rstrip()}')
    print('Style A R records (first 2 shots):')
    for r in a_r:
        print(f'  {r.rstrip()}')
    print('Style B R records (first 2 shots):')
    for r in b_r:
        print(f'  {r.rstrip()}')
