# DeskCamREC — Kurulum ve Kullanım

Sistem tepsisinde çalışan, şeffaf bir webcam kayıt uygulaması. Her şey
**tek bir dosyada** (`deskcamrec.py`) — ayrı bir ayar dosyası yoktur, ayarlar
program çalışırken tepsi menüsünden değiştirilir.

## 1) Kurulum

Python 3.9+ gereklidir. Başka hiçbir şey kurmanıza gerek yok — program
ilk çalıştırıldığında eksik olan şunları **kendisi** kurar:

- Python kütüphaneleri: `opencv-python-headless`, `pystray`, `pillow`, `numpy`, `mss`, `PyAudioWPatch`, `keyboard`
- `ffmpeg`: `imageio-ffmpeg` kütüphanesi üzerinden gelir (ayrı indirme/
  zip açma adımı yok, bu da kurulumu hem daha hızlı hem daha az hataya
  açık hale getirir)

Sadece **internet bağlantısı** gerekir (ilk çalıştırmada). Kurulum
başarısız olursa program size olası nedenleri (internet yok, güvenlik
duvarı/antivirüs engeli, yetki sorunu) ekranda gösterir; yetki sorunu
olursa otomatik olarak `--user` modunda tekrar dener.

**Not:** `ffdshow` gibi eski codec paketleri kullanılmaz/kurulmaz —
gereksizdir, çünkü kayıt OpenCV ile, sıkıştırma doğrudan ffmpeg ile
yapılır.

## 2) Çalıştırma

```
python deskcamrec.py
```

Program şifre sormadan açılır ve **otomatik olarak kayda başlar**.
Görev çubuğunun sağ altındaki gizli simgeler okunda bir daire simgesi
belirir:

- **Gri** = kayıt durdurulmuş
- **Kırmızı** = kayıt yapılıyor
- **Turuncu** = kamera açılamadı (hata)

## 3) Ayarlar penceresi (tek ekrandan tüm ayarlar)

Tepsi simgesine **sol tıklayınca** (veya sağ tık menüsünden
**"⚙ Ayarlar..."** seçince) tüm ayarları içeren küçük bir pencere
açılır:

- Kayıt Modu (Kamera / Ekran)
- Kayıt süresi (segment)
- Çözünürlük
- Kalite / dosya boyutu
- Ses (Mikrofon / Bilgisayar Sesi)
- Kayıt Klasörü (yazarak veya "Gözat..." ile seçin)
- **Kayıt Başlat / Kayıt Durdur klavye kısayolları** — burada istediğiniz
  kombinasyonu yazabilirsiniz (örn. `ctrl+shift+r`, `f9`). Geçersiz bir
  kısayol girilirse program sizi uyarır ve önceki kısayollara geri
  döner.

**Kaydet**'e bastığınızda tüm değişiklikler anında uygulanır (mevcut
segment düzgünce kapatılıp yeni ayarlarla kesintisiz devam edilir).

## 4) Tepsi menüsü (hızlı erişim)

Simgeye sağ tıklayınca, ayarlar penceresine ek olarak tek tek hızlı
değiştirebileceğiniz kısayol menüleri de vardır:

- **Kaydı Başlat / Kaydı Durdur**
- **Kayıtlar klasörünü aç** → o an seçili klasörü Dosya Gezgini'nde açar
- **Kayıt Klasörü: ...** → tıklayınca bir klasör seçme penceresi açılır;
  seçtiğiniz klasör **o andan itibaren** (bir sonraki segmentten
  başlayarak) kullanılır. Varsayılan: `C:\Temp`.
- **Kayıt Modu (Kamera / Ekran)** → Webcam yerine ekranınızı kaydetmek
  isterseniz "Ekran" seçin
- **Kayıt süresi (segment)** → 1 / 5 / 10 / 15 / 30 dakika arasından
  seçin. Varsayılan 5 dakika.
- **Çözünürlük** → Düşük (320x240), Orta (640x480), Yüksek (1280x720),
  **Maksimum (yerel çözünürlük)**. **Varsayılan: Maksimum.** Ekran
  kaydında metin/simgelerin okunabilir kalması için Maksimum önerilir
  — düşük çözünürlükler ekran içeriğini okunaksız hale getirir.
  Maksimum seçiliyken ekran modunda tam ekran çözünürlüğü, kamera
  modunda ise kameranın desteklediği en yüksek çözünürlük kullanılır
  (dosya boyutu da buna bağlı olarak artar).
