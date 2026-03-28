"""Test: Generate Style A vs B comparison plot from test_output/2/ files."""
if __name__ != "__main__":
    import pytest
    pytest.skip("Diagnostic script for local sample files.", allow_module_level=True)

import sys
sys.path.insert(0, ".")

from p190converter.engine.qc.comparison import compare_p190_files, format_comparison_report
from p190converter.engine.qc.plot import generate_comparison_plot

STYLE_A = "test_output/2/M1406_A_S_M1406_A.p190"
STYLE_B = "test_output/2/M1406_B_S_M1406_B.p190"
OUTPUT = "test_output/2/M1406_AB_comparison.png"

print("Comparing Style A vs B...")
result = compare_p190_files(STYLE_A, STYLE_B)

# Print text report
print(format_comparison_report(result))

# Additional stats
print(f"\nChannels: {result.n_channels}")
print(f"RX Mean: {result.rx_dist_mean:.2f} m")
print(f"RX Max: {result.rx_dist_max:.2f} m")
print(f"Heading diff: {result.heading_diff_mean:.1f} deg")
print(f"Spread A: {result.spread_dir_a:.1f} deg")
print(f"Spread B: {result.spread_dir_b:.1f} deg")
print(f"Positions stored: {len(result.positions)} shots")

if result.per_channel_df is not None:
    print("\nPer-channel RX distance:")
    print(result.per_channel_df.to_string(index=False))

# Generate comparison plot
print(f"\nGenerating comparison plot: {OUTPUT}")
generate_comparison_plot(result, OUTPUT, title="M1406 Style A vs B Comparison")
print(f"Done! Plot saved to: {OUTPUT}")
