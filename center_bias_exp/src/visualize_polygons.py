"""
Polygon Visualization and Verification Tool

This script displays all 27 polygons on your actual experimental setup
to visually verify:
1. No polygon clipping at edges
2. Center markers are correctly positioned
3. Polygon scaling is appropriate

Usage:
    # Show all polygons sequentially
    python src/visualize_polygons.py

    # Show specific polygon
    python src/visualize_polygons.py --polygon allfar_concave_01

    # Save screenshots for documentation
    python src/visualize_polygons.py --save-screenshots

Controls:
    SPACE: Next polygon
    BACKSPACE: Previous polygon
    S: Save screenshot of current polygon
    C: Toggle center markers
    B: Toggle bounding box
    ESC: Quit

Output:
    - Visual display of polygons
    - Optional screenshots in outputs/polygon_verification/
    - verification_report.txt with polygon dimensions

Author: Eye Tracking Lab
Date: 2026-01-17
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import json

import numpy as np
from psychopy import visual, core, event

# Import your utilities
sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_experiment_config
from psychopy_utils import create_monitor_and_window, prepare_polygon_shape
from geometry_utils import pix2deg_x, pix2deg_y


class PolygonVisualizer:
    """Interactive polygon visualization tool."""

    def __init__(self, config_path: str, save_screenshots: bool = False):
        # Load config
        self.cfg = load_experiment_config(config_path)
        self.screen_cfg = self.cfg['screen']

        # Create window
        self.monitor, self.win = create_monitor_and_window(self.screen_cfg)

        # Visualization settings
        self.show_centers = True
        self.show_bbox = True
        self.save_screenshots = save_screenshots

        # Screenshot directory
        if save_screenshots:
            self.screenshot_dir = Path('outputs/polygon_verification')
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Load polygon list
        self.polygon_dir = Path(self.cfg['paths']['stimuli']['polygons'])
        self.polygon_files = sorted(self.polygon_dir.glob('*.json'))

        # Filter out hidden files
        self.polygon_files = [f for f in self.polygon_files if not f.name.startswith('.')]

        print(f"Found {len(self.polygon_files)} polygon files")

        # Aperture scale (from experiment)
        self.aperture_scale = 1987

        # Current polygon index
        self.current_idx = 0

        # Verification log
        self.verification_log = []

    def draw_crosshair(self, x, y, size=20, color='white'):
        """Draw a crosshair marker."""
        h_line = visual.Line(
            self.win,
            start=(-size, 0),
            end=(size, 0),
            pos=(x, y),
            lineColor=color,
            lineWidth=2
        )
        v_line = visual.Line(
            self.win,
            start=(0, -size),
            end=(0, size),
            pos=(x, y),
            lineColor=color,
            lineWidth=2
        )
        h_line.draw()
        v_line.draw()

    def draw_polygon_centers(self, polygon_json: Dict):
        """Draw center markers if they exist."""
        if 'centers' not in polygon_json:
            return

        centers = polygon_json['centers']
        colors = {
            'COM': 'red',
            'BBC': 'blue',
            'CHC': 'green',
            'ICC': 'yellow'
        }

        # Scale centers to display size
        for center_type, (x, y) in centers.items():
            # Scale from canonical to display coordinates
            # Canonical coordinates are centered at (0, 0)
            # Apply same scaling as polygon vertices

            # Get polygon vertices to determine scaling
            if 'vertices_xy' in polygon_json:
                vertices = np.array(polygon_json['vertices_xy'])
            elif 'theta' in polygon_json:
                # Skip theta format for now
                continue
            else:
                continue

            # Calculate normalization (same as prepare_polygon_shape)
            min_xy = vertices.min(axis=0)
            max_xy = vertices.max(axis=0)
            current_width = max_xy[0] - min_xy[0]
            current_height = max_xy[1] - min_xy[1]
            current_max_dim = max(current_width, current_height)

            if current_max_dim > 0:
                normalize_scale = self.aperture_scale / current_max_dim
            else:
                normalize_scale = self.aperture_scale

            # Center the canonical coordinates
            center_x_canon = (min_xy[0] + max_xy[0]) / 2
            center_y_canon = (min_xy[1] + max_xy[1]) / 2

            # Scale center position
            x_display = (x - center_x_canon) * normalize_scale
            y_display = (y - center_y_canon) * normalize_scale

            # Draw marker
            if center_type in colors:
                self.draw_crosshair(x_display, y_display, size=30, color=colors[center_type])

                # Label
                label = visual.TextStim(
                    self.win,
                    text=center_type,
                    pos=(x_display, y_display - 50),
                    height=20,
                    color=colors[center_type]
                )
                label.draw()

    def visualize_polygon(self, polygon_path: Path):
        """Display a single polygon with verification info."""
        self.win.flip()  # Clear screen

        # Load polygon JSON
        with open(polygon_path, 'r') as f:
            polygon_json = json.load(f)

        # Prepare polygon shape
        try:
            polygon_shape = prepare_polygon_shape(
                self.win,
                str(polygon_path),
                aperture_scale_factor=self.aperture_scale
            )
        except Exception as e:
            print(f"ERROR loading polygon {polygon_path.name}: {e}")
            return

        # Draw polygon outline
        polygon_shape.draw()

        # Draw centers if enabled
        if self.show_centers:
            self.draw_polygon_centers(polygon_json)

        # Draw bounding box if enabled
        if self.show_bbox:
            vertices = polygon_shape.vertices
            if vertices is not None and len(vertices) > 0:
                vertices_array = np.array(vertices)
                min_x, min_y = vertices_array.min(axis=0)
                max_x, max_y = vertices_array.max(axis=0)

                # Draw rectangle
                bbox = visual.Rect(
                    self.win,
                    width=max_x - min_x,
                    height=max_y - min_y,
                    pos=((max_x + min_x)/2, (max_y + min_y)/2),
                    lineColor='cyan',
                    lineWidth=1,
                    fillColor=None
                )
                bbox.draw()

        # Draw screen boundary for reference (red line at 95% of screen)
        screen_width = self.screen_cfg['resolution_px'][0]
        screen_height = self.screen_cfg['resolution_px'][1]

        safe_zone_pct = 0.95
        safe_width = screen_width * safe_zone_pct
        safe_height = screen_height * safe_zone_pct

        # Convert to PsychoPy coordinates (centered)
        safe_w_psychopy = safe_width / 2
        safe_h_psychopy = safe_height / 2

        # Draw boundary rectangle
        boundary = visual.Rect(
            self.win,
            width=safe_width - 40,  # Offset to make visible
            height=safe_height - 40,
            lineColor='red',
            lineWidth=2,
            fillColor=None
        )
        boundary.draw()

        # Display info text
        polygon_id = polygon_path.stem
        polygon_case = polygon_json.get('case', polygon_json.get('case_name', 'UNKNOWN'))

        info_text = f"""
