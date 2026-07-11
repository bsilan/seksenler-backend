# Seksenler'i İnternete Açma (Vercel + Render)

Bu rehberle oyun herkese açık bir link alır: arkadaşların **aynı Wi-Fi'da olmadan**, her yerden telefonuyla katılabilir. Kod yazmak gerekmez; her şey tarayıcıdan tıklamayla yapılır ve iki servis de ücretsiz katmanda çalışır.

## Mimari (neden iki servis?)

| Parça | Nereye | Neden |
|---|---|---|
| Frontend (React) | **Vercel** | Statik dosyalar; Vercel bu iş için ideal ve çok hızlı. |
| Backend (FastAPI) | **Render** | Oyun odaları bellekte tutuluyor; sürekli açık kalan bir sunucu süreci gerekiyor. Vercel sunucusuz çalıştığı için (her istek ayrı, kısa ömürlü) odaları hatırlayamaz — Render ise klasik "hep açık" sunucu verir. |

## Adım 0 — Branch

Render ve Vercel, GitHub'daki bir branch'i izler. Aşağıdaki adımlarda branch olarak
`claude/product-manager-guidance-4rx4xz` seç (kodun güncel hali burada). İleride bu branch `main`'e
merge edilirse iki serviste de branch'i `main` yapman yeterli.

## Adım 1 — Backend'i Render'a kur (~5 dk)

1. https://render.com → **Sign in with GitHub** ile gir (yeni hesap gerekiyorsa GitHub'la aç).
2. Sağ üstten **New +** → **Web Service**.
3. GitHub reponu bağla: `bsilan/seksenler-backend` → **Connect**.
4. **Branch** alanında `claude/product-manager-guidance-4rx4xz` seç. Repo kökündeki `render.yaml`
   sayesinde build/start komutları otomatik dolar; ellemen gerekmez. Instance Type: **Free**.
5. **Create Web Service** → ilk deploy 2-3 dk sürer, loglar ekranda akar.
6. Bittiğinde sayfanın üstünde adresin yazar: `https://seksenler-backend-XXXX.onrender.com`
   Bu adresi tarayıcıda aç — `{"message":"Seksenler oyun API'si çalışıyor!"}` görmelisin.
7. **Bu adresi kopyala** — Adım 2'de lazım.

## Adım 2 — Frontend'i Vercel'e kur (~5 dk)

1. https://vercel.com → **Continue with GitHub** ile gir.
2. **Add New…** → **Project** → `bsilan/seksenler-backend` reposunda **Import**.
3. Ayarlar ekranında:
   - **Root Directory**: `Edit` deyip `frontend` seç. ⚠️ En kritik adım — unutulursa build patlar.
   - **Framework Preset**: otomatik "Vite" görünmeli.
   - **Environment Variables**: `VITE_API_URL` adında değişken ekle, değeri Adım 1'de kopyaladığın
     Render adresi (örn. `https://seksenler-backend-XXXX.onrender.com` — sonuna `/` koyma).
   - Branch (Production Branch ayarı proje oluşturduktan sonra Settings → Git'te):
     `claude/product-manager-guidance-4rx4xz`.
4. **Deploy** → 1-2 dk sonra `https://seksenler-XXXX.vercel.app` gibi bir link verir.

## Adım 3 — Test

1. Vercel linkini telefonundan aç → "Oda Kur".
2. Başka bir cihazdan (mobil veri de olur) aynı linki aç → oda koduyla katıl.
3. Çalışıyorsa link paylaşıma hazır. 🗞️

## Bilmen Gerekenler

- **Render free uykuya dalar:** ~15 dk istek gelmezse servis uyur; ilk giren ~1 dk bekler.
  Oyun gecesinden önce linki bir kez açıp uyandırmak yeterli. Oyun sırasında sorun olmaz
  (2 saniyede bir istek gittiği için uyumaz).
- **Sunucu yeniden başlarsa odalar silinir:** Odalar bellekte; Render bakım için süreci yeniden
  başlatabilir. Oyun ortasında olursa yeni oda kurmak gerekir. (Kalıcı saklama backlog'da — madde 8.)
- **Her `git push` otomatik deploy tetikler:** Branch'e push edilen her değişiklik Render'da ve
  Vercel'de kendiliğinden yayına çıkar.

## Sorun Giderme

- **Vercel build hatası** → Root Directory'nin `frontend` olduğundan emin ol.
- **Site açılıyor ama "Bağlanılıyor…"da kalıyor / oda kurulamıyor** → Vercel'de `VITE_API_URL`
  değerini kontrol et (Render adresi, başında `https://`, sonunda `/` yok). Değiştirdiysen
  Deployments → ⋯ → Redeploy gerekir (ortam değişkenleri build'e gömülür).
- **İlk istek çok yavaş** → Render uykudan uyanıyordur; 1 dk bekleyip yenile.
