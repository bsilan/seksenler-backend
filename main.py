from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import random
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

# Yasa kartları
REFORM = "Demokrasi Reformu"
SIKIYONETIM = "Sıkıyönetim Kararı"

class Game(BaseModel):
    id: str
    players: List[Player]
    started: bool = False
    roles_assigned: bool = False
    creator_id: str
    # Oyun döngüsü durumu
    phase: str = "lobby"  # lobby | nomination | voting | president_cards | chancellor_cards | game_over
    deck: List[str] = []
    discard: List[str] = []
    enacted_reform: int = 0
    enacted_sikiyonetim: int = 0
    president_index: int = 0
    president_id: Optional[str] = None
    nominee_id: Optional[str] = None
    chancellor_id: Optional[str] = None
    last_president_id: Optional[str] = None
    last_chancellor_id: Optional[str] = None
    election_tracker: int = 0
    votes: Dict[str, bool] = {}
    last_election: Optional[Dict] = None
    president_hand: List[str] = []
    chancellor_hand: List[str] = []
    winner: Optional[str] = None
    win_reason: Optional[str] = None

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
    if game.started:
        raise HTTPException(status_code=400, detail="Oyun başladı, katılım kapalı.")
    if len(game.players) >= RULES["players"]["max"]:
        raise HTTPException(status_code=400, detail="Oda dolu.")
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

# Oyuncu sayısına göre Darbeci sayısı (Kenan Evren hariç)
DARBECI_SAYISI = {5: 1, 6: 1, 7: 2, 8: 2, 9: 3, 10: 3}

def assign_roles(players: List[Player]):
    count = len(players)
    darbeci_count = DARBECI_SAYISI[count]
    roles = ["Kenan Evren"] + ["Darbeci"] * darbeci_count
    roles += ["Demokrat"] * (count - len(roles))
    random.shuffle(roles)
    for player, role in zip(players, roles):
        player.role = role

@app.post("/start_game/{game_id}")
def start_game(game_id: str):
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Oyun bulunamadı.")
    if game.started:
        raise HTTPException(status_code=400, detail="Oyun zaten başladı.")
    min_players = RULES["players"]["min"]
    max_players = RULES["players"]["max"]
    if not (min_players <= len(game.players) <= max_players):
        raise HTTPException(
            status_code=400,
            detail=f"Oyun {min_players}-{max_players} oyuncu ile başlayabilir. Şu an {len(game.players)} oyuncu var.",
        )
    assign_roles(game.players)
    game.deck = [REFORM] * 6 + [SIKIYONETIM] * 11
    random.shuffle(game.deck)
    game.president_index = random.randrange(len(game.players))
    game.president_id = game.players[game.president_index].id
    game.phase = "nomination"
    game.started = True
    game.roles_assigned = True
    return {"success": True}

