# DeskCamREC

Windows için, sistem tepsisinde çalışan; kamera veya ekran görüntüsünü
(isteğe bağlı olarak mikrofon ve/veya bilgisayar sesiyle birlikte)
MP4 olarak kaydeden, şeffaf (gizli olmayan) kişisel kayıt aracı.

Her an görünür bir tepsi simgesi vardır, kayıtlar açıkça belirtilen bir
klasöre yazılır (varsayılan `C:\Temp`) ve kayıt tek tıkla veya klavye
kısayoluyla (varsayılan `Ctrl+R` / `Ctrl+T`) istenildiği an durdurulabilir.

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `deskcamrec.py` | Ana program (tek dosya) |
| `derle.bat` | Windows'ta tek dosyalık `.exe` üretmek için derleme betiği (PyInstaller) |
| `OKUBENI.md` | Kurulum, ayarlar ve teknik detaylar |

## Hızlı başlangıç

```
python deskcamrec.py
```

Gerekli kütüphaneler (opencv-python-headless, pystray, pillow, numpy, mss,
PyAudioWPatch, keyboard, imageio-ffmpeg) ilk çalıştırmada otomatik kurulur.
Tek dosyalık `.exe` üretmek için `derle.bat` dosyasını çalıştırın.

**Kullanım kılavuzu artık programın içinde:** tepsi simgesine sağ
tıklayıp **"📖 Kullanım Kılavuzu"**'nu seçin — ayrı bir dosyaya gerek
yoktur, kılavuz program güncellendikçe kendisiyle birlikte güncel kalır.
Detaylı kurulum/teknik bilgi için **OKUBENI.md**'ye bakın.

## Not

Bu araç yalnızca kendi cihazınızda, kendi bilginiz dahilinde kullanım
için tasarlanmıştır: tepsi simgesi her zaman görünür, kayıt klasörü
gizli değildir ve kayıt her an durdurulabilir.
