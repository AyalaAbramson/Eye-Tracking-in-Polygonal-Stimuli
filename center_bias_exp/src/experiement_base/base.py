import configargparse
import os
import platform
import random
import time
import sys
import pylink
from experiement_base.EyeLinkCoreGraphicsPsychoPy import EyeLinkCoreGraphicsPsychoPy
from psychopy import visual, core, event, monitors, gui, logging
from math import pi, sin
from string import ascii_letters, digits

logging.console.setLevel(logging.CRITICAL)


def config_general_parser():
    parser = configargparse.get_arg_parser()
    parser.add_argument('--config', is_config_file=True, help='config file path')

    parser.add_argument('--fullscreen', action='store_true')
    parser.add_argument('--window_width', type=int, default=1200)
    parser.add_argument('--window_height', type=int, default=900)
    parser.add_argument('--background_color', type=int, nargs='+', default=[128, 128, 128])

    parser.add_argument('--dummy_mode', action='store_true')
    parser.add_argument('--calibration_target', type=str, default='circle')
    parser.add_argument('--calibration_target_size', type=int, default=24)



def get_edf_filename(args, default='test', experiment_name=None):
    # Prompt user to specify an EDF data filename
    # before we open a fullscreen window
    dlg_title = 'EDF File Name'
    if experiment_name is not None:
        dlg_title = f'EDF File Name for {experiment_name}'
    dlg_prompt = 'Please enter a file name with 8 or fewer characters\n' + \
                 '[letters, numbers, and underscore].'

    # loop until we get a valid filename
    edf_fname = default
    while True:
        dlg = gui.Dlg(dlg_title)
        dlg.addText(dlg_prompt)
        dlg.addField('File Name:', edf_fname)
        # show dialog and wait for OK or Cancel
        ok_data = dlg.show()
        if dlg.OK:  # if ok_data is not None
            print('EDF data filename: {}'.format(ok_data[0]))
        else:
            print('user cancelled')
            core.quit()
            sys.exit()

        # get the string entered by the experimenter
        tmp_str = dlg.data[0]
        # strip trailing characters, ignore the ".edf" extension
        edf_fname = tmp_str.rstrip().split('.')[0]

        # check if the filename is valid (length <= 8 & no special char)
        allowed_char = ascii_letters + digits + '_'
        if not all([c in allowed_char for c in edf_fname]):
            print('ERROR: Invalid EDF filename')
        elif len(edf_fname) > 8:
            print('ERROR: EDF filename should not exceed 8 characters')
        else:
            break

    args.edf_filename = edf_fname
    return edf_fname


def get_session_identifier(args):
    if not os.path.exists(args.results_dir):
        raise FileExistsError(f'Results directory {args.results_dir} does not exists')

    time_str = time.strftime("_%Y_%m_%d_%H_%M", time.localtime())
    session_identifier = args.edf_filename + time_str

    # create a folder for the current testing session in the "results" folder
    session_folder = os.path.join(args.results_dir, session_identifier)
    if not os.path.exists(session_folder):
        os.makedirs(session_folder)

    args.session_identifier = session_identifier
    args.session_folder = session_folder
    return session_identifier, session_folder


def connect(args):
    if args.dummy_mode:
        el_tracker = pylink.EyeLink(None)
    else:
        try:
            el_tracker = pylink.EyeLink("100.1.1.1")
        except RuntimeError as error:
            print('ERROR:', error)
            core.quit()
            sys.exit()

    args.el_tracker = el_tracker
    return el_tracker


def open_edf_file(args):
    # Step 2: Open an EDF data file on the Host PC
    edf_file = args.edf_filename + ".EDF"
    try:
        args.el_tracker.openDataFile(edf_file)
    except RuntimeError as err:
        print('ERROR:', err)
        # close the link if we have one open
        if args.el_tracker.isConnected():
            args.el_tracker.close()
        core.quit()
        sys.exit()

    preamble_text = f'Recording of experiment: {args.experiment_name}'
    args.el_tracker.sendCommand("add_file_preamble_text '%s'" % preamble_text)
    args.edf_file_on_host = edf_file
    return edf_file


def record_all_variables(args):
    # Get the software version:  1-EyeLink I, 2-EyeLink II, 3/4-EyeLink 1000,
    # 5-EyeLink 1000 Plus, 6-Portable DUO
    eyelink_ver = 0  # set version to 0, in case running in Dummy mode
    if not args.dummy_mode:
        vstr = args.el_tracker.getTrackerVersionString()
        eyelink_ver = int(vstr.split()[-1].split('.')[0])
        # print out some version info in the shell
        print('Running experiment on %s, version %d' % (vstr, eyelink_ver))

    # File and Link data control
    # what eye events to save in the EDF file, include everything by default
    file_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT'
    # what eye events to make available over the link, include everything by default
    link_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON,FIXUPDATE,INPUT'
    # what sample data to save in the EDF data file and to make available
    # over the link, include the 'HTARGET' flag to save head target sticker
    # data for supported eye trackers
    if eyelink_ver > 3:
        file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,HTARGET,GAZERES,BUTTON,STATUS,INPUT'
        link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,HTARGET,STATUS,INPUT'
    else:
        file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,GAZERES,BUTTON,STATUS,INPUT'
        link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS,INPUT'
    args.el_tracker.sendCommand("file_event_filter = %s" % file_event_flags)
    args.el_tracker.sendCommand("file_sample_data = %s" % file_sample_flags)
    args.el_tracker.sendCommand("link_event_filter = %s" % link_event_flags)
    args.el_tracker.sendCommand("link_sample_data = %s" % link_sample_flags)

