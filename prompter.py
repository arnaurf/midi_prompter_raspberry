# PROMPTERIA
#
# Copyright (C) 2025 Arnau Ruiz Fernandez
#
# MIDI PDF Teleprompter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# See <https://www.gnu.org/licenses/> for more details.

import rtmidi
import sys
import json
import argparse
import queue
import os
import time
from pdf_manager import pdfManager
from input_handler import keyboardInputHandler, MidiInputHandler
from overlay_menu import OverlayMenu
import platform

# Detect system
IS_LINUX = platform.system() == "Linux"

# Parse input params
parser = argparse.ArgumentParser(description="Light midi-controlled Teleprompter using PDFs")
parser.add_argument(
    "-i", "--input",
    default="pdf_files.json",
    help="Path to the setlist file. It must be a json containing multiple PDF's file paths. Default: pdf_files.json",
)
parser.add_argument(
    "-g", "--gui",
    action="store_true",
    help="Set to enable gui when prompting in the setup process",
)
args = parser.parse_args()
JSON_PATH = args.input
ENABLE_GUI = args.gui

def list_midi_ports():
    """List all available MIDI devices"""
    midi_in = rtmidi.MidiIn()
    available_ports = midi_in.get_ports()

    if available_ports:
        print("Available MIDI devices:")
        for i, port in enumerate(available_ports):
            print(f"{i + 1}: {port}")
        return available_ports
    else:
        print("No MIDI ports detected")


def setup_midi(pdf_manager, queue, overlay: OverlayMenu):
    """Setup the MIDI device for i/o"""
    available_ports = list_midi_ports()
    if ENABLE_GUI:
        port_name = overlay.prompt_selection("Midi Setup", available_ports) + 1
        if port_name == 0: sys.exit(0)
    else:
        port_name = input("Select the MIDI device: ")

    if not available_ports:
        print("No MIDI ports detected")
        sys.exit(1)
    print(port_name)
    midi_in = rtmidi.MidiIn()
    midi_out = rtmidi.MidiOut()
    midi_in.open_port(int(port_name) - 1)
    midi_out.open_port(int(port_name) - 1)
    print(f"Listening to port {available_ports[int(port_name) - 1]}")

    midi_in.set_callback(MidiInputHandler(port_name, midi_out, pdf_manager, queue))
    return midi_in, midi_out


def main():
    dirname = os.path.dirname(__file__)
    pdf_folder = os.path.join(dirname, "pdf")

    # Check PDF files
    with open(JSON_PATH, 'r') as f:
        raw_pdf_files = json.load(f)
    pdf_files = {int(k): v for k, v in raw_pdf_files.items()}

    missing_files = [f"{key}: {subpath}" for key, subpath in pdf_files.items()
                     if not os.path.exists(os.path.join(pdf_folder, subpath))]
    if missing_files:
        print("ERROR: The following PDFs don't exist:")
        for missing in missing_files:
            print(f"  - {missing}")
        sys.exit(1)

    # Listen keyboard and MIDI device and add tasks to queue
    zathura = pdfManager(pdf_files, pdf_folder)
    action_queue = queue.Queue()

    # Define the callback for when a PDF is selected in the menu
    def on_selection(pdf_id):
        print(f"Opening pdf {pdf_id}")
        if IS_LINUX:
            action_queue.put(lambda: zathura.open_pdf(pdf_id))
        # Re-show the hint after selection
        overlay.show_mini_hint(on_enter_press)

    overlay = OverlayMenu(pdf_files, on_selection)

    # Callback: what happens when ENTER is pressed on the hint window
    def on_enter_press():
        overlay.show_pdf_selector()

    # 1. MIDI Setup
    midi_in, midi_out = setup_midi(zathura, action_queue, overlay)

    # 2. Keyboard Input (ONLY ON LINUX / RASPBERRY)
    if IS_LINUX:
        keyboardInputHandler(zathura, action_queue)
    else:
        print("Skipping keyboardInputHandler on macOS to avoid Tcl errors.")

    # 3. Show the initial UI Hint
    overlay.show_mini_hint(on_enter_press)

    try:
        while True:
            # Process tasks from queue (MIDI or GUI actions)
            while not action_queue.empty():
                action = action_queue.get()
                action()
            
            # Keep Tkinter alive (Hint, Selectors, etc.)
            overlay.update()
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("The show has ended!")
        zathura.close()

if __name__ == "__main__":
    main()