@app.get("/my_role/{game_id}/{player_id}")
def get_my_role(game_id: str, player_id: str):
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Oyun bulunamadı.")
    if not game.roles_assigned:
        raise HTTPException(status_code=400, detail="Roller henüz dağıtılmadı.")
    player = next((p for p in game.players if p.id == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Oyuncu bulunamadı.")
    result = {"role": player.role}
    # Darbeciler birbirini ve Kenan Evren'i bilir.
    if player.role == "Darbeci":
        result["teammates"] = [
            p.nickname for p in game.players
            if p.id != player.id and p.role in ("Darbeci", "Kenan Evren")
        ]
    # 5-6 kişilik oyunda Kenan Evren tek Darbeci'yi bilir; 7+ oyuncuda bilmez.
    elif player.role == "Kenan Evren" and len(game.players) <= 6:
        result["teammates"] = [p.nickname for p in game.players if p.role == "Darbeci"]
    return result

# --- OYUN DÖNGÜSÜ ---

def get_game(game_id: str) -> Game:
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Oyun bulunamadı.")
    return game

def find_player(game: Game, player_id: str) -> Player:
    player = next((p for p in game.players if p.id == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Oyuncu bulunamadı.")
    return player

def require_phase(game: Game, phase: str):
    if game.phase != phase:
        raise HTTPException(status_code=400, detail=f"Bu işlem şu an yapılamaz (faz: {game.phase}).")

def draw_cards(game: Game, n: int) -> List[str]:
    # Destede 3'ten az kart kalınca ıskarta karıştırılıp desteye eklenir.
    if len(game.deck) < 3:
        game.deck += game.discard
        game.discard = []
        random.shuffle(game.deck)
    drawn = game.deck[:n]
    game.deck = game.deck[n:]
    return drawn

def advance_presidency(game: Game):
    game.president_index = (game.president_index + 1) % len(game.players)
    game.president_id = game.players[game.president_index].id
    game.nominee_id = None
    game.chancellor_id = None
    game.votes = {}
    game.phase = "nomination"

def end_game(game: Game, winner: str, reason: str):
    game.winner = winner
    game.win_reason = reason
    game.phase = "game_over"

def enact_policy(game: Game, card: str):
    if card == REFORM:
        game.enacted_reform += 1
        if game.enacted_reform >= 5:
            end_game(game, "Demokratlar", "5 Demokrasi Reformu yürürlüğe girdi.")
            return
    else:
        game.enacted_sikiyonetim += 1
        if game.enacted_sikiyonetim >= 6:
            end_game(game, "Darbeciler", "6 Sıkıyönetim Kararı yürürlüğe girdi.")
            return
    advance_presidency(game)

@app.post("/nominate/{game_id}")
async def nominate(game_id: str, request: Request):
    data = await request.json()
    game = get_game(game_id)
    require_phase(game, "nomination")
    if data.get("president_id") != game.president_id:
        raise HTTPException(status_code=403, detail="Sadece Cumhurbaşkanı aday gösterebilir.")
    nominee = find_player(game, data.get("nominee_id"))
    if nominee.id == game.president_id:
        raise HTTPException(status_code=400, detail="Cumhurbaşkanı kendini aday gösteremez.")
    # Dönem sınırı: son seçilen Başbakan aday olamaz; 6+ oyuncuda son Cumhurbaşkanı da olamaz.
    if nominee.id == game.last_chancellor_id:
        raise HTTPException(status_code=400, detail="Son seçilen Başbakan tekrar aday gösterilemez.")
    if len(game.players) > 5 and nominee.id == game.last_president_id:
        raise HTTPException(status_code=400, detail="Son seçilen Cumhurbaşkanı Başbakan adayı olamaz.")
    game.nominee_id = nominee.id
    game.votes = {}
    game.phase = "voting"
    return {"success": True}

@app.post("/vote/{game_id}")
async def vote(game_id: str, request: Request):
    data = await request.json()
    game = get_game(game_id)
    require_phase(game, "voting")
    player = find_player(game, data.get("player_id"))
    if player.id in game.votes:
        raise HTTPException(status_code=400, detail="Zaten oy kullandın.")
    v = data.get("vote")
    if not isinstance(v, bool):
        raise HTTPException(status_code=400, detail="Oy true/false olmalı.")
    game.votes[player.id] = v
    if len(game.votes) < len(game.players):
        return {"success": True, "waiting": len(game.players) - len(game.votes)}
    # Herkes oy verdi: sonucu çözümle. Oylar açıklanır (Secret Hitler'de oylar açıktır).
    yes = sum(1 for x in game.votes.values() if x)
    passed = yes > len(game.players) - yes
    nickname_of = {p.id: p.nickname for p in game.players}
    game.last_election = {
        "nominee": nickname_of[game.nominee_id],
        "votes": {nickname_of[pid]: v for pid, v in game.votes.items()},
        "passed": passed,
    }
    if passed:
        game.chancellor_id = game.nominee_id
        game.last_president_id = game.president_id
        game.last_chancellor_id = game.chancellor_id
        game.election_tracker = 0
        chancellor = find_player(game, game.chancellor_id)
        # 3+ Sıkıyönetim varken Kenan Evren Başbakan seçilirse Darbeciler kazanır.
        if game.enacted_sikiyonetim >= 3 and chancellor.role == "Kenan Evren":
            end_game(game, "Darbeciler", "Kenan Evren Başbakan seçildi.")
            return {"success": True, "result": game.last_election}
        game.president_hand = draw_cards(game, 3)
        game.phase = "president_cards"
    else:
        game.election_tracker += 1
        if game.election_tracker >= 3:
            # Kaos: destenin en üstündeki kart otomatik yürürlüğe girer,
            # sayaç ve dönem sınırları sıfırlanır.
            card = draw_cards(game, 1)[0]
            game.election_tracker = 0
            game.last_president_id = None
            game.last_chancellor_id = None
            enact_policy(game, card)
        else:
            advance_presidency(game)
    return {"success": True, "result": game.last_election}

@app.post("/president_discard/{game_id}")
async def president_discard(game_id: str, request: Request):
    data = await request.json()
    game = get_game(game_id)
    require_phase(game, "president_cards")
    if data.get("president_id") != game.president_id:
        raise HTTPException(status_code=403, detail="Sadece Cumhurbaşkanı kart eleyebilir.")
    idx = data.get("card_index")
    if not isinstance(idx, int) or not (0 <= idx < len(game.president_hand)):
        raise HTTPException(status_code=400, detail="Geçersiz kart seçimi.")
    game.discard.append(game.president_hand.pop(idx))
    game.chancellor_hand = game.president_hand
    game.president_hand = []
    game.phase = "chancellor_cards"
    return {"success": True}

@app.post("/chancellor_enact/{game_id}")
async def chancellor_enact(game_id: str, request: Request):
    data = await request.json()
    game = get_game(game_id)
    require_phase(game, "chancellor_cards")
    if data.get("chancellor_id") != game.chancellor_id:
        raise HTTPException(status_code=403, detail="Sadece Başbakan yasa seçebilir.")
    idx = data.get("card_index")
    if not isinstance(idx, int) or not (0 <= idx < len(game.chancellor_hand)):
        raise HTTPException(status_code=400, detail="Geçersiz kart seçimi.")
    card = game.chancellor_hand.pop(idx)
    game.discard += game.chancellor_hand
    game.chancellor_hand = []
    enact_policy(game, card)
    return {"success": True, "enacted": card}

@app.get("/game_state/{game_id}/{player_id}")
def get_game_state(game_id: str, player_id: str):
    game = get_game(game_id)
    player = find_player(game, player_id)
    nickname_of = {p.id: p.nickname for p in game.players}
    state = {
        "phase": game.phase,
        "players": [{"nickname": p.nickname, "is_creator": p.is_creator} for p in game.players],
        "president": nickname_of.get(game.president_id),
        "nominee": nickname_of.get(game.nominee_id),
        "chancellor": nickname_of.get(game.chancellor_id),
        # Dönem sınırı: frontend'in aday gösterilemeyecekleri işaretleyebilmesi için
        "last_president": nickname_of.get(game.last_president_id),
        "last_chancellor": nickname_of.get(game.last_chancellor_id),
        "enacted_reform": game.enacted_reform,
        "enacted_sikiyonetim": game.enacted_sikiyonetim,
        "election_tracker": game.election_tracker,
        "deck_count": len(game.deck),
        "last_election": game.last_election,
        "winner": game.winner,
        "win_reason": game.win_reason,
        "is_president": player.id == game.president_id,
        "is_chancellor": player.id == game.chancellor_id,
        "voted": player.id in game.votes,
        "votes_in": len(game.votes),
    }
    # Eller sadece sahibine gösterilir.
    if game.phase == "president_cards" and player.id == game.president_id:
        state["your_hand"] = game.president_hand
    elif game.phase == "chancellor_cards" and player.id == game.chancellor_id:
        state["your_hand"] = game.chancellor_hand
    return state 