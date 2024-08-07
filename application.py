import sys
import os
import json
import argparse
import time
from flask import Flask, render_template, request, session, flash, redirect, jsonify
from uuid import uuid4
from ConfigParser import ConfigParser  # Note the change in import name
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'dynamodb'))
from dynamodb.connectionManager import ConnectionManager
from dynamodb.gameController import GameController
from models.game import Game

application = Flask(__name__)
application.debug = True
application.secret_key = str(uuid4())

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
            formInput = form.get("username")
            if formInput and formInput.strip():
                session["username"] = formInput
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
        invitee = form.get("invitee", "").strip()

        if not invitee or creator == invitee:
            flash("Use valid a name (not empty or your name)")
            return redirect("/create")

        if controller.createNewGame(gameId, creator, invitee):
            return redirect("/game=%s" % gameId)

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
            flash("Some error occurred while trying to finish the game.")

    game = Game(item)
    status = game.status
    turn = game.turn

    # Safe access to 'Result' key
    result = game.getResult(session.get("username"))
    if result is None:
        result = "No result available"  # Handle missing Result key

    if turn == game.o:
        turn += " (O)"
    else:
        turn += " (X)"

    gameData = {
        'gameId': gameId,
        'status': game.status,
        'turn': game.turn,
        'board': boardState
    }
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


@application.route('/update', methods=["POST"])
def update():
    form = request.form
    if form:
        gameId = form.get("gameId")
        position = form.get("position")
        marker = form.get("marker")

        if controller.updateGameState(gameId, int(position), marker):
            return jsonify(success=True)

    return jsonify(success=False)

@application.route('/accept/<gameId>', methods=['POST'])
def accept_game(gameId):
    if session.get("username") is None:
        flash("You need to log in first.")
        return redirect("/index")
    
    game = controller.getGame(gameId)
    if game is None:
        flash("Game not found.")
        return redirect("/index")
    
    if controller.acceptGameInvite(game):
        return redirect("/game=%s" % gameId)
    else:
        flash("Error accepting game invite.")
        return redirect("/index")

@application.route('/reject/<gameId>', methods=['POST'])
def reject_game(gameId):
    if session.get("username") is None:
        flash("You need to log in first.")
        return redirect("/index")
    
    game = controller.getGame(gameId)
    if game is None:
        flash("Game not found.")
        return redirect("/index")
    
    # Implement your rejection logic here
    flash("Game invite rejected.")
    return redirect("/index")

if __name__ == '__main__':
    application.run(host='0.0.0.0', port=serverPort)
