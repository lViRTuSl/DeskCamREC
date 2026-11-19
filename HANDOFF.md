# DeskCamREC — Devam Kılavuzu (başka bir yapay zeka asistanı için)

Bu belge, bu projeye bir sonraki oturumda/başka bir asistanla kaldığı
yerden devam edebilmek için yazılmıştır. Kod kendi içinde zaten
yoğun Türkçe yorumlarla açıklanmıştır (her fonksiyonun üstünde "neden
böyle yapıldığı" anlatılır); bu belge onun ÜZERİNE, genel resmi ve
tasarım kararlarının GEREKÇELERİNİ özetler.

## 1) Proje nedir, kim için

**DeskCamREC**: Windows için, sistem tepsisinde (system tray) çalışan,
**kişisel/tek kullanıcı** kamera veya ekran kaydı programı. Tek dosyalık
Python betiği (`deskcamrec.py`), PyInstaller ile tek dosyalık `.exe`
olarak derlenir.

Sahibi: Erdem Demirtas (erdemdemirtas@gmail.com), GitHub: `lViRTuSl`.
Depo: **https://github.com/lViRTuSl/DeskCamREC** (public, `main` dalı).

### Kullanıcının kesin tercihleri (ÖNEMLİ — sapılmamalı)
- Türkçe konuşulur, kısa/öz yanıt verilir (kullanıcı "kullanım limiti"
  nedeniyle az adımla ilerlenmesini istiyor).
- Kod/dosya değişikliklerinde sadece DEĞİŞEN kısım verilir, kullanıcı
  tüm dosyayı istemediği sürece dosyanın tamamı tekrar yapıştırılmaz.
- Onaysız, "önlem olarak" kafaya göre değişiklik yapılmaz — özellikle
  kullanıcının başka projelerinde (Home Assistant/inverter vb.).
  Bu projede ise kullanıcı **"tam yetki"** vermiş ve **her değişikliğin
  onay beklemeden otomatik commit+push edilmesini** istemiştir (bkz.
  depodaki `CLAUDE.md`).
- Gereksiz araç çağrısı yapılmaz (aynı dosya tekrar okunmaz, toplu
  yüklenir).

## 2) Programın TEMEL tasarım ilkesi: Şeffaflık

Kullanıcı açıkça **gizli/stalkerware tarzı bir araç İSTEMEMİŞTİR**.
Bu yüzden program kasıtlı olarak:
- Her zaman görünür bir tepsi simgesi gösterir.
- Kayıt klasörü açıkça belirtilir (gizli bir yere yazılmaz).
- Kayıt her an tek tıkla veya klavye kısayoluyla durdurulabilir.
- Windows Service olarak KAYDEDİLMEZ (bu özellik kullanıcı tarafından
  istenmiş ama Session 0 izolasyonu/azalan görünürlük gerekçesiyle
  reddedilmiştir — bunun yerine şeffaf bir Başlangıç klasörü kısayolu
  önerilmiştir).

Bu ilke yeni özellik eklenirken de korunmalıdır.

## 3) Mimari ve "neden böyle" kararları

### 3.1 Tek dosya, ayrı ayar dosyası yok
Tüm ayarlar `deskcamrec.py` içinde sabitler + çalışma zamanı state
olarak tutulur. Kalıcı bir config dosyası YOKTUR (kasıtlı — basitlik).
Program her açıldığında varsayılanlarla başlar, kullanıcı o oturumda
Ayarlar penceresinden değiştirir.

### 3.2 Ayarlar penceresi NEDEN ayrı bir alt süreçte açılıyor
`pystray`'in arka plan thread'inden açılan bir Tkinter penceresi,
Windows'ta klavye/fare odağını ALAMIYORDU (SetForegroundWindow,
AttachThreadInput gibi tüm "zorlama" hileleri denendi, hiçbiri güvenilir
çalışmadı — kullanıcı bunu defalarca "tıklamaya tepki vermiyor" diye
bildirdi). **Kesin çözüm**: pencere, aynı exe/script'in KENDİSİNİ
`--ayarlar-penceresi <giris.json> <cikis.json>` bayrağıyla AYRI bir
process olarak yeniden başlatmasıyla açılır. Yeni bir process'in kendi
ilk penceresi olduğu için Windows normal odak hakkı verir — sorun kökten
çözüldü. Aynı desen kullanım kılavuzu penceresi için de kullanılıyor
(`--kilavuz` bayrağı). **Bu deseni bozmayın** — basit bir Toplevel'e
geri dönmek odak sorununu geri getirir.