- **Kalite / dosya boyutu** → Düşük boyut (CRF 30), Orta (CRF 23),
  **Yüksek kalite (CRF 18)**. **Varsayılan: Yüksek kalite.**
- **Ses** → Mikrofonu Ekle / Bilgisayar Sesini Ekle (ikisi birden de
  seçilebilir, bu durumda ikisi tek ses kanalında birleştirilir)
- **📖 Kullanım Kılavuzu** → son kullanıcı kılavuzunu programın
  kendi içinden, ayrı bir dosyaya gerek kalmadan açar (bkz. aşağısı)
- **Çıkış**

Program **varsayılan olarak en yüksek çözünürlük + en iyi kaliteyle**
açılır. Daha küçük dosya istiyorsanız Çözünürlük ve Kalite menülerinden
düşürebilirsiniz (aşağıya bakın).

Bu ayarların tümü **anında** uygulanır: değiştirdiğiniz an mevcut
segment düzgünce kapatılır ve yeni ayarlarla kesintisiz kayda devam
edilir — programı yeniden başlatmanıza gerek yoktur. (Not: ayar
değişikliğinde görüntü akışı kesintisizdir; ses kullanılıyorsa, ses
cihazının yeniden başlatılması nedeniyle segment geçişlerinde çok kısa
bir ses boşluğu olabilir.)

Küçük dosya istiyorsanız: **Düşük/Orta çözünürlük** + **Düşük boyut
kalitesi** + daha kısa segment süresi kombinasyonunu seçin.

### Klavye kısayolları

Program çalışırken **sistem genelinde** (hangi pencere odakta olursa
olsun) geçerli kısayollar:

- **Ctrl+R** → Kaydı başlat
- **Ctrl+T** → Kaydı durdur

**Dikkat:** Bunlar global (sistem geneli) kısayollardır — örneğin
Ctrl+R birçok tarayıcıda "sayfayı yenile" ile çakışır. Farklı bir
kombinasyon kullanmak isterseniz **Ayarlar penceresinden** (tepsi
simgesine tıklayın) "Kayıt Başlat/Durdur Kısayolu" alanlarını
değiştirip Kaydet'e basmanız yeterlidir — dosya düzenlemenize gerek
yoktur.

### Gerçek zamanlı kayıt

Video kareleri artık gerçek saate (wall clock) göre senkronize
yazılıyor: yakalama veya kodlama geçici olarak yavaşlasa bile (örn.
yüksek çözünürlüklü ekran kaydında işlemci yetişemediğinde), kayıt
videosu her zaman gerçek geçen süreyle birebir eşleşir — eskiden
görülen "videonun hızlandırılmış gibi oynaması" sorunu bu şekilde
giderildi. Çok yüksek çözünürlükte (örn. 4K ekran + Yüksek kalite)
yavaş bir bilgisayarda hâlâ CPU darboğazı yaşanabilir; bu durumda
görüntü akıcılığı (gerçek kare sayısı) düşebilir ama videonun SÜRESİ
her zaman doğru kalır. Akıcılığı artırmak isterseniz Çözünürlük veya
Kalite menüsünden bir adım aşağı inebilirsiniz.

### Ses hakkında notlar

Ses yakalama artık **PyAudioWPatch** kütüphanesi ile, Windows'un
WASAPI API'si üzerinden yapılıyor. Bu, eski "ffmpeg cihaz adı
eşleştirme" yöntemine göre çok daha güvenilirdir ve **"Stereo Mix"
gibi özel bir kayıt cihazını elle etkinleştirmenize gerek kalmaz**:

- **Mikrofon**: O an Windows'ta "varsayılan" olarak ayarlı mikrofon/
  giriş cihazı otomatik kullanılır (Windows Ses Ayarları'nda hangi
  mikrofon varsayılan olarak seçiliyse o).
- **Bilgisayar Sesi**: O an "varsayılan" olarak ayarlı çıkış (hoparlör/
  kulaklık) cihazının **loopback**'i (bilgisayardan çalınan her şeyin
  birebir kopyası) doğrudan yakalanır. Ayrıca bir sürücü/cihaz
  etkinleştirmeniz gerekmez.
- Her iki cihaz da **her segment başında yeniden sorgulanır**; yani
  kayıt sırasında kulaklığınızı takıp çıkarsanız veya varsayılan
  cihazı değiştirirseniz, bir sonraki segmentten itibaren güncel
  varsayılan cihaz kullanılır.
