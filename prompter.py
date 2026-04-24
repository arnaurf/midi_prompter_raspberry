# PROMPTERIA
#
# Copyright (C) 2025 Arnau Ruiz Fernandez
#
# MIDI PDF Teleprompter is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

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
parser.add_argument("-i", "--input", default="pdf_files.json", help="Path to the MIDI mapping JSON.")
parser.add_argument("-g", "--gui", action="store_true", help="Enable GUI setup")
args = parser.parse_args()

JSON_PATH = args.input
ENABLE_GUI = args.gui

def list_midi_ports():
    """List all available MIDI devices"""
    midi_in = rtmidi.MidiIn()
    ports = midi_in.get_ports()
    if ports:
        print("Available MIDI devices:")
        for i, port in enumerate(ports): 
            print(f"{i + 1}: {port}")
        return ports
    return []

def setup_midi(pdf_manager, action_queue, overlay, setlist_map):
    available_ports = list_midi_ports()
    if not available_ports:
        print("No MIDI ports detected")
        sys.exit(1)

    if ENABLE_GUI:
        # El menú ahora captura el foco para funcionar con teclado
        port_idx = overlay.prompt_selection("Midi Setup", available_ports)
        if port_idx == -1: 
            sys.exit(0)
    else:
        port_idx = int(input("Select the MIDI device: ")) - 1

    midi_in = rtmidi.MidiIn()
    midi_out = rtmidi.MidiOut()
    midi_in.open_port(port_idx)
    midi_out.open_port(port_idx)
    
    # Pasamos el setlist_map al handler para Program Change
    handler = MidiInputHandler(available_ports[port_idx], midi_out, pdf_manager, action_queue, setlist_map)
    midi_in.set_callback(handler)
    return midi_in, midi_out

def first_pdf(pdf_dir):
    try:
        files = [f for f in sorted(os.listdir(pdf_dir)) 
                 if f.lower().endswith('.pdf') and os.path.isfile(os.path.join(pdf_dir, f))]
        if files:
            return files[0]
    except Exception as e:
        print(f"Error accediendo a la carpeta PDF: {e}")
    
    return None

def main():
    dirname = os.path.dirname(__file__)
    pdf_folder = os.path.join(dirname, "pdf")

    # Cargar mapeo MIDI desde JSON
    try:
        with open(JSON_PATH, 'r') as f:
            setlist_map = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {JSON_PATH}: {e}")
        setlist_map = {}

    zathura = pdfManager(pdf_folder)
    action_queue = queue.Queue()

    # Callback para cuando se selecciona un PDF en el navegador
    def on_selection(rel_path):
        action_queue.put(lambda: zathura.open_pdf(rel_path))
        overlay.show_mini_hint(on_enter_press)

    overlay = OverlayMenu(pdf_folder, on_selection)

    # Callback para abrir el selector al presionar ENTER en el hint
    def on_enter_press():
        overlay.show_pdf_selector()

    midi_in, midi_out = setup_midi(zathura, action_queue, overlay, setlist_map)
    if IS_LINUX:
        # Iniciamos zathura (instancia vacía o con el primer PDF si se desea)
        zathura.start_zathura(first_pdf(pdf_folder))
    
    if ENABLE_GUI:
        overlay.show_mini_hint(on_enter_press)

    try:
        while True:
            while not action_queue.empty():
                action_queue.get()()
            if ENABLE_GUI:
                overlay.update()
            time.sleep(0.01)
    except KeyboardInterrupt:
        zathura.close()

if __name__ == "__main__":
    main()
