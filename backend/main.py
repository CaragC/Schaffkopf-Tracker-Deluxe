import json
import os
import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
        self.session_players = self.data.get("session_players", [])
        self.active_players = self.data.get("active_players", [])
        self.rotation_index = self.data.get("rotation_index", 0)
        self.session_history = self.data.get("session_history", [])
        self.t_sau = self.data.get("t_sau", 10)
        self.t_solo = self.data.get("t_solo", 20)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    if "players" not in d: d = {"players": {}, "games": []}
                    return d
            except:
                pass
        return {"players": {}, "games": []}

    def save_data(self):
        self.data["session_players"] = self.session_players
        self.data["active_players"] = self.active_players
        self.data["rotation_index"] = self.rotation_index
        self.data["session_history"] = self.session_history
        self.data["t_sau"] = self.t_sau
        self.data["t_solo"] = self.t_solo
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
        self.save_data()

    def set_tarife(self, t_sau: int, t_solo: int):
        self.t_sau = t_sau
        self.t_solo = t_solo
        self.save_data()

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

        match_record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "game_type": game_type,
            "ansager": ansager,
            "winners": winners,
            "laufende": laufende,
            "status": status,
            "scores": round_scores,
            "active_players": self.active_players.copy()
        }
        if "games" not in self.data:
            self.data["games"] = []
        self.data["games"].append(match_record)

        self.session_history.append({"type": game_type, "scores": round_scores, "ansager": ansager, "timestamp": match_record["timestamp"]})
        self.save_data()
        self.rotate_players()

    def rotate_players(self):
        n = len(self.session_players)
        if n > 4:
            self.rotation_index = (self.rotation_index + 1) % n
        self.active_players = [self.session_players[(self.rotation_index + i) % n] for i in range(4)]
        self.save_data()
        

    def recalculate_stats(self):
        # Reset current scores and stats
        for p in self.data["players"]:
            self.data["players"][p] = {
                "global_score": 0, "soli_played": 0, "soli_won": 0,
                "total_games_as_ansager": 0, "total_wins_as_ansager": 0
            }
        
        # Replay all history
        for match in self.data.get("games", []):
            game_type = match.get("game_type")
            winners = match.get("winners", [])
            ansager = match.get("ansager")
            round_scores = match.get("scores", {})
            active_players = match.get("active_players", [])
            
            for p, score in round_scores.items():
                if p in self.data["players"]:
                    self.data["players"][p]["global_score"] += score
                    
            if game_type in ["Solo", "Wenz", "Geier"]:
                is_win = (ansager in winners)
                p_stats = self.data["players"].get(ansager)
                if p_stats:
                    p_stats["total_games_as_ansager"] += 1
                    p_stats["soli_played"] += 1
                    if is_win:
                        p_stats["total_wins_as_ansager"] += 1
                        p_stats["soli_won"] += 1
            elif game_type and game_type != "Ramsch":
                p_stats = self.data["players"].get(ansager)
                if p_stats:
                    p_stats["total_games_as_ansager"] += 1
                    if ansager in winners: 
                        p_stats["total_wins_as_ansager"] += 1

    def delete_match(self, timestamp: str):
        if "games" not in self.data:
            return False
            
        initial_len = len(self.data["games"])
        self.data["games"] = [m for m in self.data["games"] if m.get("timestamp") != timestamp]
        
        if len(self.data["games"]) == initial_len:
            return False
            
        self.session_history = [m for m in self.session_history if m.get("timestamp") != timestamp]
        
        # Rotations-Index zurücksetzen, wenn es das letzte Spiel war (einfachheitshalber 1 Schritt zurück)
        n = len(self.session_players)
        if n > 4:
            self.rotation_index = (self.rotation_index - 1) % n
            self.active_players = [self.session_players[(self.rotation_index + i) % n] for i in range(4)]
            
        self.recalculate_stats()
        self.save_data()
        return True

    def reorder_players(self, new_order: list):
        if set(new_order) != set(self.session_players):
            raise ValueError("Neue Reihenfolge muss die gleichen Spieler enthalten")
        self.session_players = new_order
        n = len(self.session_players)
        self.active_players = [self.session_players[(self.rotation_index + i) % n] for i in range(min(4, n))]
        self.save_data()

    def set_active_players(self, players: list):
        if len(self.session_players) < 4:
            raise ValueError("Keine aktive Session vorhanden")

        expected_count = 4 if len(self.session_players) > 4 else len(self.session_players)
        if len(players) != expected_count:
            raise ValueError(f"Es müssen genau {expected_count} aktive Spieler gewählt werden")

        if len(set(players)) != len(players):
            raise ValueError("Spieler dürfen nicht doppelt gewählt werden")

        if any(p not in self.session_players for p in players):
            raise ValueError("Ungültige Spieler in aktiver Auswahl")

        selected = set(players)
        self.active_players = [p for p in self.session_players if p in selected]

        if len(self.session_players) > 4 and self.active_players:
            self.rotation_index = self.session_players.index(self.active_players[0])

        self.save_data()
        

    def get_state(self):


        return {
            "all_players": self.get_all_players(),
            "player_stats": self.data["players"],
            "session_players": self.session_players,
            "active_players": self.active_players,
            "session_history": self.session_history,
            "games": self.data.get("games", []),
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

class DeleteMatchModel(BaseModel):
    timestamp: str

class ReorderPlayersModel(BaseModel):
    players: List[str]


class SetActivePlayersModel(BaseModel):
    players: List[str]


class DeleteMatchModel(BaseModel):
    timestamp: str

class ReorderPlayersModel(BaseModel):
    players: List[str]


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

@app.post("/delete_match")
def delete_match(req: DeleteMatchModel):
    success = db.delete_match(req.timestamp)
    if not success:
        raise HTTPException(status_code=404, detail="Match nicht gefunden")
    return {"status": "ok"}

@app.post("/reorder_players")
def reorder_players(req: ReorderPlayersModel):
    try:
        db.reorder_players(req.players)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}


@app.post("/set_active_players")
def set_active_players(req: SetActivePlayersModel):
    try:
        db.set_active_players(req.players)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}



class DeletePlayerModel(BaseModel):
    name: str

class UpdatePlayerModel(BaseModel):
    name: str
    global_score: int

@app.post("/delete_player")
def delete_player(req: DeletePlayerModel):
    if req.name in db.data.get("players", {}):
        del db.data["players"][req.name]
        db.save_data()
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Player not found")

@app.post("/update_player_score")
def update_player_score(req: UpdatePlayerModel):
    if req.name in db.data.get("players", {}):
        db.data["players"][req.name]["global_score"] = req.global_score
        db.save_data()
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Player not found")

# Serve frontend statically
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
