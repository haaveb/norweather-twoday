# ============================================================================
# TEMPERATURE COLORMAP: COLD → NEUTRAL → WARM (LUV Color Space)
# ============================================================================
# 
# ATTRIBUTION:
# - Colorblind simulation matrices: Murtagh, F. and Birch, G. (2006)
#   "Color blindness and its simulation" 
#   Via Martin Krzywinski, Canada's Michael Smith Genome Sciences Centre
#   https://mk.bcgsc.ca/colorblind/math.mhtml
#
# ============================================================================
import numpy as np
from matplotlib.colors import to_rgb, to_hex, ListedColormap
from skimage import color

# ============================================================================
# COLOR ANCHOR DEFINITIONS
# ============================================================================

# Primary anchor colors 
    # Manually assembled, in part with using https://www.hsluv.org
    # Made to be intuitive for how temperatures feel, specifically in the 
    # context of deciding what to wear. Might be specific to Oslo-weather.

palette_anchors = [
    "#1d0096", "#0025c6", "#0061eb", 
    "#2ca5ff", "#76d5ff", 
    "#f6f6f6",
    "#adffe1", "#bbfd86", 
    "#eafc3e", "#ffd314", "#fd9400",
]

# Colorblind-optimized anchors (currently same as primary)

palette_anchors_colorblind = [
    "#1d0096", "#0025c6", "#0061eb", 
    "#2ca5ff", "#76d5ff", 
    "#f6f6f6",
    "#adffe1", "#bbfd86", 
    "#eafc3e", "#ffd314", "#fd9400",
]

# ============================================================================
# COLOR INTERPOLATION FUNCTIONS
# ============================================================================
def interpolate_luv(hex_colors, n_colors): 
    """Interpolate colors in LUV color space - optimized for screens."""
    rgb = np.array([to_rgb(c) for c in hex_colors])
    luv = color.rgb2luv(rgb[np.newaxis, :, :])
    x = np.linspace(0, 1, luv.shape[1])
    xi = np.linspace(0, 1, n_colors)
    luv_interp = np.array([
        np.interp(xi, x, luv[0, :, i]) 
        for i in range(3)
    ]).T
    rgb_interp = color.luv2rgb(luv_interp[np.newaxis, :, :])[0]
    return [to_hex(c) for c in rgb_interp]

def get_temperature_colormap(
    n_colors, 
    anchors=None, 
    colorblind_friendly=False
):
    """
    Generate temperature colormap using LUV color space interpolation.
    
    Args:
        n_colors: Number of colors to generate
        anchors: Custom anchor colors (if None, uses default)
        colorblind_friendly: If True, uses colorblind-optimized anchors
    
    Returns:
        Tuple of (ListedColormap, palette_list)
    """
    if anchors is None:
        anchors = (
            palette_anchors_colorblind 
            if colorblind_friendly 
            else palette_anchors
        )
    
    palette = interpolate_luv(anchors, n_colors)
    cmap_name = (
        "cold_neutral_warm_cb" 
        if colorblind_friendly 
        else "cold_neutral_warm"
    )
    return ListedColormap(palette, name=cmap_name), palette

# ============================================================================
# COLORBLIND SIMULATION FUNCTIONS
# ============================================================================
def simulate_colorblindness(rgb_color, cb_type='protanopia'):
    """
    Simulate colorblindness by applying transformation matrices.
    
    Args:
        rgb_color: RGB color as (r, g, b) tuple/array, values 0-1
        cb_type: 'protanopia', 'deuteranopia', 'tritanopia', 
                 'protanomaly', 'deuteranomaly', 'tritanomaly', 'achromatopsia'
    
    Returns:
        RGB color as seen by someone with that type of colorblindness.
        
    References:
        Transformation matrices based on:
        Murtagh, F. and Birch, G. (2006) "Color blindness and its simulation",
        Martin Krzywinski, Canada's Michael Smith Genome Sciences Centre
        https://mk.bcgsc.ca/colorblind/math.mhtml
    """

    # Colorblind transformation matrices
    # Source: Murtagh and Birch (2006) via https://mk.bcgsc.ca/colorblind/math.mhtml
    matrices = {
        # Complete absence (dichromacy)
        'protanopia': np.array([
            [0.152286, 1.052583, -0.204868],
            [0.114503, 0.786281, 0.099216], 
            [-0.003882, -0.048116, 1.051998]
        ]),
        'deuteranopia': np.array([
            [0.367322, 0.860646, -0.227968],
            [0.280085, 0.672501, 0.047413],
            [-0.011820, 0.042940, 0.968881]
        ]),
        'tritanopia': np.array([
            [1.255528, -0.076749, -0.178779],
            [-0.078411, 0.930809, 0.147602],
            [0.004733, 0.691367, 0.303900]
        ]),
        # Reduced sensitivity (anomalous trichromacy)
        'protanomaly': np.array([
            [0.458064, 0.679578, -0.137642],
            [0.092785, 0.846313, 0.060902],
            [-0.007494, -0.016807, 1.024301]
        ]),
        'deuteranomaly': np.array([  # Most common type.
            [0.547494, 0.607765, -0.155259],
            [0.181692, 0.781742, 0.036566],
            [-0.010410, 0.027275, 0.983136]
        ]),
        'tritanomaly': np.array([
            [1.017277, 0.027029, -0.044306],
            [-0.006113, 0.958479, 0.047634],
            [0.006379, 0.248708, 0.744913]
        ])
    }
    
    if cb_type == 'achromatopsia':
        # Complete color blindness - convert to grayscale using luminance
        # Standard luminance weights: R=0.299, G=0.587, B=0.114
        luminance_weights = np.array([0.299, 0.587, 0.114])
        if rgb_color.ndim > 1:
            gray_values = np.dot(rgb_color, luminance_weights)
            return np.column_stack([gray_values, gray_values, gray_values])
        else:
            gray_value = np.dot(rgb_color, luminance_weights)
            return np.array([gray_value, gray_value, gray_value])
    
    if cb_type not in matrices:
        return rgb_color
    
    # Apply transformation matrix
    rgb_array = np.array(rgb_color).reshape(-1, 3)
    transformed = rgb_array @ matrices[cb_type].T
    
    # Ensure values stay in [0, 1] range
    transformed = np.clip(transformed, 0, 1)
    
    return (
        transformed.reshape(rgb_color.shape) 
        if rgb_color.ndim > 1 
        else transformed[0]
    )

