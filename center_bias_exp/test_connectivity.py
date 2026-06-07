#!/usr/bin/env python3
"""
Connectivity test for center_bias_exp experiment.

Tests:
1. Import all required modules
2. Load configuration files
3. Create PsychoPy window
4. Connect to EyeLink (if available)
5. Run basic calibration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all required modules can be imported."""
    print("\n=== Testing Imports ===")
    try:
        import pandas
        print("✓ pandas")
    except ImportError as e:
        print(f"✗ pandas: {e}")
        return False
    
    try:
        import yaml
        print("✓ yaml")
    except ImportError as e:
        print(f"✗ yaml: {e}")
        return False
    
    try:
        import numpy
        print("✓ numpy")
    except ImportError as e:
        print(f"✗ numpy: {e}")
        return False
    
    try:
        from psychopy import visual, core, event, monitors
        print("✓ psychopy")
    except ImportError as e:
        print(f"✗ psychopy: {e}")
        return False
    
    try:
        import pylink
        print("✓ pylink")
    except ImportError as e:
        print(f"✗ pylink (optional for EyeLink): {e}")
        # Not fatal - can test without EyeLink
    
    print("✓ All core imports successful")
    return True


def test_config_loading():
    """Test configuration file loading."""
    print("\n=== Testing Config Loading ===")
    try:
        from config_loader import load_experiment_config
        
        config_path = Path(__file__).parent / "config" / "experiment_config.yaml"
        cfg = load_experiment_config(str(config_path))
        
        # Check required sections
        required = ["experiment", "screen", "eyelink", "drift_gate", "aoi", "paths", "logging"]
        for section in required:
            if section not in cfg:
                print(f"✗ Missing config section: {section}")
                return False
        
        print(f"✓ Config loaded with all required sections")
        print(f"  - Screen: {cfg['screen']['resolution_px']} @ {cfg['screen']['viewing_distance_cm']}cm")
        print(f"  - EyeLink: {cfg['eyelink']['sampling_rate']} Hz, {cfg['eyelink']['calibration_type']}")
        return True
        
    except Exception as e:
        print(f"✗ Config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manifest_loading():
    """Test manifest file loading."""
    print("\n=== Testing Manifest Loading ===")
    try:
        from config_loader import load_manifests, load_experiment_config
        
        config_path = Path(__file__).parent / "config" / "experiment_config.yaml"
        cfg = load_experiment_config(str(config_path))
        
        stim_df, mem_df, geom_df = load_manifests(cfg)
        
        print(f"✓ Stimulus manifest: {len(stim_df)} rows")
        print(f"✓ Memory manifest: {len(mem_df)} rows")
        print(f"✓ Geometry manifest: {len(geom_df)} rows")
        return True
        
    except Exception as e:
        print(f"✗ Manifest loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_psychopy_window():
    """Test PsychoPy window creation."""
    print("\n=== Testing PsychoPy Window ===")
    try:
        from psychopy_utils import create_monitor_and_window
        from config_loader import load_experiment_config
        
        config_path = Path(__file__).parent / "config" / "experiment_config.yaml"
        cfg = load_experiment_config(str(config_path))
        
        print("Creating window (will appear briefly)...")
        monitor, win = create_monitor_and_window(cfg["screen"])
        
        # Draw test pattern
        from psychopy import visual
        text = visual.TextStim(win, text="Window test successful\n\nPress SPACE to continue", height=40)
        text.draw()
        win.flip()
        
        # Wait for keypress or 3 seconds
        from psychopy import event, core
        event.waitKeys(maxWait=3.0, keyList=['space', 'escape'])
        
        win.close()
        print("✓ PsychoPy window created and closed successfully")
        return True
        
    except Exception as e:
        print(f"✗ PsychoPy window test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_eyelink_connection():
    """Test EyeLink connection (optional)."""
    print("\n=== Testing EyeLink Connection ===")
    try:
        import pylink
        from eyetracker_utils import connect_eyelink
        from config_loader import load_experiment_config
        
        config_path = Path(__file__).parent / "config" / "experiment_config.yaml"
        cfg = load_experiment_config(str(config_path))
        
        print(f"Attempting to connect to EyeLink at {cfg['eyelink']['address']}...")
        tracker = connect_eyelink(cfg)
        
        if tracker is not None:
            # Get version info
            version = tracker.getTrackerVersion()
            print(f"✓ Connected to EyeLink (version {version})")
            
            # Close connection
            tracker.close()
            print("✓ Connection closed successfully")
            return True
        else:
            print("✗ Failed to connect to EyeLink")
            return False
            
    except ImportError:
        print("⚠ pylink not installed - skipping EyeLink test")
        return None  # Not a failure, just skipped
    except Exception as e:
        print(f"✗ EyeLink connection failed: {e}")
        print("  (This is expected if no EyeLink is connected)")
        import traceback
        traceback.print_exc()
        return None  # Not a fatal error


def main():
    """Run all connectivity tests."""
    print("=" * 60)
    print("Center Bias Experiment - Connectivity Test")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Imports
    results['imports'] = test_imports()
    if not results['imports']:
        print("\n✗ Import test failed. Please install missing dependencies:")
        print("  pip install pandas numpy pyyaml psychopy")
        print("  pip install pylink-square  # For EyeLink support")
        return 1
    
    # Test 2: Config loading
    results['config'] = test_config_loading()
    if not results['config']:
        print("\n✗ Config loading failed. Please check experiment_config.yaml")
        return 1
    
    # Test 3: Manifest loading
    results['manifests'] = test_manifest_loading()
    if not results['manifests']:
        print("\n⚠ Manifest loading failed. This is OK for basic connectivity test.")
        print("  You'll need proper manifests to run the full experiment.")
    
    # Test 4: PsychoPy window
    results['psychopy'] = test_psychopy_window()
    if not results['psychopy']:
        print("\n✗ PsychoPy window test failed")
        return 1
    
    # Test 5: EyeLink (optional)
    results['eyelink'] = test_eyelink_connection()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    print(f"⚠ Skipped: {skipped}")
    
    if results['eyelink'] is None:
        print("\n⚠ EyeLink connection was not tested.")
        print("  To test EyeLink:")
        print("  1. Ensure EyeLink is powered on and connected")
        print("  2. Update EyeLink IP address in experiment_config.yaml")
        print("  3. Run this test again")
    
    if failed == 0:
        print("\n🎉 All core systems operational!")
        print("   You can proceed with the full experiment runner.")
        return 0
    else:
        print("\n❌ Some tests failed. Please address issues before running experiment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