### 3.3 Gerçek zamanlı kayıt (frame pacing)
Eskiden sabit `time.sleep(1/FPS)` kullanılıyordu; yüksek çözünürlükte
yakalama/kodlama FPS'den yavaş kaldığında video 1.5x-2x hızlı
oynuyordu (kullanıcı bunu özellikle şikayet etti). Çözüm:
`kayit_dongusu()` içinde HER döngüde "gerçek geçen süreye göre şu ana
kadar kaç kare yazılmış OLMALIYDI" hesaplanır, eksikse aynı kare
tekrar yazılarak (frame duplication) fark kapatılır. Böylece video
SÜRESİ her zaman gerçek geçen süreyle birebir eşleşir.

### 3.4 Ses: PyAudioWPatch (WASAPI), ffmpeg dshow DEĞİL
Eski yaklaşım ffmpeg'in dshow cihaz adı eşleştirmesiyle mikrofon/
"Stereo Mix" arıyordu — güvenilmezdi ("Stereo Mix" çoğu PC'de kapalı).
Şimdiki yaklaşım: `pyaudiowpatch` ile Windows WASAPI'nin o anki
VARSAYILAN giriş cihazını ve varsayılan çıkış cihazının LOOPBACK'ini
doğrudan alır — isim eşleştirme YOK, ekstra cihaz etkinleştirme YOK.
Her segment başında yeniden sorgulanır (kullanıcı kulaklık takıp
çıkarsa bile güncel cihaz kullanılır).

### 3.5 Video + ses nasıl birleştiriliyor
Her segment için: video HAM kareler halinde bir ffmpeg process'ine
stdin üzerinden akıtılır (`-f rawvideo -pix_fmt bgr24`); ses (varsa)
PyAudioWPatch ile AYRI thread'lerde ayrı WAV dosyalarına yazılır.
Segment kapanırken (`_segmenti_kapat_arka_planda`) video+ses(ler)
İKİNCİ bir ffmpeg çağrısıyla (gerekirse `amix` ile karıştırılarak) tek
mp4'te birleştirilir, geçici dosyalar silinir. Kamera/ekran kaynağı
segmentler arasında KAPANMAZ (sürekli açık kalır) — sadece ffmpeg
process'i değişir, böylece segmentler arası kare kaybı/kesinti olmaz.

### 3.6 Exe boyutu küçültme (en son yapılan iş, DİKKATLİ olun)
Kullanıcı derlenmiş exe'nin çok büyük olmasından defalarca şikayet
etti. Alınan önlemler (hepsi `derle.bat` + `hooks/hook-cv2.py` içinde):
1. `cv2` için GUI'siz `opencv-python-headless` kullanılıyor (program
   zaten cv2'nin hiçbir GUI özelliğini kullanmıyor, sadece
   `cv2.VideoCapture(..., cv2.CAP_DSHOW)` ile canlı kamera yakalama).
2. `ffmpeg`'in kendisi (~70-80 MB) exe'ye GÖMÜLMÜYOR. `ffmpeg_yolunu_getir()`
   fonksiyonu: önce PATH'te ffmpeg var mı bakar, yoksa `imageio_ffmpeg`
   kütüphanesi üzerinden resmi kaynaktan (GitHub Releases, HTTPS)
   **sadece ilk gerçek kayıt denemesinde** indirir ve önbelleğe alır
   (program AÇILIŞINDA değil — açılış asla bloklanmaz/çökmez). Ağ
   hatası `kayit_dongusu()` içinde genel `Exception` olarak yakalanıp
   5 sn sonra otomatik tekrar denenir, simge turuncu olur.
