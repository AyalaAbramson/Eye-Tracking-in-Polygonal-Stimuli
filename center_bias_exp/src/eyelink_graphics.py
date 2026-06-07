"""
Custom EyeLink Graphics environment for PsychoPy.

This module provides a PsychoPy-compatible implementation of the EyeLink
calibration graphics interface. It handles displaying calibration targets,
camera images, and other calibration-related graphics.

Based on SR Research's EyeLinkCoreGraphicsPsychoPy example.
"""

import pylink
from psychopy import visual, event, core
import numpy as np


class EyeLinkCoreGraphicsPsychoPy(pylink.EyeLinkCustomDisplay):
    """
    Custom display class for EyeLink calibration using PsychoPy.
    
    This class implements the pylink.EyeLinkCustomDisplay interface
    to provide calibration target display using PsychoPy windows.
    
    Parameters
    ----------
    tracker : pylink.EyeLink
        Connected EyeLink tracker object.
    win : psychopy.visual.Window
        PsychoPy window for displaying calibration targets.
    """
    
    def __init__(self, tracker, win):
        """Initialize the graphics environment."""
        pylink.EyeLinkCustomDisplay.__init__(self)
        
        self.tracker = tracker
        self.win = win
        self.win_size = win.size
        
        # Calibration target settings
        self.target_outer_size = 30  # Outer ring diameter in pixels
        self.target_inner_size = 6   # Inner dot diameter in pixels
        self.target_outer_color = 'white'
        self.target_inner_color = 'black'
        
        # Create calibration target stimuli
        self.target_outer = visual.Circle(
            win,
            radius=self.target_outer_size / 2,
            lineColor=self.target_outer_color,
            fillColor=self.target_outer_color,
            units='pix'
        )
        
        self.target_inner = visual.Circle(
            win,
            radius=self.target_inner_size / 2,
            lineColor=self.target_inner_color,
            fillColor=self.target_inner_color,
            units='pix'
        )
        
        # State variables
        self.state = None
        self.last_mouse_state = 0
        
        # Key mapping: PsychoPy key names to pylink key codes
        self.key_mapping = {
            'escape': pylink.ESC_KEY,
            'return': pylink.ENTER_KEY,
            'space': ord(' '),
            'c': ord('c'),
            'v': ord('v'),
            'a': ord('a'),
            'o': ord('o'),
            'up': pylink.CURS_UP,
            'down': pylink.CURS_DOWN,
            'left': pylink.CURS_LEFT,
            'right': pylink.CURS_RIGHT,
            'pageup': pylink.PAGE_UP,
            'pagedown': pylink.PAGE_DOWN,
            'f1': pylink.F1_KEY,
            'f2': pylink.F2_KEY,
            'f3': pylink.F3_KEY,
            'f4': pylink.F4_KEY,
            'f5': pylink.F5_KEY,
            'f6': pylink.F6_KEY,
            'f7': pylink.F7_KEY,
            'f8': pylink.F8_KEY,
            'f9': pylink.F9_KEY,
            'f10': pylink.F10_KEY,
        }
        
        # Clear event buffer
        event.clearEvents()
    
    def setup_cal_display(self):
        """
        Set up the calibration display.
        
        Called by EyeLink at the beginning of calibration/validation.
        Clears the screen to prepare for calibration targets.
        """
        self.win.color = [0, 0, 0]  # Gray background
        self.clear_cal_display()
    
    def exit_cal_display(self):
        """
        Exit the calibration display.
        
        Called by EyeLink when calibration/validation is complete.
        Clears the screen.
        """
        self.clear_cal_display()
    
    def clear_cal_display(self):
        """
        Clear the calibration display.
        
        Clears the screen by flipping to the background color.
        """
        self.win.flip()
    
    def erase_cal_target(self):
        """
        Erase the calibration target.
        
        Called by EyeLink when the current calibration target
        should be removed from the display.
        """
        self.clear_cal_display()
    
    def draw_cal_target(self, x, y):
        """
        Draw a calibration target at the specified location.
        
        Parameters
        ----------
        x : int
            X coordinate in EyeLink screen coordinates (0,0 at top-left).
        y : int
            Y coordinate in EyeLink screen coordinates (0,0 at top-left).
        """
        # Convert from EyeLink coordinates (top-left origin)
        # to PsychoPy coordinates (center origin)
        x_psychopy = x - self.win_size[0] / 2
        y_psychopy = self.win_size[1] / 2 - y
        
        # Set target positions
        self.target_outer.pos = (x_psychopy, y_psychopy)
        self.target_inner.pos = (x_psychopy, y_psychopy)
        
        # Draw targets
        self.target_outer.draw()
        self.target_inner.draw()
        self.win.flip()
    
    def play_beep(self, beepid):
        """
        Play a calibration beep sound.
        
        Parameters
        ----------
        beepid : int
            The type of beep to play:
            - pylink.CAL_TARG_BEEP: Target appearance
            - pylink.CAL_GOOD_BEEP: Good calibration
            - pylink.CAL_ERR_BEEP: Calibration error
            - pylink.DC_TARG_BEEP: Drift correction target
            - pylink.DC_GOOD_BEEP: Good drift correction
            - pylink.DC_ERR_BEEP: Drift correction error
        """
        # Sound implementation (optional - can be silent)
        # For now, just pass silently
        pass
    
    def get_input_key(self):
        """
        Get input from keyboard.
        
        Returns
        -------
        list
            List of key events as [key_code, modifier] tuples.
            Returns empty list if no keys pressed.
        """
        # Get keys from PsychoPy
        keys = event.getKeys(modifiers=True)
        key_list = []
        
        for key, modifiers in keys:
            # Convert key name to pylink key code
            if key in self.key_mapping:
                key_code = self.key_mapping[key]
            elif len(key) == 1:
                # Single character - use ASCII code
                key_code = ord(key)
            else:
                # Unknown key - skip
                continue
            
            # Build modifier value
            modifier = 0
            if modifiers.get('shift', False):
                modifier |= 1
            if modifiers.get('ctrl', False):
                modifier |= 2
            if modifiers.get('alt', False):
                modifier |= 4
            
            key_list.append(pylink.KeyInput(key_code, modifier))
        
        return key_list
    
    def get_mouse_state(self):
        """
        Get current mouse state.
        
        Returns
        -------
        tuple
            (x, y, button_state) where x, y are coordinates and
            button_state is a bitmask of pressed buttons.
        """
        # Get mouse position from PsychoPy
        mouse = event.Mouse(win=self.win)
        pos = mouse.getPos()
        buttons = mouse.getPressed()
        
        # Convert from PsychoPy coords to EyeLink coords
        x = int(pos[0] + self.win_size[0] / 2)
        y = int(self.win_size[1] / 2 - pos[1])
        
        # Build button state bitmask
        button_state = 0
        if buttons[0]:
            button_state |= 1
        if len(buttons) > 1 and buttons[1]:
            button_state |= 2
        if len(buttons) > 2 and buttons[2]:
            button_state |= 4
        
        return (x, y, button_state)
    
    def record_abort_hide(self):
        """Called when recording is aborted."""
        pass
    
    def set_tracker_info(self, info):
        """
        Set tracker information.
        
        Parameters
        ----------
        info : object
            Tracker information object.
        """
        pass
    
    def setup_image_display(self, width, height):
        """
        Set up camera image display.
        
        Parameters
        ----------
        width : int
            Image width in pixels.
        height : int
            Image height in pixels.
        """
        # Not implementing camera image display for now
        pass
    
    def exit_image_display(self):
        """Exit camera image display mode."""
        self.clear_cal_display()
    
    def image_title(self, title):
        """
        Display image title.
        
        Parameters
        ----------
        title : str
            Title text to display.
        """
        pass
    
    def draw_image_line(self, width, line, totlines, buff):
        """
        Draw a line of the camera image.
        
        Parameters
        ----------
        width : int
            Line width in pixels.
        line : int
            Line number.
        totlines : int
            Total number of lines.
        buff : bytes
            Line pixel data.
        """
        # Not implementing camera image display
        pass
    
    def set_image_palette(self, r, g, b):
        """
        Set camera image color palette.
        
        Parameters
        ----------
        r, g, b : list
            Red, green, blue palette values.
        """
        pass
    
    def alert_printf(self, msg):
        """
        Display an alert message.
        
        Parameters
        ----------
        msg : str
            Alert message text.
        """
        print(f"EyeLink Alert: {msg}")