Polygon: {polygon_id}
Case: {polygon_case}
Aperture Scale: {self.aperture_scale} px

[{self.current_idx + 1}/{len(self.polygon_files)}]

Controls:
  SPACE: Next | BACKSPACE: Previous
  C: Toggle centers | B: Toggle bbox
  S: Screenshot | ESC: Quit
"""

        info = visual.TextStim(
            self.win,
            text=info_text,
            pos=(-screen_width/2 + 200, screen_height/2 - 100),
            height=18,
            color='white',
            anchorHoriz='left',
            anchorVert='top'
        )
        info.draw()

        # Draw screen center crosshair
        self.draw_crosshair(0, 0, size=40, color='gray')

        # Flip to display
        self.win.flip()

        # Check for clipping
        vertices = polygon_shape.vertices
        if vertices is not None:
            vertices_array = np.array(vertices)
            max_extent = np.abs(vertices_array).max()

            screen_half_min = min(screen_width, screen_height) / 2
            is_clipped = max_extent > screen_half_min * safe_zone_pct

            # Log verification
            self.verification_log.append({
                'polygon_id': polygon_id,
                'polygon_case': polygon_case,
                'max_extent_px': max_extent,
                'screen_safe_bound_px': screen_half_min * safe_zone_pct,
                'is_clipped': is_clipped,
                'max_extent_deg': pix2deg_x(max_extent, self.screen_cfg)
            })

            if is_clipped:
                print(f"WARNING: {polygon_id} may be clipped! Max extent: {max_extent:.1f} px")

    def run_interactive(self):
        """Run interactive visualization loop."""
        print("\n" + "="*80)
        print("POLYGON VISUALIZATION TOOL")
        print("="*80)
        print("\nControls:")
        print("  SPACE: Next polygon")
        print("  BACKSPACE: Previous polygon")
        print("  C: Toggle center markers")
        print("  B: Toggle bounding box")
        print("  S: Save screenshot")
        print("  ESC: Quit")
        print("\nPress any key to start...")

        # Initial instructions
        self.win.flip()
        event.waitKeys()

        running = True

        while running:
            # Display current polygon
            polygon_path = self.polygon_files[self.current_idx]
            self.visualize_polygon(polygon_path)

            # Wait for input
            keys = event.waitKeys()

            if 'escape' in keys:
                running = False

            elif 'space' in keys:
                # Next polygon
                self.current_idx = (self.current_idx + 1) % len(self.polygon_files)

            elif 'backspace' in keys:
                # Previous polygon
                self.current_idx = (self.current_idx - 1) % len(self.polygon_files)

            elif 'c' in keys:
                # Toggle centers
                self.show_centers = not self.show_centers
                print(f"Centers: {'ON' if self.show_centers else 'OFF'}")

            elif 'b' in keys:
                # Toggle bbox
                self.show_bbox = not self.show_bbox
                print(f"Bounding box: {'ON' if self.show_bbox else 'OFF'}")

            elif 's' in keys:
                # Save screenshot
                if self.save_screenshots:
                    screenshot_path = self.screenshot_dir / f"{polygon_path.stem}.png"
                    self.win.getMovieFrame()  # Capture frame
                    self.win.saveMovieFrames(str(screenshot_path))
                    print(f"Screenshot saved: {screenshot_path}")
                else:
                    print("Screenshots not enabled (use --save-screenshots)")

        # Cleanup
        self.win.close()

    def generate_verification_report(self, output_path: Path):
        """Generate verification report with polygon dimensions."""
        report = f"""
{'='*100}
POLYGON VERIFICATION REPORT
Generated: {core.getTime()}
{'='*100}

