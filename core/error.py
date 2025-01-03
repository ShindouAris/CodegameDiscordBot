class InvaidFile(Exception):
    def __init__(self):
        super().__init__("Invalid file")

class NoHostAvailable(Exception):
    def __init__(self):
        super().__init__("No host available")

class CantNotConnect(Exception):
    def __init__(self):
        super().__init__("Can't connect to node")