def create_colorblind_palette(hex_colors, cb_type):
    """Create a colorblind-simulated version of a hex color palette."""
    rgb_colors = np.array([to_rgb(c) for c in hex_colors])
    cb_rgb = simulate_colorblindness(rgb_colors, cb_type)
    return [to_hex(c) for c in cb_rgb]

def get_colorblind_colormap(
    n_colors, cb_type, anchors=None, colorblind_friendly=False
):

    # First get the normal colormap
    _, normal_palette = get_temperature_colormap(
        n_colors, anchors, colorblind_friendly
    )
    
    # Transform it for colorblindness
    cb_palette = create_colorblind_palette(normal_palette, cb_type)
    
    # Create the colormap
    cmap_name = f"temp_colormap_{cb_type}"
    return ListedColormap(cb_palette, name=cmap_name), cb_palette

# ============================================================================
# DEMO CONFIGURATION & VISUALIZATION
# ============================================================================
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # ========================================================================
    # DEMO PARAMETERS
    # ========================================================================
    
    # Temperature range for demo
    COLDEND = -15
    WARMEND = 30
    DEMO_N_COLORS = int(WARMEND)*2+1  # Odd number centers white at 0°C
    
    # Display mode configuration
    SHOW_COLORBLIND_ANALYSIS = True   # Show accessibility analysis
    
    # ========================================================================
    # DEMO VISUALIZATION
    # ========================================================================

    if SHOW_COLORBLIND_ANALYSIS:
        # Show colorblind-friendly palette with accessibility analysis
        colorblind_palette = interpolate_luv(
            palette_anchors_colorblind, DEMO_N_COLORS
        )
        
        # Create colorblind simulations
        cb_types = [
            'normal', 'deuteranomaly', 'deuteranopia', 
            'protanopia', 'tritanopia', 'achromatopsia'
        ]
        cb_names = [
            'Normal Vision', 
            'Deuteranomaly (~5% of males)', 
            'Deuteranopia (no green)', 
            'Protanopia (no red)', 
            'Tritanopia (no blue)', 
            'Achromatopsia (no color)'
        ]

        # Create figure with accessibility analysis
        fig, axes = plt.subplots(len(cb_types), 1, figsize=(12, 8))
        fig.suptitle(
            'Colorblind-Friendly Temperature Colormap: '
            'Accessibility Analysis', 
            fontsize=14, fontweight='bold'
        )
        
        for idx, (cb_type, cb_name) in enumerate(zip(cb_types, cb_names)):
            ax = axes[idx]
            
            # Get palette for this vision type
            if cb_type == 'normal':
                palette = colorblind_palette
            else:
                palette = create_colorblind_palette(
                    colorblind_palette, cb_type
                )
            
            # Plot color bars
            for i, color_hex in enumerate(palette):
                ax.fill_between([i, i+1], 0, 1, color=color_hex)
            
            # Configure axes
            ax.get_yaxis().set_visible(False)
            ax.set_title(cb_name, fontsize=12, fontweight='bold', pad=10)
            ax.set_xlim(0, len(palette))
            ax.set_ylim(0, 1)
            
            # Add temperature tick marks only for the top plot
            if idx == 0:
                n = len(palette)
                
                # Major ticks with labels (same as before)
                major_tick_positions = [0, (n-1)/2+0.5, n]
                major_tick_labels = [f"{COLDEND}°C", "0°C", f"{WARMEND}°C"]
                
                # Minor ticks without labels (just the visual marks)
                minor_tick_positions = np.linspace(0, n, 13)  # 13 positions = 12 intervals
                
                # Set major ticks
                ax.set_xticks(major_tick_positions)
                ax.set_xticklabels(major_tick_labels, fontsize=11, fontweight='bold')
                
                # Add minor ticks
                ax.set_xticks(minor_tick_positions, minor=True)
                ax.tick_params(axis='x', which='major', length=8, width=2)
                ax.tick_params(axis='x', which='minor', length=4, width=1)
            else:
                ax.set_xticks([])
        
        plt.tight_layout()
        
    else:
        # Show only normal palette using LUV color space
        original_palette = interpolate_luv(palette_anchors, DEMO_N_COLORS)
        
        fig, ax = plt.subplots(figsize=(12, 2))
        fig.suptitle(
            'Temperature Colormap: Cold → Neutral → Warm (LUV Color Space)', 
            fontsize=14, fontweight='bold'
        )
        
        # Plot color bars
        for i, color_hex in enumerate(original_palette):
            ax.fill_between([i, i+1], 0, 1, color=color_hex)
        
        # Configure axes
        ax.get_yaxis().set_visible(False)
        ax.set_xlim(0, len(original_palette))
        ax.set_ylim(0, 1)
        
        # Add edge temperature tick marks
        n = len(original_palette)
        tick_positions = [0, (n-1)/2+0.5, n]
        tick_labels = [f"{COLDEND}°C", "0°C", f"{WARMEND}°C"]
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, fontsize=12, fontweight='bold')
        ax.tick_params(axis='x', length=10, width=2)
        
        plt.tight_layout()

    plt.show()
