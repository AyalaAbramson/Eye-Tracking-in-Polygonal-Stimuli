"""
Preview script to visualize Block 1 stimuli with polygon apertures.
Shows how the masked images will appear in the actual experiment.

The approach is:
1. Load the original image (e.g., 1920x1080)
2. Scale the polygon to fit INSIDE the image
3. Mask the image with the polygon
4. Upscale the masked result to target display size
"""

import pandas as pd
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import os

def load_polygon_vertices(json_path):
    """Load polygon vertices from JSON file."""
    with open(json_path, 'r') as f:
        poly_data = json.load(f)
    
    # Handle two formats: vertices_xy (standard) or theta (consolidated)
    if 'vertices_xy' in poly_data:
        vertices = np.array(poly_data['vertices_xy'])
    elif 'theta' in poly_data:
        # Consolidated format: theta values define radial polygon
        thetas = poly_data['theta']
        n = len(thetas)
        area = poly_data.get('area', 550)
        
        # Calculate base radius from area
        base_r = np.sqrt(area / np.pi) * 1.2
        mean_theta = np.mean(thetas)
        
        vertices = []
        for i, theta in enumerate(thetas):
            angle = 2 * np.pi * i / n
            local_r = base_r * (theta / mean_theta)
            x = local_r * np.cos(angle)
            y = local_r * np.sin(angle)
            vertices.append([x, y])
        vertices = np.array(vertices)
    else:
        return None
    
    return vertices

def normalize_vertices(vertices):
    """Normalize polygon vertices to be centered at origin with max dimension = 1."""
    min_xy = vertices.min(axis=0)
    max_xy = vertices.max(axis=0)
    current_max_dim = max(max_xy[0] - min_xy[0], max_xy[1] - min_xy[1])
    
    if current_max_dim > 0:
        normalize_scale = 1.0 / current_max_dim
    else:
        normalize_scale = 1.0
    
    center_x = (min_xy[0] + max_xy[0]) / 2
    center_y = (min_xy[1] + max_xy[1]) / 2
    
    normalized = np.array([
        [(x - center_x) * normalize_scale, (y - center_y) * normalize_scale]
        for x, y in vertices
    ])
    return normalized

def create_masked_image(img, vertices, display_size):
    """
    Create a masked image where the polygon fits INSIDE the image.
    
    1. Scale polygon to fit inside original image
    2. Mask the image
    3. Crop and resize to display_size
    """
    img_width, img_height = img.size
    
    # Normalize vertices to unit scale (max dim = 1)
    norm_verts = normalize_vertices(vertices)
    
    # Scale polygon to fit inside image (use smaller dimension, with larger margin)
    # Use 80% to ensure elongated polygons don't get cut at edges
    img_min_dim = min(img_width, img_height)
    margin_factor = 0.80  # 20% margin to ensure all edges visible
    poly_scale = img_min_dim * margin_factor
    
    # Image center
    img_cx, img_cy = img_width / 2, img_height / 2
    
    # Create mask at image resolution
    mask_img = Image.new('L', (img_width, img_height), 0)
    draw = ImageDraw.Draw(mask_img)
    
    # Transform vertices to image coordinates
    mask_vertices = []
    for x, y in norm_verts:
        img_x = img_cx + x * poly_scale
        img_y = img_cy - y * poly_scale  # Flip y
        mask_vertices.append((img_x, img_y))
    
    # Draw filled polygon
    draw.polygon(mask_vertices, fill=255)
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Apply mask to image
    img_rgba = img.convert('RGBA')
    mask_array = np.array(mask_img)
    img_array = np.array(img_rgba)
    img_array[:, :, 3] = mask_array
    
    masked_pil = Image.fromarray(img_array, 'RGBA')
    
    # Calculate bounding box of polygon in image coords
    verts_img = np.array(mask_vertices)
    min_x, min_y = verts_img.min(axis=0)
    max_x, max_y = verts_img.max(axis=0)
    
    # Add padding
    pad = 15  # Increased padding
    bbox = (
        max(0, int(min_x) - pad),
        max(0, int(min_y) - pad),
        min(img_width, int(max_x) + pad),
        min(img_height, int(max_y) + pad)
    )
    
    # Crop to polygon area
    cropped = masked_pil.crop(bbox)
    
    # Resize to display size (maintain aspect ratio)
    cropped_w, cropped_h = cropped.size
    scale = display_size / max(cropped_w, cropped_h)
    new_size = (int(cropped_w * scale), int(cropped_h * scale))
    resized = cropped.resize(new_size, Image.LANCZOS)
    
    # Place on grey background
    result = Image.new('RGBA', (display_size, display_size), (128, 128, 128, 255))
    paste_x = (display_size - new_size[0]) // 2
    paste_y = (display_size - new_size[1]) // 2
    result.paste(resized, (paste_x, paste_y), resized)
    
    return np.array(result.convert('RGB'))

# Load manifest
df = pd.read_csv('manifests/stimulus_manifest_partA.csv')
block1 = df[df['mini_block'] == 1]  # All 39 trials of block 1

base_path = '.'
display_size = 300  # Smaller size to fit more trials

fig, axes = plt.subplots(5, 8, figsize=(24, 15))
axes = axes.flatten()

for idx, (_, row) in enumerate(block1.iterrows()):
    ax = axes[idx]
    
    # Load polygon JSON
    json_path = os.path.join(base_path, row['polygon_json_path'])
    vertices = load_polygon_vertices(json_path)
    
    if vertices is None:
        ax.set_facecolor('red')
        ax.set_title(f'T{idx+1}: MISSING VERTICES', fontsize=8)
        ax.axis('off')
        continue
    
    # Load and mask image
    if row['trial_type'] == 'image' and pd.notna(row['image_path']):
        img_path = os.path.join(base_path, row['image_path'])
        if os.path.exists(img_path):
            img = Image.open(img_path).convert('RGB')
            masked_img = create_masked_image(img, vertices, display_size)
            ax.imshow(masked_img)
        else:
            ax.set_facecolor('gray')
    else:
        # Empty trial - show polygon outline on grey with black fill
        grey_bg = np.full((display_size, display_size, 3), 128, dtype=np.uint8)
        ax.imshow(grey_bg)
        
        # Draw polygon - use full display size, filled with black
        norm_verts = normalize_vertices(vertices)
        half = display_size / 2
        scale = display_size * 0.95 / 2  # 95% of display size for maximum visibility
        outline_verts = [(x * scale + half, half - y * scale) for x, y in norm_verts]
        # Black fill with white outline
        polygon = MplPolygon(outline_verts, fill=True, facecolor='black', edgecolor='white', linewidth=2)
        ax.add_patch(polygon)
    
    pid = row['polygon_id']
    ttype = row['trial_type']
    ax.set_title(f'T{idx+1}: {pid}\n{ttype}', fontsize=8)
    ax.axis('off')

plt.suptitle('Block 1 - All 39 Trials (Polygon fits INSIDE image, then upscaled)', fontsize=14)
plt.tight_layout()
plt.savefig('block1_preview.png', dpi=150, facecolor='#808080')
print('Saved to block1_preview.png')
plt.close()
