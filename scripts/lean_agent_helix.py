#!/usr/bin/env python3
# /// script
# dependencies = [
#   "matplotlib",
#   "pillow",
#   "numpy",
#   "fonttools",
# ]
# ///

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

# Helix parameter
t = np.linspace(0, 10 * np.pi, 800)

# Elliptical cross-section
a = 2.5
b = 0.7

# Axes (time, interaction, spatial)
x = t
y = a * np.sin(t)
z = b * np.cos(t)

fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='3d')

# --- Build colored segments between extrema ---

t_min, t_max = t.min(), t.max()
k_vals = np.arange(-10, 20)

# Maxima at t = pi/2 + 2kπ (LLM), minima at t = 3pi/2 + 2kπ (Lean)
t_maxima = np.pi/2 + 2 * np.pi * k_vals
t_minima = 3*np.pi/2 + 2 * np.pi * k_vals

t_maxima = t_maxima[(t_maxima >= t_min) & (t_maxima <= t_max)]
t_minima = t_minima[(t_minima >= t_min) & (t_minima <= t_max)]

# Combine & sort extrema
t_ext = np.concatenate([t_maxima, t_minima])
labels = (["max"] * len(t_maxima)) + (["min"] * len(t_minima))
# sort by t_ext
order = np.argsort(t_ext)
t_ext = t_ext[order]
labels = np.array(labels)[order]

# Colors
color_lean_to_llm = "tab:orange"
color_llm_to_lean = "tab:blue"

# Plot segments between successive extrema with two alternating colors
for i in range(len(t_ext) - 1):
    t_start, t_end = t_ext[i], t_ext[i+1]
    mask = (t >= t_start) & (t <= t_end)
    if labels[i] == "min" and labels[i+1] == "max":
        # Lean -> LLM
        c = color_lean_to_llm
    elif labels[i] == "max" and labels[i+1] == "min":
        # LLM -> Lean
        c = color_llm_to_lean
    else:
        # Shouldn't really happen, but fall back to one color
        c = "gray"
    ax.plot(x[mask], y[mask], z[mask], linewidth=2, color=c)

# --- Mark extrema ---

# Coordinates for maxima (LLM) and minima (Lean)
x_max = t_maxima
y_max = a * np.sin(t_maxima)
z_max = b * np.cos(t_maxima)

x_min = t_minima
y_min = a * np.sin(t_minima)
z_min = b * np.cos(t_minima)

# Lean toolcalls: ∀ on the helix
forall = "∀"
for i, (xn, yn, zn) in enumerate(zip(x_min, y_min, z_min)):
    ax.text(xn, yn, zn, forall, fontsize=16, ha='center', va='center')
    # Add checkmark next to the last forall, X for all others
    if i == len(x_min) - 1:
        ax.text(xn + 1.5, yn, zn, "✓", fontsize=24, ha='left', va='center')
    else:
        ax.text(xn + 1.5, yn, zn, "✗", fontsize=24, ha='left', va='center')

# LLM toolcalls: use Unicode symbol since matplotlib can't handle color emoji fonts
for xm, ym, zm in zip(x_max, y_max, z_max):
    ax.text(xm, ym, zm, "◉", fontsize=32, ha='center', va='center')

# Arrow along time at far right
arrow_x0 = t_max - 24.0  # Start further back so arrow extends to the right
arrow_y0 = 0
arrow_z0 = 0

ax.quiver(
    arrow_x0, arrow_y0, arrow_z0,
    1.0, 0.0, 0.0,
    length=16.0,
    arrow_length_ratio=0.05,
    color='black'
)

# Kill ticks and tick labels
ax.set_xticks([])
ax.set_yticks([])
ax.set_zticks([])
ax.set_xticklabels([])
ax.set_yticklabels([])
ax.set_zticklabels([])
ax.set_zlabel("")

# Set x-axis label to "time"
ax.set_xlabel("time→", fontsize=11)

# Add legend
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

legend_elements = [
    Patch(facecolor='tab:orange', label='Error message'),
    Patch(facecolor='tab:blue', label='LLM completion'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='black', markersize=10, label='◉ LLM'),
    Line2D([0], [0], marker='$∀$', color='w', markerfacecolor='black', markersize=12, label='∀ Proof checker')
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=9)

# Title
ax.set_title("MVP of lean agent (its a loop)")

plt.tight_layout()

# Save to book static directory
output_path = "./book/static/img/lean-agent-helix.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"Saved figure to {output_path}")
