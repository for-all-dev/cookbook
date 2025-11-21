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
from mpl_toolkits.mplot3d import proj3d
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image, ImageDraw, ImageFont

# --- helper: make an emoji image (swap font to emoji-capable font locally) ---
def make_emoji_image(char="🤖", size=64):
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    try:
        # On your machine, point this to an emoji font (e.g. Noto Color Emoji, Apple Color Emoji)
        font = ImageFont.truetype("DejaVuSans.ttf", size=int(size*0.8))
    except Exception:
        font = ImageFont.load_default()
    # Use textbbox instead of deprecated textsize
    bbox = draw.textbbox((0, 0), char, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((size - w) / 2, (size - h) / 2), char, font=font, fill=(0, 0, 0, 255))
    return img

emoji_img = make_emoji_image("🤖", size=64)

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
for xn, yn, zn in zip(x_min, y_min, z_min):
    ax.text(xn, yn, zn, forall, fontsize=16, ha='center', va='center')

# LLM toolcalls: robot emoji images projected into 2D
oi = OffsetImage(emoji_img, zoom=0.3)
for xm, ym, zm in zip(x_max, y_max, z_max):
    x2, y2, _ = proj3d.proj_transform(xm, ym, zm, ax.get_proj())
    ab = AnnotationBbox(oi, (x2, y2), xycoords='data', frameon=False)
    ax.add_artist(ab)

# --- Tiny arrowhead at far end of helix (along tangent) ---

# Approximate tangent at end using last two points
x_end, y_end, z_end = x[-1], y[-1], z[-1]
dx = x[-1] - x[-2]
dy = y[-1] - y[-2]
dz = z[-1] - z[-2]
norm = np.sqrt(dx**2 + dy**2 + dz**2)
dx, dy, dz = dx / norm, dy / norm, dz / norm

ax.quiver(
    x_end, y_end, z_end,
    dx, dy, dz,
    length=1.5,
    arrow_length_ratio=0.6,
    color="black"
)

# Kill ticks, tick labels, and z-axis label
ax.set_xticks([])
ax.set_yticks([])
ax.set_zticks([])
ax.set_xticklabels([])
ax.set_yticklabels([])
ax.set_zticklabels([])
ax.set_zlabel("")

# Title
ax.set_title("MVP of lean agent (its a loop)")

plt.tight_layout()

# Save to book static directory
output_path = "./book/static/lean-agent-helix.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"Saved figure to {output_path}")

plt.show()
