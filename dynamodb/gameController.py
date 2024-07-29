import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from datetime import datetime

class GameController:
    def __init__(self, connectionManager):
        self.cm = connectionManager
        self.dynamodb = self.cm.dynamodb
        self.gamesTable = self.cm.getGamesTable()

    def createNewGame(self, gameId, creator, invitee):
        now = str(datetime.now())
        statusDate = "PENDING_" + now
        item = {
            "GameId": gameId,
            "HostId": creator,
            "StatusDate": statusDate,
            "OUser": creator,
            "Turn": invitee,
            "OpponentId": invitee
        }
        try:
            self.gamesTable.put_item(Item=item)
            return True
        except ClientError as e:
            print("Error creating new game: {}".format(e))
            return False

    def checkIfTableIsActive(self):
        try:
            description = self.dynamodb.meta.client.describe_table(TableName=self.gamesTable.name)
            status = description['Table']['TableStatus']
            return status == "ACTIVE"
        except ClientError as e:
            print("Error checking table status: {}".format(e))
            return False

    def getGame(self, gameId):
        try:
            response = self.gamesTable.get_item(Key={"GameId": gameId})
            return response.get('Item', None)
        except ClientError as e:
            print("Error retrieving game: {}".format(e))
            return None

    def acceptGameInvite(self, game):
        date = str(datetime.now())
        status = "IN_PROGRESS_"
        statusDate = status + date
        key = {"GameId": game["GameId"]}
        update_expression = "SET StatusDate = :statusDate"
        condition_expression = "begins_with(StatusDate, :pending)"
        expression_attribute_values = {
            ":statusDate": statusDate,
            ":pending": "PENDING_"
        }
        try:
            self.gamesTable.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ConditionExpression=condition_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return True
        except ClientError as e:
            print("Error accepting game invite: {}".format(e))
            return False

    def rejectGameInvite(self, game):
        key = {"GameId": game["GameId"]}
        condition_expression = "begins_with(StatusDate, :pending)"
        expression_attribute_values = {":pending": "PENDING_"}
        try:
            self.gamesTable.delete_item(
                Key=key,
                ConditionExpression=condition_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return True
        except ClientError as e:
            print("Error rejecting game invite: {}".format(e))
            return False

    def getGameInvites(self, user):
        if user is None:
            return []
        try:
            response = self.gamesTable.query(
                IndexName="OpponentId-StatusDate-index",
                KeyConditionExpression="OpponentId = :user AND begins_with(StatusDate, :status)",
                ExpressionAttributeValues={
                    ":user": user,
                    ":status": "PENDING_"
                },
                Limit=10
            )
            return response.get('Items', [])
        except ClientError as e:
            print("Error getting game invites: {}".format(e))
            return []

    def updateBoardAndTurn(self, item, position, current_player):
        player_one = item["HostId"]
        player_two = item["OpponentId"]
        gameId = item["GameId"]
        statusDate = item["StatusDate"]
        date = statusDate.split("_")[1]

        representation = "X" if item["OUser"] == current_player else "O"
        next_player = player_two if current_player == player_one else player_one

        key = {"GameId": gameId}
        update_expression = "SET {} = :representation, Turn = :next_player".format(position)
        condition_expression = "begins_with(StatusDate, :in_progress) AND Turn = :current_player AND attribute_not_exists({})".format(position)
        expression_attribute_values = {
            ":representation": representation,
            ":next_player": next_player,
            ":in_progress": "IN_PROGRESS_",
            ":current_player": current_player
        }

        try:
            self.gamesTable.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ConditionExpression=condition_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return True
        except ClientError as e:
            print("Error updating board and turn: {}".format(e))
            return False

    def getBoardState(self, item):
        squares = ["TopLeft", "TopMiddle", "TopRight", "MiddleLeft", "MiddleMiddle", "MiddleRight",
                   "BottomLeft", "BottomMiddle", "BottomRight"]
        return [item.get(square, " ") for square in squares]

    def checkForGameResult(self, board, item, current_player):
        yourMarker = "X" if current_player == item["OUser"] else "O"
        theirMarker = "O" if yourMarker == "X" else "X"

        winConditions = [[0, 3, 6], [0, 1, 2], [0, 4, 8],
                         [1, 4, 7], [2, 5, 8], [2, 4, 6],
                         [3, 4, 5], [6, 7, 8]]

        for winCondition in winConditions:
            if all(board[i] == yourMarker for i in winCondition):
                return "Win"
            if all(board[i] == theirMarker for i in winCondition):
                return "Lose"

        if self.checkForTie(board):
            return "Tie"

        return None

    def checkForTie(self, board):
        return all(cell != " " for cell in board)

    def changeGameToFinishedState(self, item, result, current_user):
        if item.get("Result"):
            return True

        date = str(datetime.now())
        status = "FINISHED_" + date

        item["StatusDate"] = status
        item["Turn"] = "N/A"
        if result == "Tie":
            item["Result"] = result
        elif result == "Win":
            item["Result"] = current_user
        else:
            item["Result"] = item["OpponentId"] if item["HostId"] == current_user else item["HostId"]

        try:
            self.gamesTable.put_item(Item=item)
            return True
        except ClientError as e:
            print("Error changing game to finished state: {}".format(e))
            return False

    def mergeQueries(self, host, opp, limit=10):
        games = []
        try:
            while len(games) < limit:
                try:
                    game_one = next(host)
                except StopIteration:
                    for game in opp:
                        if len(games) == limit:
                            break
                        games.append(game)
                    return games

                try:
                    game_two = next(opp)
                except StopIteration:
                    for game in host:
                        if len(games) == limit:
                            break
                        games.append(game)
                    return games

                if game_one > game_two:
                    games.append(game_one)
                else:
                    games.append(game_two)

        except StopIteration:
            pass

        return games

    def getGamesWithStatus(self, user, status):
        if user is None:
            return []
        try:
            hostGamesInProgress = self.gamesTable.query(
                IndexName="HostId-StatusDate-index",
                KeyConditionExpression="HostId = :user AND begins_with(StatusDate, :status)",
                ExpressionAttributeValues={
                    ":user": user,
                    ":status": status
                },
                Limit=10
            )

            oppGamesInProgress = self.gamesTable.query(
                IndexName="OpponentId-StatusDate-index",
                KeyConditionExpression="OpponentId = :user AND begins_with(StatusDate, :status)",
                ExpressionAttributeValues={
                    ":user": user,
                    ":status": status
                },
                Limit=10
            )

            games = self.mergeQueries(iter(hostGamesInProgress['Items']), iter(oppGamesInProgress['Items']))
            return games
        except ClientError as e:
            print("Error getting games with status: {}".format(e))
            return []