- Menüde "(cihaz bulunamadı)" görünüyorsa, bilgisayarınızda WASAPI
  destekli bir mikrofon/çıkış cihazı tespit edilememiş demektir (çok
  nadir bir durumdur); bu durumda Windows Ses Ayarları'ndan bir
  cihazın etkin ve varsayılan olarak ayarlı olduğunu kontrol edin.
- **Teknik not:** Ses açıkken, her segment video+ses olarak iki adımda
  oluşturulur (önce ayrı ayrı kaydedilir, segment biterken otomatik
  birleştirilir); bu nedenle ses açıkken dosyalar segment bitiminden
  birkaç saniye sonra tam olarak hazır hale gelir — bu normaldir.

## 5) Windows açılışında otomatik başlatma

1. `Win + R` → `shell:startup` yazıp Enter'a basın.
2. `deskcamrec.py` dosyasının bir kısayolunu bu klasöre kopyalayın.
3. Kısayolun özelliklerinde "Hedef" alanını şöyle ayarlayın (konsol
   penceresi açmadan çalışır):

   ```
   C:\Windows\System32\pythonw.exe "C:\tam\yol\deskcamrec.py"
   ```

Program açılır açılmaz otomatik kayda başlar; tepsi simgesi her zaman
görünür kalır, istediğiniz an durdurabilirsiniz.

## 6) Notlar

- `KAMERA_INDEX` ve `FPS` gibi çok nadir değişen ayarlar hâlâ
  `deskcamrec.py`'nin en üstündeki "SABİT AYARLAR" bölümünde elle
  düzenlenebilir. Kayıt klasörü, klavye kısayolları ve diğer tüm
  ayarlar artık **Ayarlar penceresinden** değiştirilir (bkz. yukarı),
  dosyayı düzenlemenize gerek yoktur.
- Diskte yer kalmazsa kayıt duracaktır; eski kayıtları periyodik
  olarak temizlemeniz önerilir.
- Bu araç yalnızca kendi cihazınızda, kendi bilginiz dahilinde
  kullanım için tasarlanmıştır.

### Derlenmiş .exe boyutu neden daha küçük, gerçekçi beklenti nedir?

Boyutu küçültmek için üç önlem birlikte uygulanır:

1. **`ffmpeg` programının kendisi (~70-80 MB) exe'nin içine hiç
   gömülmez.** `ffmpeg`, yalnızca **ilk gerçek kayıt denemenizde**,
   kütüphanenin resmi kaynağından (GitHub Releases, HTTPS üzerinden)
   otomatik indirilip bilgisayarınıza bir kez kaydedilir. Sonraki her
   çalıştırmada zaten diskte olduğu için tekrar inmez. Bu indirme
   sırasında (ve internet yoksa) tepsi simgesi turuncu olur; bağlantı
   geldiğinde kayıt kendiliğinden başlar.
2. **`cv2` için GUI/Qt içermeyen `opencv-python-headless` kullanılır**
   (bu program zaten cv2'nin hiçbir pencere/GUI özelliğini kullanmıyor).
3. **`cv2`'nin Windows paketinde lisans nedeniyle AYRI bir dosya olarak
   gelen `opencv_videoio_ffmpeg*.dll` eklentisi (~25-30 MB) ve
   kullanılmayan `msmf`/`gstreamer` eklentileri `hooks/hook-cv2.py`
   ile dışarıda tutulur.** Bu program video DOSYASI okuma/yazma için
   cv2'yi hiç kullanmaz (sadece canlı kamera görüntüsü için
   `CAP_DSHOW`), bu yüzden güvenli bir çıkarmadır.

**Gerçekçi beklenti:** Bu önlemlerle birlikte exe, `ffmpeg` gömülü
haline göre belirgin şekilde küçülür, ama sıfıra inmez — Python
çalışma zamanı, `tkinter` (ayarlar/kılavuz pencereleri için) ve
`numpy`/`opencv` çekirdek kütüphaneleri hâlâ gereklidir ve bunlar
tek başlarına onlarca MB'dir. Daha fazla küçültmek isterseniz:
[UPX](https://github.com/upx/upx/releases) indirip `upx.exe`'yi
PATH'inize eklerseniz, `derle.bat` çalıştırdığınızda PyInstaller
bunu otomatik fark edip exe'yi ek olarak sıkıştırır (bu adım
isteğe bağlıdır, `derle.bat` bunu sizin onayınız olmadan indirmez).
