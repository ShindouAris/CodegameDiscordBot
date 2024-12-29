class InvaidFile(Exception):
    def __init__(self):
        super().__init__("Invalid file")

class NoHostAvailable(Exception):
    def __init__(self):
        super().__init__("No host available")