3. `hooks/hook-cv2.py`: cv2'nin Windows paketinde LİSANS nedeniyle
   AYRI bir dosya olarak gelen `opencv_videoio_ffmpeg*.dll` eklentisi
   (~25-30 MB, biz hiç kullanmıyoruz çünkü video dosyası okuma/yazma
   yapmıyoruz) ve msmf/gstreamer eklentileri derlemeden çıkarılıyor.

   **ÖNEMLİ UYARI — burada bir kez hata yapıldı ve düzeltildi:** İlk
   hook denemesi sadece `collect_dynamic_libs("cv2")` kullanmıştı; bu,
   cv2'nin kendi yükleyicisinin DİNAMİK olarak (normal import DEĞİL,
   dosya yolundan) okuduğu `config.py`/`config-3.py` dosyalarını
   `datas` listesinden düşürüyordu ve program **"OpenCV loader: missing
   configuration file"** hatasıyla hiç açılmıyordu. Düzeltme:
   `collect_all("cv2")` kullanmak (bu, `--collect-all cv2` ile AYNI,
   kanıtlanmış doğru yöntem — datas/hiddenimports eksiksiz gelir),
   sadece elde edilen `binaries` listesinden istenmeyen DLL'ler süzülür.
   **Eğer cv2 ile ilgili yeni bir "açılmıyor" hatası gelirse, önce bu
   hook'tan şüphelenin.**

   Son durum: Kullanıcı derlemeyi bu düzeltmeden SONRA henüz test edip
   geri bildirim vermedi (bu konuşma burada kesildi). **Bir sonraki
   oturumda ilk soru şu olmalı: "exe artık sorunsuz açılıyor mu, yeni
   boyutu ne oldu?"**

   Gerçekçi beklenti (kullanıcıya zaten söylendi): Python çalışma
   zamanı + `tkinter` (ayarlar/kılavuz pencereleri için) + `numpy`/
   `opencv` çekirdeği hâlâ onlarca MB'dir, sıfıra inmez. Daha fazla
   küçültme istenirse: (a) UPX (kullanıcı onayı olmadan OTOMATİK
   indirilmez, sadece PATH'te varsa PyInstaller otomatik kullanır),
   (b) daha agresif ama RİSKLİ bir adım: kamera yakalamayı cv2'den
   tamamen çıkarıp ffmpeg'in kendi dshow girişine bağlamak (bu,
   cv2'yi TAMAMEN kaldırır ama kamera cihaz seçimini isim-eşleştirmeye
   döndürür — kullanıcıya bu seçenek sunulmuş, henüz onay verilmedi).

### 3.7 Kullanım kılavuzu programın İÇİNDE
Ayrı bir `KULLANIM_KILAVUZU.md`/PDF artık YOK (kullanıcı özellikle
kaldırılmasını istedi). Kılavuz metni `deskcamrec.py` içinde
`KILAVUZ_METNI` sabitinde tutulur, tepsi menüsündeki
**"📖 Kullanım Kılavuzu"** öğesiyle (yine ayrı bir alt süreçte, bkz.
3.2) salt okunur bir pencerede gösterilir. **Programda kullanıcıya
görünür bir davranış değiştiğinde bu metni de güncelleyin** — tek
doğru kaynak budur, ayrı dosya yazmayın.

## 4) Dosya yapısı

| Dosya | Ne işe yarar |
|---|---|
| `deskcamrec.py` | Tüm program (tek dosya) |
| `derle.bat` | Windows'ta PyInstaller ile tek dosyalık `.exe` üretir |
| `hooks/hook-cv2.py` | Özel PyInstaller hook'u (bkz. 3.6) |
| `README.md` | Kısa tanıtım + hızlı başlangıç |
| `OKUBENI.md` | Kurulum, ayarlar, teknik detaylar (uzun) |
| `CLAUDE.md` | Bu depodaki çalışma kuralı: her değişiklik otomatik push edilir |
| `LICENSE` | MIT |
| `.gitignore` | `build/`, `dist/`, `*.spec`, `__pycache__/` vb. |

## 5) Derleme (Windows'ta)

```
derle.bat
```
Gerekli pip paketlerini kurar, `python -c "import ..."` ile önce
gerçekten çalıştıklarını doğrular, sonra PyInstaller ile derler.
Çıktı: `dist\DeskCamREC.exe`.

## 6) Bilinen sınırlamalar / açık uçlar
- İlk gerçek kayıt denemesinde internet gerekir (ffmpeg indirmek için,
  bkz. 3.6 madde 2) — sonrasında tamamen offline çalışır.
- Kamera her zaman `KAMERA_INDEX = 0` (tek kameralı kullanıcı için
  yeterli; birden fazla kamera varsa dosyanın başındaki sabitten elle
  değiştirilir — ayarlar penceresinde YOK).
- Tek ekran desteklenir (`mss.monitors[1]`); çoklu ekran seçimi yok.
- Son exe derlemesi kullanıcı tarafından henüz doğrulanmadı (bkz. 3.6).

## 7) Git/GitHub durumu
- Repo: `https://github.com/lViRTuSl/DeskCamREC`, dal: `main`.
- Bu depo, eski `lViRTuSl/Kamera_Ekran_Kayit` deposunun yeniden
  adlandırılmış/taşınmış hâlidir (eski depo kullanıcı tarafından
  silindi). Eski depoda daha fazla commit geçmişi vardı; bu depo
  temiz tek commit ile başlatıldı, kod içeriği güncel ve eksiksizdir.
- **Kural (CLAUDE.md'den):** Bu depoda yapılan HER değişiklik, onay
  beklemeden commit edilip `git push` ile yayınlanır. Anlamlı Türkçe
  commit mesajı yazılır.
