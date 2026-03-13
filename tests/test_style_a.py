# -*- coding: utf-8 -*-
"""End-to-end Style A pipeline test."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p190converter.engine.pipeline import ConversionPipeline
from p190converter.models.survey_config import SurveyConfig, MarineGeometry, CRSConfig

NPD = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\20250721_133809_C\20250721_133809_C.NPD'
TRACK = r'C:\Users\JWONLINETEAM\Desktop\QC_인수인계_이종현\03_소프트웨어\Feathering\Sample\M1406_track.txt'

print(f'NPD exists: {os.path.exists(NPD)}')
print(f'Track exists: {os.path.exists(TRACK)}')

config = SurveyConfig(
    style='A',
    npd_file=NPD,
    track_file=TRACK,
    line_name='M1406_Test',
    output_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_output'),
    front_gps_source='Head_Buoy',
    tail_gps_source='Tail_Buoy',
    geometry=MarineGeometry(
        source_dx=0.0,
        source_dy=0.0,
        rx1_dx=-10.0,
        rx1_dy=20.0,
        n_channels=16,
        rx_interval=3.125,
        cable_depth=1.0,
        interp_method='linear',
    ),
    crs=CRSConfig.from_zone(52, 'N'),
)

os.makedirs(config.output_dir, exist_ok=True)

pipeline = ConversionPipeline()
pipeline.set_log_callback(lambda level, msg: print(f'[{level}] {msg}'))

output = pipeline.run_style_a(config)
print(f'\n=== SUCCESS ===')
print(f'Output: {output}')

with open(output, 'r') as f:
    lines = f.readlines()

h_lines = [l for l in lines if l.startswith('H')]
s_lines = [l for l in lines if l.startswith('S')]
r_lines = [l for l in lines if l.startswith('R')]

print(f'H records: {len(h_lines)}')
print(f'S records: {len(s_lines)}')
print(f'R records: {len(r_lines)}')
print(f'Expected R per shot: {(16 + 2) // 3}')
print(f'Expected total R: {len(s_lines) * ((16 + 2) // 3)}')

if s_lines:
    print(f'\nFirst S: {s_lines[0].rstrip()}')
    print(f'Last S:  {s_lines[-1].rstrip()}')
    first_ffid = s_lines[0][19:25].strip()
    last_ffid = s_lines[-1][19:25].strip()
    print(f'First FFID in P190: {first_ffid}')
    print(f'Last FFID in P190:  {last_ffid}')

over80 = [i + 1 for i, l in enumerate(lines) if len(l.rstrip()) > 80]
print(f'\nLines > 80 cols: {len(over80)}')
if over80:
    print(f'First violations: {over80[:5]}')
