"""
Eye dominance test utility.

Simple hole-in-card test to determine ocular dominance.
Based on the standard clinical method.
"""

from psychopy import visual, event, core


def run_eye_dominance_test(win):
    """
    Run a simple eye dominance test (hole-in-card method).

    The participant extends both arms and creates a small triangle/hole
    with their hands, then views a target through it with both eyes open.
    When they close one eye at a time, the target disappears when the
    non-dominant eye is open.

    Parameters
    ----------
    win : visual.Window
        PsychoPy window to display instructions.

    Returns
    -------
    str
        'left', 'right', or 'unknown' (if test fails/skipped)

    Notes
    -----
    This is a self-report test - the participant indicates which eye
    keeps the target visible when alternating eye closure.
    """
    # Instructions text
    instructions = """EYE DOMINANCE TEST

This quick test will determine your dominant eye.

Instructions:
1. Extend both arms in front of you
2. Create a small triangle/hole with your hands
3. Look at the + on screen through the hole (both eyes open)
4. Keep looking at the + and slowly bring your hands toward your face
5. Your hands will naturally move toward one eye - that's your dominant eye

When ready:
- Press 'L' if your hands moved to your LEFT eye
- Press 'R' if your hands moved to your RIGHT eye
- Press 'S' to SKIP this test

Note: There's no right or wrong answer!
"""

    # Create instruction text
    instr_text = visual.TextStim(
        win,
        text=instructions,
        pos=(0, 0),
        height=30,
        color='white',
        wrapWidth=win.size[0] * 0.8,
        alignText='left'
    )

    # Create fixation cross for participant to focus on
    fixation = visual.TextStim(
        win,
        text='+',
        pos=(0, 0),
        height=80,
        color='white',
        bold=True
    )

    # Show instructions with fixation cross visible
    instr_text.draw()
    fixation.draw()
    win.flip()

    # Wait for participant response
    event.clearEvents()

    dominant_eye = 'unknown'
    waiting = True

    while waiting:
        keys = event.getKeys(keyList=['l', 'r', 's', 'escape'])

        if keys:
            key = keys[0].lower()

            if key == 'l':
                dominant_eye = 'left'
                waiting = False
            elif key == 'r':
                dominant_eye = 'right'
                waiting = False
            elif key == 's':
                dominant_eye = 'unknown'
                waiting = False
            elif key == 'escape':
                dominant_eye = 'unknown'
                waiting = False

        core.wait(0.01)  # Small delay to prevent CPU spinning

    # Show confirmation
    if dominant_eye != 'unknown':
        confirmation_text = visual.TextStim(
            win,
            text=f"Dominant eye recorded: {dominant_eye.upper()}\n\nPress SPACE to continue",
            pos=(0, 0),
            height=40,
            color='white'
        )
        confirmation_text.draw()
        win.flip()
        event.waitKeys(keyList=['space'])
    else:
        skip_text = visual.TextStim(
            win,
            text="Eye dominance test skipped\n\nPress SPACE to continue",
            pos=(0, 0),
            height=40,
            color='white'
        )
        skip_text.draw()
        win.flip()
        event.waitKeys(keyList=['space'])

    return dominant_eye