SUMMARY
-------
Total polygons checked: {len(self.verification_log)}
Polygons with clipping: {sum(1 for p in self.verification_log if p['is_clipped'])}

POLYGON DETAILS
---------------
{'Polygon ID':<35} {'Case':<30} {'Max Extent (px)':<15} {'Max Extent (°)':<15} {'Clipped?'}
{'-'*100}
"""

        for entry in self.verification_log:
            clipped_str = 'YES ⚠️' if entry['is_clipped'] else 'NO ✓'
            report += f"{entry['polygon_id']:<35} {entry['polygon_case']:<30} "
            report += f"{entry['max_extent_px']:<15.1f} {entry['max_extent_deg']:<15.2f} {clipped_str}\n"

        report += f"\n{'='*100}\n"
        report += f"END OF REPORT\n"
        report += f"{'='*100}\n"

        with open(output_path, 'w') as f:
            f.write(report)

        print(f"\nVerification report saved to: {output_path}")
        print(report)


def main():
    parser = argparse.ArgumentParser(
        description='Visualize and verify polygon stimuli'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/experiment_config.yaml',
        help='Path to experiment config (default: config/experiment_config.yaml)'
    )
    parser.add_argument(
        '--polygon',
        type=str,
        help='Show specific polygon only (e.g., allfar_concave_01)'
    )
    parser.add_argument(
        '--save-screenshots',
        action='store_true',
        help='Save screenshots of all polygons'
    )

    args = parser.parse_args()

    # Create visualizer
    visualizer = PolygonVisualizer(args.config, args.save_screenshots)

    # Filter to specific polygon if requested
    if args.polygon:
        visualizer.polygon_files = [f for f in visualizer.polygon_files
                                    if args.polygon in f.stem]
        if not visualizer.polygon_files:
            print(f"ERROR: Polygon not found: {args.polygon}")
            sys.exit(1)

    # Run interactive visualization
    visualizer.run_interactive()

    # Generate verification report
    report_path = Path('outputs/polygon_verification/verification_report.txt')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    visualizer.generate_verification_report(report_path)

    print("\nVisualization complete!")


if __name__ == '__main__':
    main()
