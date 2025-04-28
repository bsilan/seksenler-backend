from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import uuid
from typing import List, Dict, Optional

app = FastAPI()

# CORS ayarları (React frontend için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kuralları yükle
RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")
with open(RULES_PATH, "r", encoding="utf-8") as f:
    RULES = json.load(f)

# --- MODELLER ---
class Player(BaseModel):
    id: str
    nickname: str
    role: Optional[str] = None
    is_creator: bool = False

class Game(BaseModel):
    id: str
    players: List[Player]
    started: bool = False
    roles_assigned: bool = False
    creator_id: str

# --- BELLEKTE ODA TUTUCU ---
games: Dict[str, Game] = {}

@app.get("/rules")
def get_rules():
    return RULES

@app.get("/")
def root():
    return {"message": "Seksenler oyun API'si çalışıyor!"}

@app.post("/create_game")
async def create_game(request: Request):
    data = await request.json()
    creator_nickname = data.get("nickname", "Kurucu")
    game_id = str(uuid.uuid4())[:8]
    player_id = str(uuid.uuid4())
    creator = Player(id=player_id, nickname=creator_nickname, is_creator=True)
    game = Game(id=game_id, players=[creator], creator_id=player_id)
    games[game_id] = game
    return {"game_id": game_id, "player_id": player_id}

@app.post("/join_game/{game_id}")
async def join_game(game_id: str, request: Request):
    data = await request.json()
    nickname = data.get("nickname")
    if not nickname:
        raise HTTPException(status_code=400, detail="Nickname gerekli.")
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Oyun bulunamadı.")
    if any(p.nickname == nickname for p in game.players):
        raise HTTPException(status_code=400, detail="Bu nickname zaten kullanılıyor.")
    player_id = str(uuid.uuid4())
    player = Player(id=player_id, nickname=nickname)
    game.players.append(player)
    return {"player_id": player_id}

@app.get("/lobby/{game_id}")
def get_lobby(game_id: str):
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Oyun bulunamadı.")
    return {
        "players": [{"nickname": p.nickname, "is_creator": p.is_creator} for p in game.players],
        "started": game.started,
        "roles_assigned": game.roles_assigned,
        "creator_id": game.creator_id
    }

@app.post("/start_game/{game_id}")
def start_game(game_id: str):
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Oyun bulunamadı.")
    if game.started:
        raise HTTPException(status_code=400, detail="Oyun zaten başladı.")
    # --- ROL DAĞITIMI BURADA YAPILACAK ---
    # (Şimdilik sadece started ve roles_assigned güncelleniyor)
    game.started = True
    game.roles_assigned = True
    return {"success": True} 