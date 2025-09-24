import numpy as np
from matplotlib.colors import to_rgb, to_hex, ListedColormap
from skimage import color

# ==== (COLD → NEUTRAL → WARM) ANCHOR COLORS ====
palette_anchors = [
    "#231cf3", "#3171fb", "#54acff", "#86d9ff", "#a2eafa",
    "#f6f6f6",
    "#c2ffd8", "#c0ff77", "#edff4b", "#ffd427", "#ff7316"
]
# e.g. #231cf3, #3171fb, #54acff, #86d9ff, #a2eafa,
#      #f6f6f6,
#      #c2ffd8, #c0ff77, #edff4b, #ffd427, #ff7316 
#
# or e.g. #6c8fff, #3adafa, #a0def5, 
          #f6f6f6, 
          #c7fede, #f9dc74, #ffaa17

# ==== TEMPERATURE PALETTE GENERATION FUNCTIONS ====
def interpolate_lab(hex_colors, n_colors):
    # Interpolate n_colors between given hex colors in LAB space.
    rgb = np.array([to_rgb(c) for c in hex_colors])
    lab = color.rgb2lab(rgb[np.newaxis, :, :])
    x = np.linspace(0, 1, lab.shape[1])
    xi = np.linspace(0, 1, n_colors)
    lab_interp = np.array([np.interp(xi, x, lab[0, :, i]) for i in range(3)]).T
    rgb_interp = color.lab2rgb(lab_interp[np.newaxis, :, :])[0]
    return [to_hex(c) for c in rgb_interp]

def get_temperature_colormap(n_colors, anchors=None):
    # Return a ListedColormap and palette.
    if anchors is None:
        anchors = palette_anchors
    palette = interpolate_lab(anchors, n_colors)
    return ListedColormap(palette, name="cold_neutral_warm"), palette

# ==== DEMO: VISUALIZE PALETTE ====
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # Demo parameters
    COLDEND = -15
    WARMEND = 30
    DEMO_N_COLORS = int(WARMEND)*2+1 # Odd number centers the white-ish color block at 0°C.

    # Generate palette and plot
    cold_neutral_warm_palette = interpolate_lab(palette_anchors, DEMO_N_COLORS)
    fig, ax = plt.subplots(figsize=(12, 1))
    for i, color_hex in enumerate(cold_neutral_warm_palette):
        ax.fill_between([i, i+1], 0, 1, color=color_hex)
    ax.get_yaxis().set_visible(False)

    # Add tick marks for COLDEND, 0, and WARMEND
    n = len(cold_neutral_warm_palette)
    tick_positions = [0, (n-1)/2+0.5, n]
    tick_labels = [f"{COLDEND}°C", "0°C", f"{WARMEND}°C"]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=12, fontweight='bold')
    ax.tick_params(axis='x', length=10, width=2)
    ax.set_xlim(0, n)

    plt.tight_layout()
    plt.show()
    