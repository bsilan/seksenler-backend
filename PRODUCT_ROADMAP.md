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
| 1 | **Rol atama** (`start_game` içinde) | Oyunun her adımı role bağlı; bu olmadan hiçbir tur mantığı yazılamaz. |
| 2 | **Tur döngüsü — Cumhurbaşkanı/Başbakan seçimi + oylama** | Oyunun çekirdek etkileşimi. Rol ataması bittikten sonra ilk oynanabilir versiyon budur. |
| 3 | **Yasa kartı seçimi ve yürürlüğe girmesi** | Oylama olmadan anlamsız, oylamadan hemen sonra gelir. |
| 4 | **Kazanma koşulu kontrolü** (5 Demokrasi Reformu / 6 Sıkıyönetim / Kenan Evren öldürülür veya Cumhurbaşkanı olur) | Bu olmadan oyun asla "bitmiyor" — oynanabilirlik için zorunlu. |
| 5 | **Özel yetkiler** (sorgulama, ihraç, doğrudan başbakan seçimi, kaos modu) | Oyunun derinliği için önemli ama temel döngü çalışmadan anlamı yok — sona bırakılabilir. |
| 6 | **Frontend** (React — CORS ayarı zaten buna göre yapılmış) | Bugüne kadarki her şey API üzerinden test edilebilir (Postman/curl), ama gerçek kullanıcı testi için şart. |
| 7 | **Deploy** (`runtime.txt` mevcut — Heroku benzeri bir platforma hazırlanmış) | Gerçek kullanıcılarla test etmeden önce gerekli. |
| 8 | **Kalıcı veri saklama** (bellek yerine DB/Redis) | Tek sunucu, düşük kullanıcı sayısıyla MVP için ertelenebilir; çoklu kullanıcı / production için zorunlu hale gelir. |

## 4. Şimdi Ne Yapmalı (önerilen sıradaki adım)

**1 numaralı madde ile başla: Rol atama.** Küçük, izole, test edilmesi kolay bir parça — oyuncu sayısına göre kaç Darbeci/Demokrat olacağını `rules.json`'daki `player_count_based` mantığına göre hesaplayıp `start_game` içinde dağıtmak. Bunu istersen şimdi uygulamaya geçebiliriz.

## 5. Not Edilecek Riskler
- `CORS allow_origins=["*"]` — geliştirme için sorun değil, production'a çıkmadan önce daraltılmalı.
- Eski/terk edilmiş oyunlar için hiçbir temizleme mekanizması yok — bellek zamanla şişebilir.
