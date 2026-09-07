
from flask import Flask, render_template, request, jsonify
import random
import json
import os


app = Flask(__name__)


# ============================================================
# SETTINGS
# ============================================================

LEARNING_ROUNDS = 10

MOVES = ["rock", "paper", "scissors"]

RESULTS = ["win", "lose", "draw"]

DATA_FILE = "data/game_data.json"


# ============================================================
# GAME STATE
# ============================================================

game = {
    "round": 0,
    "player_score": 0,
    "ai_score": 0,
    "draws": 0,

    "correct_predictions": 0,
    "total_predictions": 0,

    "history": []
}


# ============================================================
# BAYESIAN MODEL
# ============================================================

class BayesianRPS:

    def __init__(self):

        self.counts = {}

        self.initialize_counts()


    def initialize_counts(self):

        for computer_move in MOVES:

            self.counts[computer_move] = {}

            for result in RESULTS:

                # Laplace smoothing
                # Start every possibility at 1

                self.counts[computer_move][result] = {

                    "rock": 1,
                    "paper": 1,
                    "scissors": 1

                }


    # --------------------------------------------------------
    # UPDATE MODEL
    # --------------------------------------------------------

    def update(
        self,
        previous_computer_move,
        previous_result,
        player_move
    ):

        if previous_computer_move is None:
            return

        if previous_result is None:
            return

        self.counts[
            previous_computer_move
        ][
            previous_result
        ][
            player_move
        ] += 1


    # --------------------------------------------------------
    # PREDICT
    # --------------------------------------------------------

    def predict(
        self,
        previous_computer_move,
        previous_result
    ):

        if (
            previous_computer_move is None
            or previous_result is None
        ):

            return {
                "rock": 1 / 3,
                "paper": 1 / 3,
                "scissors": 1 / 3
            }


        counts = self.counts[
            previous_computer_move
        ][
            previous_result
        ]


        total = sum(counts.values())


        return {

            move: counts[move] / total

            for move in MOVES

        }


# Create model
model = BayesianRPS()


# ============================================================
# WINNER
# ============================================================

def determine_winner(player, computer):

    if player == computer:

        return "draw"


    if (

        (player == "rock" and computer == "scissors")

        or

        (player == "paper" and computer == "rock")

        or

        (player == "scissors" and computer == "paper")

    ):

        return "win"


    return "lose"


# ============================================================
# COUNTER MOVE
# ============================================================

def counter_move(move):

    counters = {

        "rock": "paper",

        "paper": "scissors",

        "scissors": "rock"

    }

    return counters[move]


# ============================================================
# SAVE DATA
# ============================================================

def save_data():

    directory = os.path.dirname(DATA_FILE)

    if directory:

        os.makedirs(
            directory,
            exist_ok=True
        )


    data = {

        "game": game,

        "bayesian_counts": model.counts

    }


    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    global game
    global model


    if not os.path.exists(DATA_FILE):

        return


    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)


        if "game" in data:

            game = data["game"]


        if "bayesian_counts" in data:

            model.counts = data[
                "bayesian_counts"
            ]


    except Exception as error:

        print(
            "Error loading data:",
            error
        )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "home.html"
    )


# ============================================================
# DATA VIEW PAGE
# ============================================================



# ============================================================
# PLAY
# ============================================================

