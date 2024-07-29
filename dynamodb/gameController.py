from datetime import datetime
from botocore.exceptions import ClientError

class GameController:
    def __init__(self, connectionManager):
        self.cm = connectionManager
        self.gamesTable = self.cm.getTable('Games')

    def acceptGameInvite(self, game):
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
            print(f"Error accepting game invite: {e}")
            return False

    def getGame(self, gameId):
        """
        Retrieve a game item from the DynamoDB table.
        """
        try:
            response = self.gamesTable.get_item(Key={"GameId": gameId})
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting game: {e}")
            return None

    def getBoardState(self, gameItem):
        """
        Get the board state from the game item.
        """
        return gameItem.get('BoardState', [None]*9)

    def checkForGameResult(self, boardState, gameItem, username):
        """
        Check if the game has a result based on the board state and game item.
        """
        # Placeholder for game result checking logic
        # Example implementation: check if there is a result key
        return gameItem.get('Result', None)

    def changeGameToFinishedState(self, gameItem, result, username):
        """
        Change the game state to finished and update the result.
        """
        key = {"GameId": gameItem.get("GameId")}
        attributeUpdates = {
            "Status": {"Value": "FINISHED", "Action": "PUT"},
            "Result": {"Value": result, "Action": "PUT"}
        }
        try:
            self.gamesTable.update_item(
                Key=key,
                AttributeUpdates=attributeUpdates
            )
            return True
        except ClientError as e:
            print(f"Error updating game state: {e}")
            return False

    def createNewGame(self, gameId, creator, invitee):
        """
        Create a new game and add it to the DynamoDB table.
        """
        item = {
            "GameId": gameId,
            "Creator": creator,
            "Invitee": invitee,
            "StatusDate": "PENDING_",
            "BoardState": [None]*9,
            "Turn": creator
        }
        try:
            self.gamesTable.put_item(Item=item)
            return True
        except ClientError as e:
            print(f"Error creating new game: {e}")
            return False

    def updateGameState(self, gameId, position, marker):
        """
        Update the board state of the game.
        """
        try:
            response = self.gamesTable.get_item(Key={"GameId": gameId})
            item = response.get('Item', {})
            boardState = item.get('BoardState', [None]*9)
            boardState[position] = marker

            attributeUpdates = {
                "BoardState": {"Value": boardState, "Action": "PUT"},
                "Turn": {"Value": marker, "Action": "PUT"}  # Switch turn
            }
            self.gamesTable.update_item(
                Key={"GameId": gameId},
                AttributeUpdates=attributeUpdates
            )
            return True
        except ClientError as e:
            print(f"Error updating game state: {e}")
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
            print(f"Error getting game invites: {e}")
            return []

    def getGamesWithStatus(self, username, status):
        """
        Get all games for a user with a specific status.
        """
        try:
            response = self.gamesTable.scan(
                FilterExpression="Creator = :username OR Invitee = :username AND begins_with(StatusDate, :status)",
                ExpressionAttributeValues={
                    ":username": username,
                    ":status": status
                }
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting games with status {status}: {e}")
            return []

    def checkIfTableIsActive(self):
        """
        Check if the games table is active.
        """
        try:
            response = self.cm.dynamodb.describe_table(TableName='Games')
            return response['Table']['TableStatus'] == 'ACTIVE'
        except ClientError as e:
            print(f"Error checking if table is active: {e}")
            return False
