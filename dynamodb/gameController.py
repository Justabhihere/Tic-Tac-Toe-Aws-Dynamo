from datetime import datetime
from botocore.exceptions import ClientError

class GameController:
    def __init__(self, connectionManager):
        self.cm = connectionManager
        self.gamesTable = self.cm.dynamodb.Table('Games')

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
        try:
            self.gamesTable.update_item(
                Key=key,
                AttributeUpdates=attributeUpdates
            )
            return True
        except ClientError as e:
            print "Error accepting game invite: {}".format(e)
            return False

    def getGameInvites(self, username):
        """
        Retrieve all game invites for a specific user.
        """
        try:
            response = self.gamesTable.scan(
                FilterExpression="Invitee = :username and #status = :status",
                ExpressionAttributeValues={
                    ":username": username,
                    ":status": "INVITED"
                },
                ExpressionAttributeNames={
                    "#status": "Status"
                }
            )
            return response.get('Items', [])
        except ClientError as e:
            print "Error retrieving game invites: {}".format(e)
            return []

    def getGamesWithStatus(self, username, status):
        """
        Retrieve all games for a specific user with a specific status.
        """
        try:
            response = self.gamesTable.scan(
                FilterExpression="Creator = :username or Invitee = :username",
                ExpressionAttributeValues={
                    ":username": username
                }
            )
            games = [item for item in response.get('Items', []) if item.get('Status') == status]
            return games
        except ClientError as e:
            print "Error retrieving games with status {}: {}".format(status, e)
            return []

    def getGame(self, gameId):
        """
        Retrieve a specific game by gameId.
        """
        try:
            response = self.gamesTable.get_item(
                Key={"GameId": gameId}
            )
            return response.get('Item', None)
        except ClientError as e:
            print "Error retrieving game: {}".format(e)
            return None

    def updateGameState(self, gameId, position, marker):
        """
        Update the game state with the current position and marker.
        """
        try:
            self.gamesTable.update_item(
                Key={"GameId": gameId},
                UpdateExpression="SET board[{}] = :marker".format(position),
                ExpressionAttributeValues={":marker": marker}
            )
            return True
        except ClientError as e:
            print "Error updating game state: {}".format(e)
            return False