@app.route(
    "/play",
    methods=["POST"]
)
def play():

    global game
    global model


    # --------------------------------------------------------
    # Get player move
    # --------------------------------------------------------

    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({
            "error": "No JSON data received"
        }), 400


    player_move = data.get(
        "move"
    )


    if player_move not in MOVES:

        return jsonify({
            "error": "Invalid move"
        }), 400


    # --------------------------------------------------------
    # Previous round information
    # --------------------------------------------------------

    previous_computer_move = None

    previous_result = None


    if game["history"]:

        previous_round = game[
            "history"
        ][-1]


        previous_computer_move = (
            previous_round["computer"]
        )


        previous_result = (
            previous_round["result"]
        )


    # --------------------------------------------------------
    # NEW ROUND
    # --------------------------------------------------------

    game["round"] += 1

    current_round = game["round"]


    # ========================================================
    # AFTER FIRST 10 ROUNDS:
    # CHECK MODEL'S PREVIOUS PREDICTION
    # ========================================================

    prediction_used = False

    predicted_move = None

    probabilities = {

        "rock": 1 / 3,

        "paper": 1 / 3,

        "scissors": 1 / 3

    }


    if current_round > LEARNING_ROUNDS:

        probabilities = model.predict(

            previous_computer_move,

            previous_result

        )


        predicted_move = max(
            probabilities,
            key=probabilities.get
        )


        # This prediction was made for
        # the current player's move.

        prediction_used = True


        # Compare prediction with actual move

        game[
            "total_predictions"
        ] += 1


        if predicted_move == player_move:

            game[
                "correct_predictions"
            ] += 1


    # ========================================================
    # CHOOSE COMPUTER MOVE
    # ========================================================

    if current_round <= LEARNING_ROUNDS:

        # FIRST 10 = RANDOM

        computer_move = random.choice(
            MOVES
        )

        phase = "learning"


    else:

        # AFTER 10 = COUNTER PREDICTION

        computer_move = counter_move(
            predicted_move
        )

        phase = "prediction"


    # ========================================================
    # RESULT
    # ========================================================

    result = determine_winner(

        player_move,

        computer_move

    )


    # ========================================================
    # SCORE
    # ========================================================

    if result == "win":

        game["player_score"] += 1


    elif result == "lose":

        game["ai_score"] += 1


    else:

        game["draws"] += 1


    # ========================================================
    # UPDATE BAYESIAN MODEL
    # ========================================================

    model.update(

        previous_computer_move,

        previous_result,

        player_move

    )


    # ========================================================
    # SAVE CURRENT ROUND
    # ========================================================

    game["history"].append({

        "round": current_round,

        "player": player_move,

        "computer": computer_move,

        "result": result

    })


    # ========================================================
    # SAVE TO FILE
    # ========================================================

    save_data()


    # ========================================================
    # ACCURACY
    # ========================================================

    if game["total_predictions"] > 0:

        accuracy = (

            game["correct_predictions"]

            /

            game["total_predictions"]

        ) * 100

    else:

        accuracy = 0


    # ========================================================
    # RESPONSE
    # ========================================================

    return jsonify({

        "round": current_round,

        "player": player_move,

        "computer": computer_move,

        "result": result,

        "phase": phase,

        "player_score":
            game["player_score"],

        "ai_score":
            game["ai_score"],

        "draws":
            game["draws"],

        "predicted_move":
            predicted_move,

        "probabilities":
            probabilities,

        "accuracy":
            round(
                accuracy,
                2
            )

    })


# ============================================================
# RESET
# ============================================================

@app.route(
    "/reset",
    methods=["POST"]
)
def reset():

    global game
    global model


    game = {

        "round": 0,

        "player_score": 0,

        "ai_score": 0,

        "draws": 0,

        "correct_predictions": 0,

        "total_predictions": 0,

        "history": []

    }


    model = BayesianRPS()


    save_data()


    return jsonify({

        "success": True

    })


# ============================================================
# DATA API
# ============================================================

@app.route("/data")
def data():

    if game["total_predictions"] > 0:

        accuracy = (

            game["correct_predictions"]

            /

            game["total_predictions"]

        ) * 100

    else:

        accuracy = 0


    return jsonify({

        "round":
            game["round"],

        "player_score":
            game["player_score"],

        "ai_score":
            game["ai_score"],

        "draws":
            game["draws"],

        "accuracy":
            round(
                accuracy,
                2
            ),

        "correct_predictions":
            game[
                "correct_predictions"
            ],

        "total_predictions":
            game[
                "total_predictions"
            ],

        "history":
            game["history"],

        "bayesian_counts":
            model.counts

    })


@app.route("/data-view")
def data_view_page():
    return render_template("data_view.html")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    load_data()

    app.run(
        debug=True
    )
