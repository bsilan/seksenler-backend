# Seksenler — Ürün Durumu ve Yol Haritası

Bu doküman, backend'in şu anki gerçek durumunu ve MVP'ye giden yolda öncelik sıralı eksik listesini özetler. PM tarafında kod okumadan karar verebilmek için hazırlandı.

## 1. Şu An Ne Var (main.py, 100 satır)

Çalışan uçlar:
- `POST /create_game` — oda kurar, kurucuyu oyuncu olarak ekler.
- `POST /join_game/{game_id}` — odaya oyuncu ekler (nickname çakışması kontrolü var).
- `GET /lobby/{game_id}` — lobideki oyuncu listesini döner.
- `POST /start_game/{game_id}` — oyunu "başladı" olarak işaretler.
- `GET /rules` — `rules.json` içeriğini döner (statik kural metni, oyun mantığına bağlı değil).

Veri saklama: **tamamen bellekte** (`games: Dict[str, Game]`). Sunucu yeniden başlarsa (deploy, crash, restart) tüm oyunlar kaybolur. Şu an için bu MVP'de kabul edilebilir bir trade-off, ama kullanıcıya söylenmesi gereken bir sınırlama.

## 2. Kritik Eksik: Oyunun Kendisi Yok

`rules.json` oyunun kurallarını tarif ediyor (Kenan Evren/Darbeciler/Demokratlar rolleri, tur akışı, kazanma koşulları, özel yetkiler) ama **hiçbiri `main.py`'de uygulanmamış**:

- `start_game` içinde rol atama yorum satırı olarak duruyor (`# --- ROL DAĞITIMI BURADA YAPILACAK ---`), gerçekte hiçbir role atanmıyor.
- Tur akışı (Cumhurbaşkanı seçimi → Başbakan adayı → Oylama → Yasa kartı → yürürlük → özel yetkiler) hiç yok.
- Kazanma koşulu kontrolü yok.
- Özel yetkiler (sorgulama, ihraç, doğrudan başbakan seçimi, kaos modu) yok.

Yani bugün bu backend ile **oda kurup insanları bir araya getirebilirsin ama oyun oynanamaz.**

## 3. Öncelik Sıralı Backlog (MVP'ye giden yol)

| # | Özellik | Neden bu sırada |
|---|---|---|
| 1 | ✅ **Rol atama** (`start_game` içinde) — TAMAMLANDI | Oyuncu sayısına göre 1 Kenan Evren + 1-3 Darbeci + kalan Demokrat dağıtılıyor; her oyuncu `GET /my_role/{game_id}/{player_id}` ile kendi rolünü görüyor, Darbeciler takım arkadaşlarını biliyor. Min/max oyuncu ve geç katılım kontrolleri eklendi. |
| 2 | ✅ **Tur döngüsü — seçim + oylama** — TAMAMLANDI | Cumhurbaşkanlığı rotasyonu, Başbakan adayı gösterme (dönem sınırları ile), açık oylama ve kaos modu (3 başarısız seçimde en üstteki yasa otomatik yürürlüğe girer) Secret Hitler kurallarına birebir uygun çalışıyor. |
| 3 | ✅ **Yasa kartı seçimi** — TAMAMLANDI | 17 kartlık deste (6 Reform + 11 Sıkıyönetim), Cumhurbaşkanı 3 çeker 1 eler, Başbakan 2'den 1'ini yürürlüğe koyar; eller yalnızca sahibine görünür; deste bitince ıskarta karıştırılıp tazelenir. |
| 4 | ✅ **Kazanma koşulları** — TAMAMLANDI (infaz hariç) | 5 Reform → Demokratlar; 6 Sıkıyönetim → Darbeciler; 3+ Sıkıyönetim varken Kenan Evren Başbakan seçilirse → Darbeciler. "Kenan Evren öldürülür" koşulu infaz yetkisiyle birlikte gelecek (madde 5). |
| 5 | ✅ **Özel yetkiler + veto** — TAMAMLANDI | Oyuncu sayısına göre açılan yetkiler (kart gözetleme, sorgulama, özel seçim, infaz) Secret Hitler tablosuna birebir uygun; Kenan Evren infaz edilirse Demokratlar kazanır; ölü oyuncular oy/adaylık/rotasyon dışı; 5. Sıkıyönetim'den sonra veto hakkı (Başbakan önerir, Cumhurbaşkanı karar verir). Kaosla geçen kart yetki tetiklemez. **Backend artık Secret Hitler kural setinin eksiksiz bir uygulaması.** |
| 6 | **Frontend** (React — CORS ayarı zaten buna göre yapılmış) | Bugüne kadarki her şey API üzerinden test edilebilir (Postman/curl), ama gerçek kullanıcı testi için şart. |
| 7 | **Deploy** (`runtime.txt` mevcut — Heroku benzeri bir platforma hazırlanmış) | Gerçek kullanıcılarla test etmeden önce gerekli. |
| 8 | **Kalıcı veri saklama** (bellek yerine DB/Redis) | Tek sunucu, düşük kullanıcı sayısıyla MVP için ertelenebilir; çoklu kullanıcı / production için zorunlu hale gelir. |

## 4. Şimdi Ne Yapmalı (önerilen sıradaki adım)

Oyun mantığı (madde 1-5) tamamlandı ve uçtan uca test edildi. Sıradaki adım **madde 6: Frontend** — CORS ayarı React'e göre zaten hazır; `GET /game_state` polling ucu arayüzün ihtiyacı olan her şeyi veriyor.

## 5. Not Edilecek Riskler
- `CORS allow_origins=["*"]` — geliştirme için sorun değil, production'a çıkmadan önce daraltılmalı.
- Eski/terk edilmiş oyunlar için hiçbir temizleme mekanizması yok — bellek zamanla şişebilir.
