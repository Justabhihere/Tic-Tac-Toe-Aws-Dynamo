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
            response = self.gamesTable.update_item(
                Key=key,
                UpdateExpression="set StatusDate = :statusDate",
                ExpressionAttributeValues={
                    ":statusDate": statusDate
                },
                ReturnValues="UPDATED_NEW"
            )
            return True
        except ClientError as e:
            print "Error updating game invite: {}".format(e)
            return False

    def getGame(self, gameId):
        """
        Retrieve a game by its ID.
        """
        try:
            response = self.gamesTable.get_item(Key={"GameId": gameId})
            return response.get('Item', None)
        except ClientError as e:
            print "Error retrieving game: {}".format(e)
            return None

    def createNewGame(self, gameId, creator, invitee):
        """
        Create a new game entry.
        """
        item = {
            "GameId": gameId,
            "Creator": creator,
            "Invitee": invitee,
            "Status": "INVITED",
            "Turn": creator,
            "Board": [""] * 9
        }
        try:
            self.gamesTable.put_item(Item=item)
            return True
        except ClientError as e:
            print "Error creating new game: {}".format(e)
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
        Retrieve all games with a specific status for a user.
        """
        try:
            response = self.gamesTable.scan(
                FilterExpression="(Creator = :username or Invitee = :username) and #status = :status",
                ExpressionAttributeValues={
                    ":username": username,
                    ":status": status
                },
                ExpressionAttributeNames={
                    "#status": "Status"
                }
            )
            return response.get('Items', [])
        except ClientError as e:
            print "Error retrieving games with status '{}': {}".format(status, e)
            return []

    def checkIfTableIsActive(self):
        """
        Check if the DynamoDB table is active.
        """
        try:
            response = self.cm.dynamodb.describe_table(TableName='Games')
            status = response['Table']['TableStatus']
            return status == 'ACTIVE'
        except ClientError as e:
            print "Error checking table status: {}".format(e)
            return False

    def getBoardState(self, game):
        """
        Retrieve the current board state for a game.
        """
        return game.get("Board", [""] * 9)

    def checkForGameResult(self, boardState, game, username):
        """
        Check if there is a result for the game.
        """
        # Implement your game result checking logic here
        # Return the result if available, otherwise return None
        pass

    def changeGameToFinishedState(self, game, result, username):
        """
        Change the game's status to finished.
        """
        try:
            key = {"GameId": game.get("GameId")}
            update_expression = "set Status = :status, Result = :result"
            expression_attribute_values = {
                ":status": "FINISHED",
                ":result": result
            }
            self.gamesTable.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return True
        except ClientError as e:
            print "Error updating game to finished state: {}".format(e)
            return False

    def updateGameState(self, gameId, position, marker):
        """
        Update the state of the game with the marker at the specified position.
        """
        try:
            response = self.gamesTable.update_item(
                Key={"GameId": gameId},
                UpdateExpression="set Board[{}] = :marker".format(position),
                ExpressionAttributeValues={
                    ":marker": marker
                },
                ReturnValues="UPDATED_NEW"
            )
            return True
        except ClientError as e:
            print "Error updating game state: {}".format(e)
            return False
