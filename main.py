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
    alive: bool = True

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
    # Özel yetkiler ve veto
    pending_power: Optional[str] = None
    investigated_ids: List[str] = []
    veto_unlocked: bool = False
    veto_rejected: bool = False
    special_election_return_index: Optional[int] = None
    power_log: List[Dict] = []

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

# Yasama yoluyla geçen N'inci Sıkıyönetim Kararı'nın açtığı yetki
# (oyun başındaki oyuncu sayısına göre)
POWERS = {
    5: {3: "peek", 4: "execute", 5: "execute"},
    6: {3: "peek", 4: "execute", 5: "execute"},
    7: {2: "investigate", 3: "special_election", 4: "execute", 5: "execute"},
    8: {2: "investigate", 3: "special_election", 4: "execute", 5: "execute"},
    9: {1: "investigate", 2: "investigate", 3: "special_election", 4: "execute", 5: "execute"},
    10: {1: "investigate", 2: "investigate", 3: "special_election", 4: "execute", 5: "execute"},
}

def alive_players(game: Game) -> List[Player]:
    return [p for p in game.players if p.alive]

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
    # Özel seçimden dönüş: rotasyon, yetkiyi kullanan Cumhurbaşkanı'nın solundan devam eder.
    if game.special_election_return_index is not None:
        game.president_index = game.special_election_return_index
        game.special_election_return_index = None
    # Ölü oyuncular rotasyonda atlanır.
    while True:
        game.president_index = (game.president_index + 1) % len(game.players)
        if game.players[game.president_index].alive:
            break
    game.president_id = game.players[game.president_index].id
    game.nominee_id = None
    game.chancellor_id = None
    game.votes = {}
    game.pending_power = None
    game.phase = "nomination"

def end_game(game: Game, winner: str, reason: str):
    game.winner = winner
    game.win_reason = reason
    game.phase = "game_over"

def enact_policy(game: Game, card: str, by_legislation: bool = True):
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
        if game.enacted_sikiyonetim >= 5:
            game.veto_unlocked = True
        # Kaosla (seçim sayacıyla) geçen kart yetki tetiklemez.
        if by_legislation:
            power = POWERS[len(game.players)].get(game.enacted_sikiyonetim)
            if power:
                game.pending_power = power
                game.phase = "executive_action"
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
    if not nominee.alive:
        raise HTTPException(status_code=400, detail="Ölü oyuncu aday gösterilemez.")
    if nominee.id == game.president_id:
        raise HTTPException(status_code=400, detail="Cumhurbaşkanı kendini aday gösteremez.")
    # Dönem sınırı: son seçilen Başbakan aday olamaz; 6+ canlı oyuncuda son Cumhurbaşkanı da olamaz.
    if nominee.id == game.last_chancellor_id:
        raise HTTPException(status_code=400, detail="Son seçilen Başbakan tekrar aday gösterilemez.")
    if len(alive_players(game)) > 5 and nominee.id == game.last_president_id:
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
    if not player.alive:
        raise HTTPException(status_code=400, detail="Ölü oyuncular oy kullanamaz.")
    if player.id in game.votes:
        raise HTTPException(status_code=400, detail="Zaten oy kullandın.")
    v = data.get("vote")
    if not isinstance(v, bool):
        raise HTTPException(status_code=400, detail="Oy true/false olmalı.")
    game.votes[player.id] = v
    alive_count = len(alive_players(game))
    if len(game.votes) < alive_count:
        return {"success": True, "waiting": alive_count - len(game.votes)}
    # Tüm canlılar oy verdi: sonucu çözümle. Oylar açıklanır (Secret Hitler'de oylar açıktır).
    yes = sum(1 for x in game.votes.values() if x)
    passed = yes > alive_count - yes
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
            enact_policy(game, card, by_legislation=False)
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
    game.veto_rejected = False
    enact_policy(game, card)
    return {"success": True, "enacted": card}

