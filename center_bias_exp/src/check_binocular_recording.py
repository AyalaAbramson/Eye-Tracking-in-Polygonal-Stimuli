"""
Check if EDF file contains binocular (both eyes) data.

This script reads an EDF or ASC file and verifies that data from
both left and right eyes is being recorded.

Usage:
    python src/check_binocular_recording.py <path_to_edf_or_asc>
"""

import sys
import subprocess
from pathlib import Path


def check_asc_binocular(asc_path):
    """
    Check if ASC file contains binocular data.

    Parameters
    ----------
    asc_path : Path
        Path to ASC file

    Returns
    -------
    dict
        Dictionary with keys:
        - has_left: bool
        - has_right: bool
        - is_binocular: bool
        - sample_count: int
        - left_sample_count: int
        - right_sample_count: int
    """
    print(f"Checking ASC file: {asc_path}")

    has_left = False
    has_right = False
    sample_count = 0
    left_sample_count = 0
    right_sample_count = 0

    with open(asc_path, 'r') as f:
        for line in f:
            # Check SAMPLE lines (numeric timestamps)
            if line[0].isdigit():
                parts = line.strip().split()
                if len(parts) >= 7:  # Should have timestamp + gaze data
                    sample_count += 1

                    # Binocular format: timestamp gaze_lx gaze_ly pupil_l ... gaze_rx gaze_ry pupil_r ...
                    # Check if we have valid (non-missing) data for each eye
                    # Missing data is typically represented as "." or very large numbers

                    # Left eye (columns 1-3: x, y, pupil)
                    if len(parts) > 3:
                        left_x, left_y = parts[1], parts[2]
                        if left_x != '.' and left_y != '.' and left_x.replace('-','').replace('.','').isdigit():
                            has_left = True
                            left_sample_count += 1

                    # Right eye (columns typically around 4-6 or later depending on format)
                    # In binocular mode, right eye data follows left eye data
                    if len(parts) > 6:
                        # Try to find right eye data (usually after left eye data)
                        # Format varies, but typically: timestamp L_x L_y L_pupil ... R_x R_y R_pupil
                        right_x, right_y = parts[4], parts[5]
                        if right_x != '.' and right_y != '.' and right_x.replace('-','').replace('.','').isdigit():
                            has_right = True
                            right_sample_count += 1

                # Only check first 1000 samples for speed
                if sample_count > 1000:
                    break

    is_binocular = has_left and has_right

    return {
        'has_left': has_left,
        'has_right': has_right,
        'is_binocular': is_binocular,
        'sample_count': sample_count,
        'left_sample_count': left_sample_count,
        'right_sample_count': right_sample_count
    }


def check_edf_binocular(edf_path):
    """
    Check if EDF file contains binocular data.

    First converts EDF to ASC using edf2asc, then checks the ASC file.

    Parameters
    ----------
    edf_path : Path
        Path to EDF file

    Returns
    -------
    dict
        Same as check_asc_binocular
    """
    print(f"Checking EDF file: {edf_path}")

    # Convert to ASC
    asc_path = edf_path.with_suffix('.asc')

    if not asc_path.exists():
        print(f"Converting EDF to ASC: {edf_path} -> {asc_path}")
        try:
            # Run edf2asc - note: it often returns non-zero exit codes even on success
            result = subprocess.run(['edf2asc', str(edf_path)],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)

            # Check if ASC was actually created (better indicator than exit code)
            if not asc_path.exists():
                print(f"ERROR: edf2asc failed to create ASC file")
                sys.exit(1)
            else:
                print(f"Conversion successful (ASC file created)")

        except FileNotFoundError:
            print("ERROR: edf2asc not found. Please install SR Research EDF utilities.")
            print("Download from: https://www.sr-research.com/support/")
            sys.exit(1)
    else:
        print(f"Using existing ASC file: {asc_path}")

    return check_asc_binocular(asc_path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/check_binocular_recording.py <path_to_edf_or_asc>")
        print("\nExample:")
        print("  python src/check_binocular_recording.py data/raw/participant_P01/part_A/session_TIMESTAMP/edf/P01A.edf")
        print("\nOr use wildcard (will check first match):")
        print("  python src/check_binocular_recording.py \"data/raw/participant_P01/part_A/session_*/edf/*.edf\"")
        sys.exit(1)

    file_pattern = sys.argv[1]

    # Handle wildcards using glob
    import glob
    file_path = None

    if '*' in file_pattern or '?' in file_pattern:
        # Expand wildcard
        matches = glob.glob(file_pattern)
        if not matches:
            print(f"ERROR: No files found matching pattern: {file_pattern}")
            sys.exit(1)
        file_path = Path(matches[0])
        if len(matches) > 1:
            print(f"Found {len(matches)} matching files, checking first: {file_path.name}")
    else:
        file_path = Path(file_pattern)

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    # Check file type and process
    if file_path.suffix.lower() == '.edf':
        result = check_edf_binocular(file_path)
    elif file_path.suffix.lower() == '.asc':
        result = check_asc_binocular(file_path)
    else:
        print(f"ERROR: Unknown file type: {file_path.suffix}")
        print("Expected .edf or .asc file")
        sys.exit(1)

    # Print results
    print("\n" + "="*60)
    print("BINOCULAR RECORDING CHECK RESULTS")
    print("="*60)
    print(f"File: {file_path.name}")
    print(f"Samples analyzed: {result['sample_count']}")
    print(f"\nLeft eye data found:  {'YES ✓' if result['has_left'] else 'NO ✗'} ({result['left_sample_count']} samples)")
    print(f"Right eye data found: {'YES ✓' if result['has_right'] else 'NO ✗'} ({result['right_sample_count']} samples)")
    print(f"\nRecording mode: {'BINOCULAR ✓✓' if result['is_binocular'] else 'MONOCULAR ✗'}")

    if result['is_binocular']:
        print("\n✓ SUCCESS: Both eyes are being recorded!")
    else:
        print("\n✗ WARNING: Only one eye is being recorded!")
        if result['has_left'] and not result['has_right']:
            print("  Only LEFT eye data found")
        elif result['has_right'] and not result['has_left']:
            print("  Only RIGHT eye data found")
        else:
            print("  No eye data found (file may be empty or corrupted)")

    print("="*60)

    sys.exit(0 if result['is_binocular'] else 1)


if __name__ == '__main__':
    main()
