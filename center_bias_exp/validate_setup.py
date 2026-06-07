#!/usr/bin/env python3
"""Quick validation script to check all systems are ready."""

import sys
sys.path.insert(0, 'src')

# Test imports
print('Testing imports...')
from config_loader import load_experiment_config, load_manifests
from geometry_utils import apply_polygon_transform
from psychopy_utils import prepare_polygon_shape, prepare_masked_image
from eyetracker_utils import connect_eyelink
from cue_grid import get_cue_positions
print('✓ All imports successful')

# Test config loading
print('\nTesting config loading...')
cfg = load_experiment_config('config/experiment_config.yaml')
print(f'✓ Config loaded with {len(cfg)} sections')

# Test manifest loading
print('\nTesting manifest loading...')
stim_df, mem_df, geom_df = load_manifests(cfg)
print(f'✓ Stimulus manifest: {len(stim_df)} trials')
print(f'✓ Memory manifest: {len(mem_df)} probes')
print(f'✓ Geometry manifest: {len(geom_df)} polygons')

# Test cue grid
print('\nTesting cue grid...')
cues = get_cue_positions()
print(f'✓ Cue grid: {len(cues)} positions')

print('\n' + '='*60)
print('🎉 All systems operational!')
print('='*60)