def check_for_escape(args):
    if 'escape' in event.getKeys():
        terminate_experiment(args)
# args.fullscreen

def setup_screen(args):
    mon = monitors.Monitor('myMonitor', width=100.0, distance=150.0)
    win = visual.Window(fullscr= True,
                        size=(args.window_width, args.window_height),
                        monitor=mon,
                        winType='pyglet',
                        units='pix',
                        )
    print(args.window_width)
    print(args.window_height)

    # win.setMouseVisible(False)
    # win.mouseVisible = False
    event.Mouse(visible=False)
    # get the native screen resolution used by PsychoPy
    scn_width, scn_height = win.size
    # Pass the display pixel coordinates (left, top, right, bottom) to the tracker
    # see the EyeLink Installation Guide, "Customizing Screen Settings"
    el_coords = "screen_pixel_coords = 0 0 %d %d" % (scn_width - 1, scn_height - 1)
    args.el_tracker.sendCommand(el_coords)

    # Write a DISPLAY_COORDS message to the EDF file
    # Data Viewer needs this piece of info for proper visualization, see Data
    # Viewer User Manual, "Protocol for EyeLink Data to Viewer Integration"
    dv_coords = "DISPLAY_COORDS  0 0 %d %d" % (scn_width - 1, scn_height - 1)
    args.el_tracker.sendMessage(dv_coords)

    # Configure a graphics environment (genv) for tracker calibration
    genv = EyeLinkCoreGraphicsPsychoPy(args.el_tracker, win)
    print(genv)  # print out the version number of the CoreGraphics library
    # if genv.get_input_key().key == 27: ##todo
    #     abort_trial(args)
    # Set background and foreground colors for the calibration target
    # in PsychoPy, (-1, -1, -1)=black, (1, 1, 1)=white, (0, 0, 0)=mid-gray
    foreground_color = (-1, -1, -1)
    background_color = win.color
    genv.setCalibrationColors(foreground_color, background_color)
    args.mon = mon
    args.win = win
    args.genv = genv


def set_calibration_settings(args):
    args.genv.setTargetType(args.calibration_target)
    args.genv.setTargetSize(args.calibration_target_size) # in pixels
    args.genv.setCalibrationSounds('', '', '')


def clear_screen(args):
    """ clear up the PsychoPy window"""
    args.win.fillColor = args.genv.getBackgroundColor()
    args.win.flip()


def show_msg(args, text, wait_for_keypress=True):
    """ Show task instructions on screen"""

    screen_width = args.win.size[0]
    msg = visual.TextStim(args.win, text,
                          # color=args.genv.getForegroundColor(),
                          wrapWidth=screen_width,
                          height=60)
    clear_screen(args)
    msg.draw()
    args.win.flip()

    # wait indefinitely, terminates upon any key press
    if wait_for_keypress:
        event.waitKeys()
        clear_screen(args)


def terminate_experiment(args):
    """ Terminate the task gracefully and retrieve the EDF data file

    file_to_retrieve: The EDF on the Host that we would like to download
    win: the current window used by the experimental script
    """

    el_tracker = pylink.getEYELINK()

    if el_tracker.isConnected():
        # Terminate the current trial first if the task terminated prematurely
        error = el_tracker.isRecording()
        if error == pylink.TRIAL_OK:
            abort_trial(args)

        # Put tracker in Offline mode
        el_tracker.setOfflineMode()

        # Clear the Host PC screen and wait for 500 ms
        el_tracker.sendCommand('clear_screen 0')
        pylink.msecDelay(500)

        # Close the edf data file on the Host
        el_tracker.closeDataFile()

        # Show a file transfer message on the screen
        msg = 'EDF data is transferring from EyeLink Host PC...'
        show_msg(args, msg, wait_for_keypress=False)

        # Download the EDF data file from the Host PC to a local data folder
        # parameters: source_file_on_the_host, destination_file_on_local_drive
        local_edf = os.path.join(args.session_folder, args.session_identifier + '.EDF')
        print(local_edf)
        try:
            el_tracker.receiveDataFile(args.edf_filename, local_edf)
        except RuntimeError as error:
            print('ERROR:', error)

        # Close the link to the tracker.
        el_tracker.close()

    # close the PsychoPy window
    args.win.close()

    # quit PsychoPy
    core.quit()



def abort_trial(args):
    """Ends recording """

    el_tracker = pylink.getEYELINK()

    # Stop recording
    if el_tracker.isRecording():
        # add 100 ms to catch final trial events
        pylink.pumpDelay(100)
        el_tracker.stopRecording()

    # clear the screen
    clear_screen(args)
    # Send a message to clear the Data Viewer screen
    bgcolor_RGB = (116, 116, 116)
    el_tracker.sendMessage('!V CLEAR %d %d %d' % bgcolor_RGB)

    # send a message to mark trial end
    el_tracker.sendMessage('TRIAL_RESULT %d' % pylink.TRIAL_ERROR)

    return pylink.TRIAL_ERROR