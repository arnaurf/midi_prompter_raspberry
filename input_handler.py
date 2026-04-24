import time
import threading

NEXT_PAGE = 48  # MIDI note for "next page" (C3)
CHANNEL = 1     # Default MIDI channel
DEBUG = False

def keyboardInputHandler(pdf_manager, action_queue):
    def input_thread():
        while True:
            cmd = input("Enter Relative Path or 'exit': ")
            if cmd == "exit":
                action_queue.put(lambda: exit())
            else:
                action_queue.put(lambda pm=pdf_manager, p=cmd: pm.open_pdf(p))
    threading.Thread(target=input_thread, daemon=True).start()

class MidiInputHandler:
    def __init__(self, port, midi_through, pdf_manager, queue, setlist_map):
        self.port = port
        self._wallclock = time.time()
        self.midi_through = midi_through
        self.pdf_manager = pdf_manager
        self.channel = CHANNEL - 1 
        self.action_queue = queue
        self.setlist_map = setlist_map # { "1": "Folder/Song.pdf" }

    def __call__(self, event, data=None):
        message, deltatime = event
        self._wallclock += deltatime
        self.midi_through.send_message(message)

        message_type = message[0] & 0xF0
        message_channel = message[0] & 0x0F  

        if message_type == 0xC0 and message_channel == self.channel:
            program_number = message[1]
            rel_path = self.setlist_map.get(str(program_number))
            if rel_path:
                self.action_queue.put(lambda: self.pdf_manager.open_pdf(rel_path))

        elif message_type == 0x90 and message_channel == self.channel:
            if message[1] == NEXT_PAGE:
                self.action_queue.put(lambda: self.pdf_manager.turn_page())