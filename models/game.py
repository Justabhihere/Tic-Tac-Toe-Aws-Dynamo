class Game:
    def __init__(self, data):
        self.data = data
        self.status = data.get('status', 'UNKNOWN')
        self.turn = data.get('turn', 'UNKNOWN')
        self.o = data.get('playerO', 'UNKNOWN')  # Example player identifiers

    def getResult(self, username):
        # Handle cases where the result key might be missing
        return self.data.get('Result', None)

    def getOpposingPlayer(self, username):
        # Example method to return the opposing player
        return self.data.get('opponent', 'UNKNOWN')
