# Seksenler

'80'ler Türkiye temalı, Secret Hitler mekaniğinde sosyal blöf oyunu. 5-10 kişi; herkes kendi telefonundan oynar. Demokratlar 5 Demokrasi Reformu geçirmeye ya da Kenan Evren'i bulmaya çalışır; Darbeciler 6 Sıkıyönetim Kararı geçirmeye ya da Kenan Evren'i Başbakan seçtirmeye.

- **Backend:** FastAPI (`main.py`) — oda, roller, seçim/yasama turu, özel yetkiler, veto.
- **Frontend:** React + Vite (`frontend/`) — '80'ler gazete estetiği, telefon öncelikli.
- Ürün durumu ve backlog: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)

## Lokalde Çalıştırma

### Gereksinimler (bir kez kurulur)

| Araç | Sürüm | İndirme |
|---|---|---|
| Git | herhangi | https://git-scm.com/downloads |
| Python | 3.10+ | https://www.python.org/downloads/ (kurulumda "Add to PATH" işaretle) |
| Node.js | 18+ | https://nodejs.org (LTS) |

### Kurulum (bir kez)

```bash
git clone https://github.com/bsilan/seksenler-backend.git
cd seksenler-backend
git checkout claude/product-manager-guidance-4rx4xz

# Backend bağımlılıkları
pip install -r requirements.txt

# Frontend bağımlılıkları
cd frontend
npm install
cd ..
```

### Çalıştırma (her oyun gecesi)

İki ayrı terminal aç:

**Terminal 1 — backend:**
```bash
cd seksenler-backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — frontend:**
```bash
cd seksenler-backend/frontend
npm run dev -- --host
```

Terminal 2'de şöyle bir çıktı görürsün:

```
➜  Local:   http://localhost:5173/
➜  Network: http://192.168.1.34:5173/
```

### Oynama

- **Tek başına denemek için:** tarayıcıda `http://localhost:5173` adresini 5 ayrı sekmede aç, her sekmede farklı takma adla aynı odaya gir. (Rolleri tek ekranda göreceğin için gerçek oyun değil, deneme.)
- **Arkadaşlarla (asıl mod):** herkes bilgisayarınla **aynı Wi-Fi'a** bağlanır ve telefonundan Terminal 2'deki **Network** adresini açar (örnekteki `http://192.168.1.34:5173`). Biri "Oda Kur" der, oda kodunu söyler, kalanlar "Odaya Katıl" ile girer.

## Sık Karşılaşılan Sorunlar

- **Telefon bağlanamıyor:** Bilgisayarın güvenlik duvarı ilk çalıştırmada izin isteyebilir — "İzin ver" de (Windows'ta "Özel ağlar" kutusu işaretli olsun). Telefonun aynı Wi-Fi'da olduğundan emin ol.
- **"Port is already in use":** Eski bir sunucu hâlâ açık. O terminaldeki işlemi `Ctrl+C` ile durdur ya da bilgisayarı yeniden başlat.
- **Odalar kayboldu:** Oyunlar bellekte tutulur; backend'i (Terminal 1) kapatıp açarsan tüm odalar silinir. Oyun ortasında sunucuları kapatma.
- **`pip` / `npm` bulunamadı:** Python/Node kurulumundan sonra terminali kapatıp yeniden açman gerekir.

## İnternete Açma

Arkadaşların Wi-Fi şartı olmadan, her yerden linkle katılsın istiyorsan: frontend **Vercel**'e,
backend **Render**'a kurulur (ikisi de ücretsiz). Tıklama tıklama rehber: [`DEPLOY.md`](DEPLOY.md)

## Testler

Uçtan uca test scriptleri geliştirme oturumlarında `scratchpad` üzerinden koşuluyor; API'yi elle denemek istersen backend çalışırken `http://localhost:8000/docs` adresinde FastAPI'nin hazır arayüzü var.
