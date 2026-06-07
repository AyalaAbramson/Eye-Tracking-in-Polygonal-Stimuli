"""Debug script to understand theta format in consolidated polygons."""
import json
import numpy as np

# Load
with open('data/raw/stimuli/polygons/baseline_asymmetric_consolidated.json') as f:
    asym = json.load(f)

thetas = asym['theta']
area = asym['area']
n = len(thetas)

# Method: Treat theta as angular span for each vertex sector
# Normalize to 360 degrees for a closed polygon
theta_sum = sum(thetas)
scale = 360.0 / theta_sum

# Calculate radius from area for a regular n-gon approximation
# A = 0.5 * n * r^2 * sin(2*pi/n)
r = np.sqrt(2 * area / (n * np.sin(2*np.pi/n)))
print(f'Estimated radius: {r:.2f}')

# Generate vertices using cumulative scaled angles
vertices = []
cum_angle = 0
for theta in thetas:
    rad = np.radians(cum_angle)
    x = r * np.cos(rad)
    y = r * np.sin(rad)
    vertices.append([x, y])
    cum_angle += theta * scale

verts = np.array(vertices)
print(f'Final cumulative angle: {cum_angle:.1f}')

# Check if centers match
com = verts.mean(axis=0)
print(f'Computed COM: {com}')
print(f'Expected COM: {asym["center_positions"]["center_of_mass"]}')

# Try different interpretation: theta as the radius multiplier for each angle
# Vertices at equal angular intervals but varying radii
vertices2 = []
base_r = np.sqrt(area / np.pi)  # Rough radius from area
for i, theta in enumerate(thetas):
    angle = 2 * np.pi * i / n
    # Use theta as a scaling factor for radius
    local_r = base_r * (theta / np.mean(thetas))
    x = local_r * np.cos(angle)
    y = local_r * np.sin(angle)
    vertices2.append([x, y])

verts2 = np.array(vertices2)
com2 = verts2.mean(axis=0)
print(f'\nMethod 2 - varying radius:')
print(f'Computed COM: {com2}')
print(f'Expected COM: {asym["center_positions"]["center_of_mass"]}')
