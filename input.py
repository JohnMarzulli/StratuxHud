class InputResponse(object):
    def __init__(self, is_handled: bool, is_terminal: bool, input_event):
        self.is_handled = is_handled
        self.is_terminal = is_terminal
        self.input_event = input_event