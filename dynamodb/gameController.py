from datetime import datetime
from botocore.exceptions import ClientError

class GameController:
    def __init__(self, connectionManager):
        self.cm = connectionManager
        self.gamesTable = self.cm.getTable('Games')

    def acceptGameInvite(self, game, username):
        """
        Accept a game invite and update the game status to IN_PROGRESS.
        """
        date = str(datetime.now())
        status = "IN_PROGRESS_"
        statusDate = status + date
        key = {"GameId": game.get("GameId")}
        attributeUpdates = {
            "StatusDate": {"Value": statusDate, "Action": "PUT"}
        }
        conditions = {
            "StatusDate": {
                "AttributeValueList": ["PENDING_"],
                "ComparisonOperator": "BEGINS_WITH"
            }
        }
        try:
            self.gamesTable.update_item(
                Key=key,
                AttributeUpdates=attributeUpdates,
                Expected=conditions
            )
            return True
        except ClientError as e:
            print("Error accepting game invite: {}".format(e))
            return False

    def getGameInvites(self, username):
        """
        Get all game invites for a user.
        """
        try:
            response = self.gamesTable.scan(
                FilterExpression="Invitee = :username AND begins_with(StatusDate, :pending)",
                ExpressionAttributeValues={
                    ":username": username,
                    ":pending": "PENDING_"
                }
            )
            return response.get('Items', [])
        except ClientError as e:
            print("Error getting game invites: {}".format(e))
            return []

    def getGame(self, gameId):
        """
        Retrieve a game by its ID.
        """
        try:
            response = self.gamesTable.get_item(Key={"GameId": gameId})
            return response.get('Item', None)
        except ClientError as e:
            print("Error getting game: {}".format(e))
            return None

    def getBoardState(self, game):
        """
        Retrieve the board state from the game item.
        """
        return game.get('BoardState', [None] * 9)

    def checkForGameResult(self, boardState, game, username):
        """
        Check for the result of the game.
        """
        # Placeholder for actual game result logic
        return game.get('Result', None)

    def changeGameToFinishedState(self, game, result, username):
        """
        Change the game state to finished.
        """
        date = str(datetime.now())
        status = "FINISHED_"
        statusDate = status + date
        key = {"GameId": game.get("GameId")}
        attributeUpdates = {
            "StatusDate": {"Value": statusDate, "Action": "PUT"},
            "Result": {"Value": result, "Action": "PUT"}
        }
        conditions = {
            "StatusDate": {
                "AttributeValueList": ["IN_PROGRESS_"],
                "ComparisonOperator": "BEGINS_WITH"
            }
        }
        try:
            self.gamesTable.update_item(
                Key=key,
                AttributeUpdates=attributeUpdates,
                Expected=conditions
            )
            return True
        except ClientError as e:
            print("Error changing game to finished state: {}".format(e))
            return False

    def createNewGame(self, gameId, creator, invitee):
        """
        Create a new game item.
        """
        try:
            self.gamesTable.put_item(
                Item={
                    "GameId": gameId,
                    "Creator": creator,
                    "Invitee": invitee,
                    "StatusDate": "PENDING_{}".format(str(datetime.now())),
                    "BoardState": [None] * 9
                }
            )
            return True
        except ClientError as e:
            print("Error creating new game: {}".format(e))
            return False

    def updateGameState(self, gameId, position, marker):
        """
        Update the game state with a new move.
        """
        try:
            response = self.gamesTable.update_item(
                Key={"GameId": gameId},
                UpdateExpression="SET BoardState[{}] = :marker".format(position),
                ExpressionAttributeValues={":marker": marker},
                ReturnValues="UPDATED_NEW"
            )
            return response.get('Attributes') is not None
        except ClientError as e:
            print("Error updating game state: {}".format(e))
            return False

    def checkIfTableIsActive(self):
        """
        Check if the 'Games' table is active.
        """
        try:
            table_description = self.cm.getTable('Games').describe()
            status = table_description.get('Table', {}).get('TableStatus', '')
            return status == 'ACTIVE'
        except ClientError as e:
            print("Error checking table status: {}".format(e))
            return False
