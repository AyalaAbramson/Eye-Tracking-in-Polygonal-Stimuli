"""
Visualize all polygons from the polygons folder.

Creates a grid plot showing all polygon shapes with their filenames,
making it easy to identify which polygon is which.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import PatchCollection
import numpy as np


def load_polygon(json_path: Path) -> dict:
    """Load polygon data from JSON file."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Handle consolidated format (theta angles) vs standard format (vertices_xy)
    if 'vertices_xy' not in data and 'theta' in data:
        # These consolidated files use theta as angular spans per vertex
        # The polygon is constructed with vertices at varying radii
        thetas = data['theta']
        n = len(thetas)
        area = data.get('area', 550)
        
        # Calculate base radius from area
        base_r = np.sqrt(area / np.pi) * 1.2
        
        # Method: Place vertices at equal angular intervals
        # but vary the radius based on theta values
        # This creates polygons where theta controls the "bulge" at each vertex
        mean_theta = np.mean(thetas)
        
        vertices = []
        for i, theta in enumerate(thetas):
            # Equal angular spacing around the circle
            angle = 2 * np.pi * i / n
            # Radius varies with theta (larger theta = larger radius)
            local_r = base_r * (theta / mean_theta)
            x = local_r * np.cos(angle)
            y = local_r * np.sin(angle)
            vertices.append([x, y])
        
        data['vertices_xy'] = vertices
        
        # Also convert center_positions to centers format if present
        if 'center_positions' in data and 'centers' not in data:
            cp = data['center_positions']
            data['centers'] = {
                'COM': cp.get('center_of_mass'),
                'CHC': cp.get('convex_hull_center'),
                'BBC': cp.get('bounding_box_center'),
                'ICC': cp.get('inscribed_circle_center')
            }
    
    return data


def plot_polygon(ax, polygon_data: dict, title: str):
    """Plot a single polygon on the given axes."""
    vertices = np.array(polygon_data['vertices_xy'])
    
    # Close the polygon by appending the first vertex
    vertices_closed = np.vstack([vertices, vertices[0]])
    
    # Plot the polygon
    ax.fill(vertices_closed[:, 0], vertices_closed[:, 1], 
            alpha=0.3, color='blue', edgecolor='blue', linewidth=2)
    
    # Plot centers if available
    centers = polygon_data.get('centers', {})
    center_colors = {
        'COM': 'red',
        'BBC': 'green', 
        'CHC': 'orange',
        'ICC': 'purple'
    }
    
    for center_name, coords in centers.items():
        if center_name in center_colors and coords is not None:
            ax.scatter(coords[0], coords[1], color=center_colors[center_name], 
                      s=50, marker='o', label=center_name, zorder=5)
    
    # Set equal aspect ratio and title
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Add legend if centers exist
    if centers:
        ax.legend(fontsize=6, loc='upper right')


def main():
    # Path to polygons folder
    polygons_dir = Path('data/raw/stimuli/polygons')
    
    # Get all JSON files (exclude .DS_Store and other system files)
    json_files = sorted([f for f in polygons_dir.glob('*.json') 
                        if not f.name.startswith('.')])
    
    print(f"Found {len(json_files)} polygon files:")
    for f in json_files:
        print(f"  - {f.name}")
    
    # Calculate grid dimensions
    n_polygons = len(json_files)
    n_cols = 6
    n_rows = (n_polygons + n_cols - 1) // n_cols
    
    # Create figure
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 3 * n_rows))
    axes = axes.flatten() if n_polygons > 1 else [axes]
    
    # Plot each polygon
    for idx, json_path in enumerate(json_files):
        try:
            polygon_data = load_polygon(json_path)
            title = json_path.stem  # Filename without extension
            plot_polygon(axes[idx], polygon_data, title)
        except Exception as e:
            print(f"Error loading {json_path.name}: {e}")
            axes[idx].set_title(f"{json_path.stem}\n(ERROR)", fontsize=8, color='red')
    
    # Hide empty subplots
    for idx in range(n_polygons, len(axes)):
        axes[idx].axis('off')
    
    plt.tight_layout()
    
    # Save to file
    output_path = Path('polygon_visualization.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization to: {output_path}")
    
    # Also show the plot
    plt.show()


if __name__ == '__main__':
    main()
