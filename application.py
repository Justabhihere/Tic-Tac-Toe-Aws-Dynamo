import sys
import os
from flask import Flask, render_template, request, session, flash, redirect, jsonify, json
from uuid import uuid4
from configparser import ConfigParser
import argparse
import time

# Append the path of the dynamodb directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'dynamodb'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))
from dynamodb.connectionManager import ConnectionManager
from dynamodb.gameController import GameController
from models.game import Game

from models.game import Game

application = Flask(__name__)
application.debug = True
application.secret_key = str(uuid4())

cm = None

parser = argparse.ArgumentParser(description='Run the TicTacToe sample app', prog='application.py')
parser.add_argument('--config', help='Path to the config file containing application settings.')
parser.add_argument('--mode', help='Whether to connect to a DynamoDB service endpoint, or to connect to DynamoDB Local.',
                    choices=['local', 'service'], default='service')
parser.add_argument('--endpoint', help='An endpoint to connect to.')
parser.add_argument('--port', help='The port of DynamoDB Local endpoint to connect to.', type=int)
parser.add_argument('--serverPort', help='The port for this Flask web server to listen on.', type=int)
args = parser.parse_args()

configFile = args.config
config = None
if 'CONFIG_FILE' in os.environ:
    if configFile is not None:
        raise Exception('Cannot specify --config when setting the CONFIG_FILE environment variable')
    configFile = os.environ['CONFIG_FILE']
if configFile is not None:
    config = ConfigParser()
    config.read(configFile)

use_instance_metadata = ""
if 'USE_EC2_INSTANCE_METADATA' in os.environ:
    use_instance_metadata = os.environ['USE_EC2_INSTANCE_METADATA']

cm = ConnectionManager(mode=args.mode, config=config, endpoint=args.endpoint, port=args.port, use_instance_metadata=use_instance_metadata)
controller = GameController(cm)

serverPort = args.serverPort
if config is not None:
    if config.has_option('flask', 'secret_key'):
        application.secret_key = config.get('flask', 'secret_key')
    if serverPort is None:
        if config.has_option('flask', 'serverPort'):
            serverPort = config.get('flask', 'serverPort')

if 'SERVER_PORT' in os.environ:
    serverPort = int(os.environ['SERVER_PORT'])

if serverPort is None:
    serverPort = 5000

@application.route('/logout')
def logout():
    session["username"] = None
    return redirect("/index")

@application.route('/table', methods=["GET", "POST"])
def createTable():
    cm.createGamesTable()
    while not controller.checkIfTableIsActive():
        time.sleep(3)
    return redirect('/index')

@application.route('/')
@application.route('/index', methods=["GET", "POST"])
def index():
    if session == {} or session.get("username", None) is None:
        form = request.form
        if form:
            formInput = form["username"]
            if formInput and formInput.strip():
                session["username"] = request.form["username"]
            else:
                session["username"] = None
        else:
            session["username"] = None

    if request.method == "POST":
        return redirect('/index')

    inviteGames = controller.getGameInvites(session.get("username"))
    if inviteGames is None:
        flash("Table has not been created yet, please follow this link to create table.")
        return render_template("table.html", user="")

    inviteGames = [Game(inviteGame) for inviteGame in inviteGames]

    inProgressGames = controller.getGamesWithStatus(session.get("username"), "IN_PROGRESS")
    inProgressGames = [Game(inProgressGame) for inProgressGame in inProgressGames]

    finishedGames = controller.getGamesWithStatus(session.get("username"), "FINISHED")
    fs = [Game(finishedGame) for finishedGame in finishedGames]

    return render_template("index.html",
                           user=session["username"],
                           invites=inviteGames,
                           inprogress=inProgressGames,
                           finished=fs)

@application.route('/create')
def create():
    if session.get("username", None) is None:
        flash("Need to login to create game")
        return redirect("/index")
    return render_template("create.html", user=session["username"])

@application.route('/play', methods=["POST"])
def play():
    form = request.form
    if form:
        creator = session["username"]
        gameId = str(uuid4())
        invitee = form["invitee"].strip()

        if not invitee or creator == invitee:
            flash("Use valid a name (not empty or your name)")
            return redirect("/create")

        if controller.createNewGame(gameId, creator, invitee):
            return redirect("/game={}".format(gameId))

    flash("Something went wrong creating the game.")
    return redirect("/create")

@application.route('/game=<gameId>')
def game(gameId):
    if session.get("username", None) is None:
        flash("Need to login")
        return redirect("/index")

    item = controller.getGame(gameId)
    if item is None:
        flash("That game does not exist.")
        return redirect("/index")

    boardState = controller.getBoardState(item)
    result = controller.checkForGameResult(boardState, item, session["username"])

    if result is not None:
        if not controller.changeGameToFinishedState(item, result, session["username"]):
            flash("Some error occurred while trying to finish game.")

    game = Game(item)
    status = game.status
    turn = game.turn

    if game.getResult(session["username"]) is None:
        if turn == game.o:
            turn += " (O)"
        else:
            turn += " (X)"

    gameData = {'gameId': gameId, 'status': game.status, 'turn': game.turn, 'board': boardState}
    gameJson = json.dumps(gameData)
    return render_template("play.html",
                           gameId=gameId,
                           gameJson=gameJson,
                           user=session["username"],
                           status=status,
                           turn=turn,
                           opponent=game.getOpposingPlayer(session["username"]),
                           result=result,
                           TopLeft=boardState[0],
                           TopMiddle=boardState[1],
                           TopRight=boardState[2],
                           MiddleLeft=boardState[3],
                           MiddleMiddle=boardState[4],
                           MiddleRight=boardState[5],
                           BottomLeft=boardState[6],
                           BottomMiddle=boardState[7],
                           BottomRight=boardState[8])

@application.route('/gameData=<gameId>')
def gameData(gameId):
    item = controller.getGame(gameId)
    boardState = controller.getBoardState(item)
    if item is None:
        return jsonify(error='That game does not exist')

    game = Game(item)
    return jsonify(gameId=gameId,
                   status=game.status,
                   turn=game.turn,
                   board=boardState)

@application.route('/accept=<invite>', methods=["POST"])
def accept(invite):
    gameId = request.form["response"]
    game = controller.getGame(gameId)

    if game is None:
        flash("That game does not exist anymore.")
        return redirect("/index")

    if not controller.acceptGameInvite(game):
        flash("Error validating the game...")
        return redirect("/index")

    return redirect(f"/game={game['GameId']}")

@application.route('/reject=<invite>', methods=["POST"])
def reject(invite):
    gameId = request.form["response"]
    game = controller.getGame(gameId)

    if game is None:
        flash("That game doesn't exist anymore.")
        return redirect("/index")

    if not controller.rejectGameInvite(game):
        flash("Something went wrong when deleting invite.")
        return redirect("/index")

    return redirect("/index")

@application.route('/select=<gameId>', methods=["POST"])
def selectSquare(gameId):
    value = request.form["cell"]

    item = controller.getGame(gameId)
    if item is None:
        flash("This is not a valid game.")
        return redirect("/index")

    if not controller.updateBoardAndTurn(item, value, session["username"]):
        flash("You have selected a square either when it's not your turn, the square is already selected, or the game is not 'In-Progress'.",
              "updateError")
        return redirect(f"/game={gameId}")

    return redirect(f"/game={gameId}")

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=serverPort)