@app.post("/use_power/{game_id}")
async def use_power(game_id: str, request: Request):
    data = await request.json()
    game = get_game(game_id)
    require_phase(game, "executive_action")
    if data.get("president_id") != game.president_id:
        raise HTTPException(status_code=403, detail="Sadece Cumhurbaşkanı yetki kullanabilir.")
    power = game.pending_power
    president = find_player(game, game.president_id)
    nickname_of = {p.id: p.nickname for p in game.players}

    if power == "peek":
        # Destenin üstündeki 3 kart gizlice görülür (çekilmez).
        if len(game.deck) < 3:
            game.deck += game.discard
            game.discard = []
            random.shuffle(game.deck)
        cards = game.deck[:3]
        game.power_log.append({"power": "peek", "by": president.nickname})
        advance_presidency(game)
        return {"power": "peek", "cards": cards}

    target = find_player(game, data.get("target_id"))
    if not target.alive:
        raise HTTPException(status_code=400, detail="Hedef oyuncu ölü.")
    if target.id == game.president_id:
        raise HTTPException(status_code=400, detail="Cumhurbaşkanı kendini hedef alamaz.")

    if power == "investigate":
        if target.id in game.investigated_ids:
            raise HTTPException(status_code=400, detail="Bu oyuncu zaten sorgulandı.")
        game.investigated_ids.append(target.id)
        # Parti üyeliği: Kenan Evren de Darbeci görünür. Sonuç yalnızca bu yanıtta.
        party = "Darbeci" if target.role in ("Darbeci", "Kenan Evren") else "Demokrat"
        game.power_log.append({"power": "investigate", "by": president.nickname,
                               "target": target.nickname})
        advance_presidency(game)
        return {"power": "investigate", "target": target.nickname, "party": party}

    if power == "special_election":
        # Rotasyon bu turdan sonra, yetkiyi kullanan Cumhurbaşkanı'nın solundan devam eder.
        game.special_election_return_index = game.president_index
        game.president_index = game.players.index(target)
        game.president_id = target.id
        game.nominee_id = None
        game.chancellor_id = None
        game.votes = {}
        game.pending_power = None
        game.phase = "nomination"
        game.power_log.append({"power": "special_election", "by": president.nickname,
                               "target": target.nickname})
        return {"power": "special_election", "new_president": target.nickname}

    if power == "execute":
        target.alive = False
        game.power_log.append({"power": "execute", "by": president.nickname,
                               "target": target.nickname})
        if target.role == "Kenan Evren":
            end_game(game, "Demokratlar", "Kenan Evren infaz edildi.")
            return {"power": "execute", "target": target.nickname, "game_over": True}
        advance_presidency(game)
        return {"power": "execute", "target": target.nickname, "game_over": False}

    raise HTTPException(status_code=400, detail="Bekleyen yetki yok.")

@app.post("/propose_veto/{game_id}")
async def propose_veto(game_id: str, request: Request):
    data = await request.json()
    game = get_game(game_id)
    require_phase(game, "chancellor_cards")
    if data.get("chancellor_id") != game.chancellor_id:
        raise HTTPException(status_code=403, detail="Sadece Başbakan veto önerebilir.")
    if not game.veto_unlocked:
        raise HTTPException(status_code=400, detail="Veto hakkı henüz açılmadı (5 Sıkıyönetim gerekli).")
    if game.veto_rejected:
        raise HTTPException(status_code=400, detail="Veto bu tur zaten reddedildi; yasa koymak zorundasın.")
    game.phase = "veto_decision"
    return {"success": True}

@app.post("/veto_decision/{game_id}")
async def veto_decision(game_id: str, request: Request):
    data = await request.json()
    game = get_game(game_id)
    require_phase(game, "veto_decision")
    if data.get("president_id") != game.president_id:
        raise HTTPException(status_code=403, detail="Veto kararı Cumhurbaşkanı'nındır.")
    approve = data.get("approve")
    if not isinstance(approve, bool):
        raise HTTPException(status_code=400, detail="approve true/false olmalı.")
    if not approve:
        game.veto_rejected = True
        game.phase = "chancellor_cards"
        return {"success": True, "vetoed": False}
    # Veto kabul: eldeki kartlar ıskartaya, seçim sayacı ilerler (3 olursa kaos).
    game.discard += game.chancellor_hand
    game.chancellor_hand = []
    game.election_tracker += 1
    if game.election_tracker >= 3:
        card = draw_cards(game, 1)[0]
        game.election_tracker = 0
        game.last_president_id = None
        game.last_chancellor_id = None
        enact_policy(game, card, by_legislation=False)
    else:
        advance_presidency(game)
    return {"success": True, "vetoed": True}

@app.get("/game_state/{game_id}/{player_id}")
def get_game_state(game_id: str, player_id: str):
    game = get_game(game_id)
    player = find_player(game, player_id)
    nickname_of = {p.id: p.nickname for p in game.players}
    state = {
        "phase": game.phase,
        "players": [{"nickname": p.nickname, "is_creator": p.is_creator, "alive": p.alive}
                    for p in game.players],
        "pending_power": game.pending_power,
        "veto_unlocked": game.veto_unlocked,
        "power_log": game.power_log,
        "investigated": [nickname_of[pid] for pid in game.investigated_ids],
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