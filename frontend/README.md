# COREX Konteyner Takip — Frontend

COREX'in çoklu liman konteyner takip sisteminin arayüzü. Vue 3 + Vite ile
yazıldı; harita (Leaflet), yapay zeka destekli chatbot (backend üzerinden
Groq/Cerebras LLM) ve kontrol paneli (grafikler) olmak üzere üç ana sekmeden
oluşuyor.

Bu klasör sadece frontend'i içerir — çalışması için `backend/` klasöründeki
FastAPI sunucusunun da ayrıca çalışıyor olması gerekir (bkz. proje kök
dizinindeki `baslat.bat` / `kapat.bat`, ikisini birlikte başlatıp durdurur).

## Özellikler

- **Kontrol Paneli**: seçili limana göre saatlik/haftalık/aylık yoğunluk,
  kalış süresi istatistikleri ve son işlemler.
- **Harita**: Corex'in limanı olan ülkelerin interaktif dünya haritası,
  ülke bazlı hava durumu, liman seçimi.
- **Sohbet**: konteyner/liman verisi hakkında doğal dilde soru sorabildiğin
  yapay zeka asistanı, geçmiş sohbetler, adminler için veri ekleme/yönetme
  paneli.

## Proje Kurulumu

```sh
npm install
```

Sadece bir kere, ilk kurulumda gerekli.

## Geliştirme Sunucusu (Hot-Reload)

```sh
npm run dev
```

`http://localhost:5173` adresinde açılır. Backend'in de `http://127.0.0.1:8001`
üzerinde ayrıca çalışıyor olması gerekir (kök dizindeki `baslat.bat` her
ikisini de başlatır).

## Production Derlemesi

```sh
npm run build
```

Statik dosyaları `dist/` klasörüne üretir (bu klasör Git'e dahil değildir,
her derlemede yeniden oluşturulur).

```sh
npm run preview
```

`dist/` içindeki derlenmiş halini yerelde test etmek için.

## Lint / Format

```sh
npm run lint    # ESLint + oxlint ile otomatik düzeltme
npm run format  # Prettier ile src/ klasörünü biçimlendirir
```

## Klasör Yapısı (özet)

```
src/
  components/     # TopNav, LoginView, DashboardPanel, OceanMap, ChatWidget, AdminPanel, BarChart
  i18n.js         # TR/EN çeviri sözlüğü
  facility.js     # seçili liman state'i (sekmeler arası paylaşılır)
  activity.js     # "son işlemler" kaydı (girişli: backend, misafir: sessionStorage)
  main.js         # uygulamanın giriş noktası
public/
  favicon.ico, logo-icon.png   # statik varlıklar, build'e olduğu gibi kopyalanır
```

## Önerilen IDE Kurulumu

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)
eklentisi (Vetur kuruluysa kapatılmalı, ikisi çakışıyor).
