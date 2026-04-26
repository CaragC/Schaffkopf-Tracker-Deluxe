import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "schafkopf_daten_final.json"

class SchafkopfData:
    def __init__(self):
        self.data = self.load_data()
        self.session_players = []
        self.active_players = []
        self.rotation_index = 0
        self.session_history = []
        self.t_sau = 10
        self.t_solo = 20

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    if "players" not in d: d = {"players": {}, "global_history": []}
                    return d
            except:
                pass
        return {"players": {}, "global_history": []}

    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def add_player(self, name):
        name = name.strip()
        if name and name not in self.data["players"]:
            self.data["players"][name] = {
                "global_score": 0, "soli_played": 0, "soli_won": 0,
                "total_games_as_ansager": 0, "total_wins_as_ansager": 0
            }
            self.save_data()
            return True
        return False

    def get_all_players(self):
        return sorted(list(self.data["players"].keys()))

    def start_session(self, players: list):
        if len(players) < 4:
            raise ValueError("Mindestens 4 Spieler erforderlich")
        self.session_players = players
        self.rotation_index = 0
        self.active_players = self.session_players[:4]
        self.session_history = []

    def set_tarife(self, t_sau: int, t_solo: int):
        self.t_sau = t_sau
        self.t_solo = t_solo

    def record_game(self, game_type, winners, ansager, laufende, status):
        base_points = self.t_solo if game_type in ["Solo", "Wenz", "Geier"] else self.t_sau
        round_scores = {p: 0 for p in self.session_players}
        laufende_val = int(laufende)

        if status == "Sie (Alle Stiche)":
            multiplier = (1 + 4 + 2) * 2
        elif status == "Schwarz":
            multiplier = 1 + laufende_val + 2
        elif status == "Schneider":
            multiplier = 1 + laufende_val + 1
        else:
            multiplier = 1 + laufende_val

        total_points = multiplier * base_points
        losers_at_table = [p for p in self.active_players if p not in winners]

        if game_type == "Ramsch":
            if len(winners) == 3:
                verlierer = losers_at_table[0]
                round_scores[verlierer] = -base_points * 3
                for w in winners: round_scores[w] = base_points
            elif len(winners) == 1:
                gewinner = winners[0]
                round_scores[gewinner] = base_points * 3
                for l in losers_at_table: round_scores[l] = -base_points

        elif game_type in ["Solo", "Wenz", "Geier"]:
            is_win = (ansager in winners)
            if is_win:
                round_scores[ansager] = total_points * 3
                for l in losers_at_table: round_scores[l] = -total_points
            else:
                round_scores[ansager] = -total_points * 3
                for w in winners: round_scores[w] = total_points

            p = self.data["players"][ansager]
            p["total_games_as_ansager"] += 1
            p["soli_played"] += 1
            if is_win:
                p["total_wins_as_ansager"] += 1
                p["soli_won"] += 1

        else:
            for w in winners: round_scores[w] = total_points
            for l in losers_at_table: round_scores[l] = -total_points

            p = self.data["players"][ansager]
            p["total_games_as_ansager"] += 1
            if ansager in winners: p["total_wins_as_ansager"] += 1

        for p, score in round_scores.items():
            if p in self.data["players"]:
                self.data["players"][p]["global_score"] += score

        self.session_history.append({"type": game_type, "scores": round_scores, "ansager": ansager})
        self.save_data()
        self.rotate_players()

    def rotate_players(self):
        n = len(self.session_players)
        if n > 4:
            self.rotation_index = (self.rotation_index + 1) % n
        self.active_players = [self.session_players[(self.rotation_index + i) % n] for i in range(4)]
        
    def get_state(self):
        return {
            "all_players": self.get_all_players(),
            "player_stats": self.data["players"],
            "session_players": self.session_players,
            "active_players": self.active_players,
            "session_history": self.session_history,
            "t_sau": self.t_sau,
            "t_solo": self.t_solo
        }

db = SchafkopfData()

class PlayerModel(BaseModel):
    name: str

class SessionStartModel(BaseModel):
    players: List[str]
    t_sau: int
    t_solo: int

class RecordGameModel(BaseModel):
    game_type: str
    winners: List[str]
    ansager: str
    laufende: int
    status: str

@app.get("/state")
def get_state():
    return db.get_state()

@app.post("/add_player")
def add_player(player: PlayerModel):
    success = db.add_player(player.name)
    if not success:
        raise HTTPException(status_code=400, detail="Spieler existiert bereits oder ungültiger Name")
    return {"status": "ok"}

@app.post("/start_session")
def start_session(session: SessionStartModel):
    try:
        db.start_session(session.players)
        db.set_tarife(session.t_sau, session.t_solo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}

@app.post("/record_game")
def record_game(game: RecordGameModel):
    db.record_game(game.game_type, game.winners, game.ansager, game.laufende, game.status)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
