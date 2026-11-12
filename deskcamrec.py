r"""
DeskCamREC
----------------------
Sistem tepsisinde (system tray) çalışan, şeffaf bir webcam kayıt aracı.

ÖNEMLİ - ŞEFFAFLIK ÖZELLİKLERİ:
- Her zaman görev çubuğunda bir simge gösterir; simgeye tıklayarak
  kaydı durdurabilir, başlatabilir veya programdan çıkabilirsiniz.
- Program açıldığında şifre sormadan otomatik olarak kayda başlar.
  Tepsi ikonu her zaman görünür kalır (kırmızı = kayıt yapılıyor,
  gri = durdurulmuş) ve menüden istediğiniz an durdurabilirsiniz.
- Kamera her kullanıldığında bilgisayarınızın donanım kamera LED'i
  (varsa) yanar; bu Windows tarafından kontrol edilir, program
  bunu gizleyemez.
- Kayıtlar açıkça belirlenmiş bir klasöre kaydedilir (varsayılan
  C:\Temp), gizli bir konuma değil. Bu klasör tepsi menüsünden
  değiştirilebilir.
- Kayıt/durdurma için sistem genelinde klavye kısayolları vardır
  (varsayılan: Ctrl+R başlat, Ctrl+T durdur).
- Video karelerinin yazılması gerçek saat (wall clock) zamanına göre
  senkronize edilir; yakalama/kodlama geçici olarak yavaşlasa bile
  (örn. yüksek çözünürlüklü ekran kaydında) kayıt videosu her zaman
  gerçek geçen süreyle eşleşir, hızlandırılmış görünmez.
- Program ilk açıldığında eksik Python kütüphanelerini ve ffmpeg'i
  otomatik kontrol eder; eksikse kurar (internet gerekir). ffmpeg,
  manuel indirme/zip açma gerektirmeyen imageio-ffmpeg kütüphanesi
  üzerinden gelir; bu kurulumu basitleştirir ve daha güvenilir yapar.
  Not: ffdshow gibi eski/terk edilmiş codec paketleri bu program
  tarafından KULLANILMAZ ve kurulmaz — gereksizdir, çünkü kayıt ve
  sıkıştırma doğrudan OpenCV + ffmpeg ile yapılır.
- Kayıt süresi (segment uzunluğu), çözünürlük ve kalite/dosya boyutu
  AYRI BİR AYAR DOSYASI OLMADAN, doğrudan tepsi menüsünden
  değiştirilebilir. Değişiklik yapıldığında mevcut segment düzgünce
  kapatılır ve yeni ayarlarla kesintisiz devam edilir.

Gereksinimler:
    Program ilk açıldığında eksik Python kütüphanelerini (opencv-python-headless,
    pystray, pillow, imageio-ffmpeg) otomatik olarak kontrol eder,
    eksikse kendisi kurar. Manuel kurulum gerekmez, ama internet
    bağlantısı gerekir (ilk çalıştırmada).

Kullanım:
    python deskcamrec.py
"""

import importlib
import subprocess
import sys
import os
import json
import tempfile

# ============================================================
# OTOMATİK KÜTÜPHANE KONTROLÜ VE KURULUMU
# (diğer her şeyden önce çalışır, çünkü cv2/pystray/PIL henüz
# sistemde olmayabilir)
# ============================================================

GEREKLI_PAKETLER = {
    "cv2": "opencv-python-headless",
    "pystray": "pystray",
    "PIL": "pillow",
    "numpy": "numpy",
    # ffmpeg'i elle indirip kurmak yerine, ffmpeg'in kendisini paketin
    # içinde hazır getiren bu kütüphaneyi kullanıyoruz. Bu, manuel
    # zip indirme/açma adımlarını (ve bunların bazı sistemlerde
    # kırılgan olmasını) tamamen ortadan kaldırır.
    "imageio_ffmpeg": "imageio-ffmpeg",
    # Ekran kaydı için hızlı ekran görüntüsü yakalama kütüphanesi
    "mss": "mss",
    # Mikrofon VE bilgisayarın çıkış sesini (hoparlör/loopback) doğrudan
    # Windows'un WASAPI API'si üzerinden, "Stereo Mix" gibi özel bir
    # kayıt cihazı etkinleştirmeye gerek kalmadan yakalar. ffmpeg'in
    # DirectShow cihaz listesine isim eşleştirerek ses cihazı bulmaya
    # çalışmaktan çok daha güvenilirdir.
    "pyaudiowpatch": "PyAudioWPatch",
    # Klavye kısayolları (Ctrl+R / Ctrl+T) için
    "keyboard": "keyboard",
}


def _calisiyor_mu_derlenmis_exe():
    """PyInstaller ile derlenmiş bir .exe olarak mı çalışıyoruz, yoksa
    düz bir .py betiği olarak mı? (PyInstaller sys.frozen'ı True yapar.)"""
    return getattr(sys, "frozen", False)


def _hata_penceresi_goster(baslik, mesaj):
    """input()/console'a bağımlı olmadan, pencereli (konsolsuz) exe'de
    bile çalışan basit bir hata penceresi gösterir."""
    try:
        import tkinter as _tk
        from tkinter import messagebox as _messagebox
        _kok = _tk.Tk()
        _kok.withdraw()
        _kok.attributes("-topmost", True)
        _messagebox.showerror(baslik, mesaj, parent=_kok)
        _kok.destroy()
    except Exception:
        # tkinter de çalışmazsa (çok nadir), son çare olarak konsola yaz.
        # input() KULLANILMAZ: konsolsuz (pencereli) exe'de stdin yoktur
        # ve input() orada anında "EOFError" ile çöker.
        print(f"{baslik}\n{mesaj}")


def _pip_ile_kur(paketler, ekstra_bayrak=None):
    komut = [sys.executable, "-m", "pip", "install"]
    if ekstra_bayrak:
        komut.append(ekstra_bayrak)
    komut.extend(paketler)
    # stdin=DEVNULL: pip'in (veya altındaki bir aracın) stdin okumaya
    # çalışması durumunda konsolsuz ortamda kilitlenmesini/çökmesini
    # önler.
    subprocess.check_call(
        komut,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def eksik_python_kutuphanelerini_kur():
    # Derlenmiş bir .exe içindeyken kendi .exe dosyamızı "python -m pip"
    # gibi çalıştırmaya çalışmak hem anlamsızdır (exe bir Python
    # yorumlayıcısı değildir) hem de hataya yol açar. Derlenmiş exe'de
    # TÜM kütüphaneler derleme sırasında (--collect-all ile) zaten
    # pakete gömülmüş olmalıdır; burada sadece gerçekten eksik bir şey
    # varsa kullanıcıyı bilgilendirip çıkıyoruz — pip ile kurmayı HİÇ
    # denemiyoruz.
    if _calisiyor_mu_derlenmis_exe():
        eksikler = []
        for modul_adi in GEREKLI_PAKETLER:
            try:
                importlib.import_module(modul_adi)
            except Exception as e:
                # Sadece modül adını değil, GERÇEK hata nedenini de
                # gösteriyoruz; bu, sorunun "paketleme sırasında hiç
                # dahil edilmemiş" mi yoksa "dahil edildi ama içe
                # aktarırken başka bir hata oluştu" mu olduğunu
                # ayırt etmeyi kolaylaştırır.
                eksikler.append(f"{modul_adi}  →  {type(e).__name__}: {e}")
        if eksikler:
            _hata_penceresi_goster(
                "DeskCamREC - Eksik Bileşen",
                "Program içinde olması gereken bazı bileşenler yüklenemedi:\n\n"
                + "\n".join(eksikler)
                + "\n\n"
                "Bu, programın derlenmesi (derle.bat) sırasında bir şeyin "
                "eksik/hatalı kalmış olabileceği anlamına gelir. Lütfen "
                "güncel derle.bat dosyasını kullanıp 'dist' ve 'build' "
                "klasörlerini silerek programı SIFIRDAN yeniden derleyin.",
            )
            sys.exit(1)
        return

    eksik_paketler = []
    for modul_adi, pip_adi in GEREKLI_PAKETLER.items():
        try:
            importlib.import_module(modul_adi)
        except ImportError:
            eksik_paketler.append(pip_adi)

    if not eksik_paketler:
        return

    print(f"Eksik kütüphaneler tespit edildi: {', '.join(eksik_paketler)}")
    print("Kuruluyor, lütfen bekleyin...")

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # pip'in kendisini güncelleyememek kritik değil, devam edilir

    # 1) Normal kurulum dene
    try:
        _pip_ile_kur(eksik_paketler)
        print("Kütüphaneler başarıyla kuruldu.")
        return
    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        print(f"Beklenmeyen hata: {e}")

    # 2) Yetki sorunu olabilir (örn. yönetici izni olmayan hesap) -> --user dene
    print("Normal kurulum başarısız oldu, kullanıcı moduyla tekrar deneniyor...")
    try:
        _pip_ile_kur(eksik_paketler, ekstra_bayrak="--user")
        print("Kütüphaneler --user modunda başarıyla kuruldu.")
        return
    except Exception as e:
        hata_mesaji = (
            f"Kütüphaneler kurulamadı: {e}\n\n"
            "Olası nedenler:\n"
            "  - İnternet bağlantınız yok veya güvenlik duvarı/proxy engelliyor\n"
            "  - Antivirüs yazılımı pip'i engelliyor\n"
            "  - Python kurulumunuz bozuk olabilir\n\n"
            "Lütfen internet bağlantınızı kontrol edip programı tekrar çalıştırın."
        )
        print(hata_mesaji)
        _hata_penceresi_goster("DeskCamREC - Kurulum Hatası", hata_mesaji)
        sys.exit(1)


eksik_python_kutuphanelerini_kur()

# ============================================================
# ŞİMDİ GÜVENLE İÇE AKTARILABİLİR
# ============================================================

import cv2
import numpy as np
import mss
import pyaudiowpatch as pyaudio
import wave
import keyboard
import threading
import time
import shutil
import imageio_ffmpeg
import tkinter as tk
from tkinter import filedialog, ttk
from datetime import datetime
from pathlib import Path

import pystray
from pystray import MenuItem as Item
from PIL import Image, ImageDraw

# ------------------ SABİT AYARLAR ------------------
KAMERA_INDEX = 0                  # Birden fazla kamera varsa değiştirin (0, 1, 2...)
FPS = 20.0
VARSAYILAN_CIKTI_KLASORU = Path("C:/Temp")  # program çalışırken menüden değiştirilebilir
FFMPEG_PRESET = "veryfast"        # ultrafast..veryslow (yavaş=daha iyi sıkıştırma, daha çok CPU)

# Klavye kısayolları (program çalışırken sistem genelinde her zaman
# aktiftir — başka bir pencere odaktayken de çalışır). DİKKAT: bunlar
# GENEL (global) kısayollardır; Ctrl+R tarayıcılarda "sayfayı
# yenile" ile çakışabilir. Değiştirmek isterseniz buradaki metinleri
# düzenleyin (örn. "ctrl+shift+r").
KISAYOL_KAYDI_BASLAT = "ctrl+r"
KISAYOL_KAYDI_DURDUR = "ctrl+t"

# ------------------ DEĞİŞTİRİLEBİLİR AYARLAR ------------------
# Bu üç ayar (segment süresi, çözünürlük, kalite) program ÇALIŞIRKEN
# tepsi ikonu menüsünden değiştirilebilir. Buradaki değerler sadece
# programın ilk açılıştaki varsayılanlarıdır; ayrı bir ayar dosyası
# yoktur, her şey bu tek dosyada tanımlıdır.
SEGMENT_SECENEKLERI_DK = [1, 5, 10, 15, 30]
VARSAYILAN_SEGMENT_DK = 5

COZUNURLUK_SECENEKLERI = [
    ("Düşük (320x240 - en küçük dosya)", 320, 240),
    ("Orta (640x480)", 640, 480),
    ("Yüksek (1280x720)", 1280, 720),
    # genislik/yukseklik = None -> kaynağın GERÇEK (yerel) çözünürlüğü
    # kullanılır. Özellikle ekran kaydında önemlidir: ekran görüntüsü
    # küçük çözünürlüklere indirgenince yazılar/simgeler okunmaz hale
    # gelir. Kamera modunda da kameranın desteklediği en yüksek
    # çözünürlük istenir.
    ("Maksimum (yerel çözünürlük - en okunur, en büyük dosya)", None, None),
]
# Program varsayılan olarak en yüksek çözünürlük + en iyi kaliteyle açılır.
# Daha küçük dosya isterseniz tepsi menüsünden değiştirebilirsiniz.
VARSAYILAN_COZUNURLUK = (None, None)   # = Maksimum (yerel çözünürlük)

# Bazı kamera sürücüleri ilk kare yakalanmadan CAP_PROP_FRAME_WIDTH/HEIGHT
# için 0 döndürür. "Maksimum" modunda gerçek çözünürlük bu şekilde
# okunamazsa (0 gelirse), None yerine bu güvenli/somut değere düşülür —
# aksi halde ffmpeg'e "WxH" olarak "Nonex..." gibi geçersiz bir dize
# gider ve kayıt hiç başlamaz.
KAMERA_YEDEK_COZUNURLUK = (1920, 1080)

KALITE_SECENEKLERI = [
    ("Düşük boyut (CRF 30)", 30),
    ("Orta (CRF 23)", 23),
    ("Yüksek kalite (CRF 18 - büyük dosya)", 18),
]
VARSAYILAN_CRF = 18   # = Yüksek kalite

KAYIT_MODU_SECENEKLERI = [
    ("Kamera", "kamera"),
    ("Ekran", "ekran"),
]
VARSAYILAN_KAYIT_MODU = "kamera"

# Ses yakalama ile ilgili ayar: tek bir ses parçasının (ör. sadece
# mikrofon) WAV olarak kaydedilirken kullanılan arabellek boyutu
SES_CHUNK = 1024
# ----------------------------------------------

# ------------------ KULLANIM KILAVUZU (programın İÇİNDE) ------------------
# Ayrı bir kılavuz dosyasına ihtiyaç kalmaması için kullanım kılavuzu
# doğrudan programın içinde tutulur; tepsi menüsündeki "Kullanım
# Kılavuzu" öğesiyle açılır. Program güncellendiğinde bu metin de
# burada güncellenir — tek doğru kaynak budur.
KILAVUZ_METNI = f"""DESKCAMREC — KULLANIM KILAVUZU

DeskCamREC; bilgisayarınızın kamerasından veya ekranından,
isterseniz sesle birlikte, otomatik olarak video kaydı alan basit bir
programdır.

1) PROGRAMI ÇALIŞTIRMA
   Programı çift tıklayın. Hiçbir pencere açılmaz; görev çubuğunun
   sağ alt köşesinde (gerekirse ok işaretine tıklayın) bir daire
   simgesi belirir ve kayıt otomatik başlar.

   Simge rengi:
     Kırmızı  = Kayıt yapılıyor
     Gri      = Kayıt durdurulmuş
     Turuncu  = Bir sorun var (kamera/ekran açılamadı)

2) AYARLARI DEĞİŞTİRME
   Tepsi simgesine SOL tıklayın. Açılan pencereden şunlar ayarlanır:
     - Kayıt Modu (Kamera / Ekran)
     - Kayıt süresi (segment): {", ".join(str(d) for d in SEGMENT_SECENEKLERI_DK)} dakika
     - Çözünürlük ve Kalite / dosya boyutu
     - Ses (Mikrofon / Bilgisayar Sesi)
     - Kayıt Klasörü
     - Klavye Kısayolları
   Kaydet'e bastığınızda değişiklikler anında, kesintisiz uygulanır.
   Simgeye SAĞ tıklayarak da tek tek hızlı değişiklik yapabilirsiniz.

3) KLAVYE KISAYOLLARI (varsayılan)
     Ctrl+R = Kaydı başlat
     Ctrl+T = Kaydı durdur
   Farklı bir kombinasyon istiyorsanız Ayarlar penceresinden değiştirin.
   Not: Ctrl+R bazı tarayıcılarda "sayfayı yenile" ile çakışabilir.

4) KAYITLARIM NEREDE?
   Varsayılan klasör: {VARSAYILAN_CIKTI_KLASORU}
   Açmak için simgeye sağ tıklayıp "Kayıtlar klasörünü aç"ı seçin.
   Farklı bir klasör istiyorsanız Ayarlar penceresinden değiştirin.

5) SIK SORULAN SORULAR
   Simgeyi göremiyorum:
     Görev çubuğundaki ok (^) işaretine tıklayın, gizli simgeler arasında.
   Kaydı durdurmak istiyorum:
     Simgeye sağ tıklayıp "Kaydı Durdur" veya Ctrl+T.
   Programdan çıkmak istiyorum:
     Simgeye sağ tıklayıp en alttaki "Çıkış".
   Dosya boyutu çok büyük:
     Ayarlar'dan çözünürlüğü ve kaliteyi düşürün.
   "(cihaz yok)" yazıyor:
     Windows Ses Ayarları'ndan bir mikrofon/hoparlörün etkin ve
     varsayılan olarak seçili olduğundan emin olun.
   Program açılırken hata veriyor:
     İnternet bağlantınızı kontrol edip tekrar çalıştırın.
   Simge turuncu oluyor / ilk kayıt denememde biraz bekliyor:
     Program dosyasını küçük tutmak için ffmpeg programı içine
     gömülmez; İLK kayıt denemenizde (sadece bir kez, internetten)
     otomatik indirilir. İnternet yoksa simge turuncu olur ve
     bağlantı gelince kayıt kendiliğinden başlar.
"""
# ----------------------------------------------------------------------


_FFMPEG_YOLU_ONBELLEK = None


def ffmpeg_yolunu_getir():
    """ffmpeg'in çalıştırılabilir dosyasının yolunu döndürür.

    ÖNEMLİ - DERLENMİŞ .EXE BOYUTUNU KÜÇÜK TUTMAK İÇİN TASARIM KARARI:
    ffmpeg (tek başına ~70-80 MB) derlenmiş exe'nin İÇİNE gömülmez.
    Bunun yerine:
      1) Önce sistemde (PATH'te) kurulu bir ffmpeg var mı diye bakılır.
      2) Yoksa, imageio-ffmpeg kütüphanesi çağrılır: eğer ffmpeg zaten
         indirilmişse (önceki çalıştırmadan) onu kullanır; hiç yoksa,
         kütüphanenin KENDİ resmi kaynağından (GitHub Releases, HTTPS)
         ffmpeg'i otomatik indirip kullanıcının yerel önbellek
         klasörüne (örn. %LOCALAPPDATA%) kaydeder ve yolunu döndürür.
    Bu sayede exe dosyası küçük kalır; ffmpeg sadece GERÇEKTEN ilk kayıt
    denendiğinde (program açılışında DEĞİL) ve sadece BİR KEZ indirilir,
    sonraki çalıştırmalarda zaten diskte olduğu için tekrar inmez.
    İndirme internet gerektirir; bu fonksiyonu çağıran kod (bkz.
    kayit_dongusu) olası ağ hatalarını zaten yakalayıp kullanıcıyı
    bilgilendirip otomatik olarak yeniden deniyor."""
    global _FFMPEG_YOLU_ONBELLEK
    if _FFMPEG_YOLU_ONBELLEK and Path(_FFMPEG_YOLU_ONBELLEK).exists():
        return _FFMPEG_YOLU_ONBELLEK

    sistemdeki = shutil.which("ffmpeg")
    if sistemdeki:
        _FFMPEG_YOLU_ONBELLEK = sistemdeki
        return sistemdeki

    _FFMPEG_YOLU_ONBELLEK = imageio_ffmpeg.get_ffmpeg_exe()
    return _FFMPEG_YOLU_ONBELLEK


def varsayilan_mikrofon_cihazi(p):
    """Windows'un o an VARSAYILAN olarak ayarlı mikrofon/giriş cihazını
    WASAPI üzerinden döndürür (cihaz adı eşleştirmeye gerek yoktur)."""
    try:
        wasapi_bilgisi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        indeks = wasapi_bilgisi.get("defaultInputDevice", -1)
        if indeks is None or indeks < 0:
            return None
        return p.get_device_info_by_index(indeks)
    except Exception as e:
        print(f"Varsayılan mikrofon bulunamadı: {e}")
        return None


def varsayilan_sistem_sesi_cihazi(p):
    """Windows'un o an VARSAYILAN çıkış (hoparlör/kulaklık) cihazının
    'loopback' (bilgisayardan çalınan sesi dinleyen) karşılığını
    WASAPI üzerinden döndürür. Bu, 'Stereo Mix' gibi ayrıca
    etkinleştirilmesi gereken bir kayıt cihazına ihtiyaç duymaz."""
    try:
        wasapi_bilgisi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        hoparlor_indeks = wasapi_bilgisi.get("defaultOutputDevice", -1)
        if hoparlor_indeks is None or hoparlor_indeks < 0:
            return None
        hoparlor = p.get_device_info_by_index(hoparlor_indeks)

        if hoparlor.get("isLoopbackDevice"):
            return hoparlor

        for loopback in p.get_loopback_device_info_generator():
            if hoparlor["name"] in loopback["name"]:
                return loopback
    except Exception as e:
        print(f"Varsayılan sistem sesi (loopback) cihazı bulunamadı: {e}")
    return None


def _ses_akisini_kaydet(p, cihaz, dosya_yolu, durdur_event):
    """Verilen ses cihazından (mikrofon veya loopback) durdur_event
    tetiklenene kadar sürekli okuyup bir WAV dosyasına yazar. Ayrı bir
    thread içinde çalıştırılmak üzere tasarlanmıştır."""
    try:
        kanal_sayisi = max(1, int(cihaz["maxInputChannels"]))
        ornek_hizi = int(cihaz["defaultSampleRate"])
        akis = p.open(
            format=pyaudio.paInt16,
            channels=kanal_sayisi,
            rate=ornek_hizi,
            input=True,
            input_device_index=cihaz["index"],
            frames_per_buffer=SES_CHUNK,
        )
    except Exception as e:
        print(f"Ses akışı açılamadı ({cihaz.get('name', '?')}): {e}")
        return

    try:
        wav_dosyasi = wave.open(str(dosya_yolu), "wb")
        wav_dosyasi.setnchannels(kanal_sayisi)
        wav_dosyasi.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wav_dosyasi.setframerate(ornek_hizi)
    except Exception as e:
        print(f"Ses dosyası oluşturulamadı: {e}")
        akis.stop_stream()
        akis.close()
        return

    try:
        while not durdur_event.is_set():
            try:
                veri = akis.read(SES_CHUNK, exception_on_overflow=False)
            except Exception:
                break
            wav_dosyasi.writeframes(veri)
    finally:
        akis.stop_stream()
        akis.close()
        wav_dosyasi.close()


def _ayarlar_penceresi_olustur(giris_veri):
    """Ayarlar penceresinin TÜM arayüzünü kurar ve kaydedilen sonucu
    (dict) ya da İptal/kapatma durumunda None döndürür.

    ÖNEMLİ TASARIM KARARI: Bu pencere artık tepsi ikonunun arka plan
    thread'inden DEĞİL, ayrı/bağımsız bir Python sürecinin KENDİ ana
    thread'i olarak çalıştırılıyor (bkz. ayarlar_penceresi_alt_surec_mi
    ve KameraKaydedici.ayarlar_penceresini_ac). Böylece Windows'un
    "arka plandaki süreçlere klavye/fare odağı vermeyi engelleme"
    kısıtlaması hiç devreye girmiyor; pencere normal, tıklanabilir,
    seçilebilir bir uygulama penceresi gibi davranıyor. Eskiden
    kullanılan SetForegroundWindow/AttachThreadInput gibi "odağı zorla
    alma" hileleri bu nedenle artık gerekmiyor ve kaldırıldı."""
    sonuc = {"deger": None}

    root = tk.Tk()
    root.title("DeskCamREC - Ayarlar")
    root.resizable(False, False)

    ana = tk.Frame(root, padx=18, pady=16)
    ana.pack(fill="both", expand=True)

    satir = 0

    # --- Kayıt Modu ---
    tk.Label(ana, text="Kayıt Modu:", anchor="w").grid(row=satir, column=0, sticky="w", pady=5)
    mod_degeri = tk.StringVar(value=giris_veri["kayit_modu"])
    mod_cercevesi = tk.Frame(ana)
    mod_cercevesi.grid(row=satir, column=1, sticky="w")
    for etiket, deger in KAYIT_MODU_SECENEKLERI:
        tk.Radiobutton(mod_cercevesi, text=etiket, variable=mod_degeri, value=deger).pack(side="left")
    satir += 1

    # --- Segment süresi ---
    tk.Label(ana, text="Kayıt süresi (segment):", anchor="w").grid(row=satir, column=0, sticky="w", pady=5)
    segment_combo = ttk.Combobox(ana, state="readonly", width=22,
                                  values=[f"{dk} dakika" for dk in SEGMENT_SECENEKLERI_DK])
    segment_combo.set(f"{giris_veri['segment_dakika']} dakika")
    segment_combo.grid(row=satir, column=1, sticky="w")
    satir += 1

    # --- Çözünürlük ---
    cozunurluk_degerleri = {etiket: (g, y) for etiket, g, y in COZUNURLUK_SECENEKLERI}
    guncel_cozunurluk = next(
        (etiket for etiket, g, y in COZUNURLUK_SECENEKLERI
         if g == giris_veri["genislik"] and y == giris_veri["yukseklik"]),
        list(cozunurluk_degerleri.keys())[-1],
    )
    tk.Label(ana, text="Çözünürlük:", anchor="w").grid(row=satir, column=0, sticky="w", pady=5)
    cozunurluk_combo = ttk.Combobox(ana, state="readonly", width=44, values=list(cozunurluk_degerleri.keys()))
    cozunurluk_combo.set(guncel_cozunurluk)
    cozunurluk_combo.grid(row=satir, column=1, sticky="w")
    satir += 1

    # --- Kalite ---
    kalite_degerleri = {etiket: crf for etiket, crf in KALITE_SECENEKLERI}
    guncel_kalite = next((etiket for etiket, crf in KALITE_SECENEKLERI if crf == giris_veri["crf"]),
                          list(kalite_degerleri.keys())[1])
    tk.Label(ana, text="Kalite / dosya boyutu:", anchor="w").grid(row=satir, column=0, sticky="w", pady=5)
    kalite_combo = ttk.Combobox(ana, state="readonly", width=32, values=list(kalite_degerleri.keys()))
    kalite_combo.set(guncel_kalite)
    kalite_combo.grid(row=satir, column=1, sticky="w")
    satir += 1

    # --- Ses ---
    tk.Label(ana, text="Ses:", anchor="w").grid(row=satir, column=0, sticky="w", pady=5)
    ses_cercevesi = tk.Frame(ana)
    ses_cercevesi.grid(row=satir, column=1, sticky="w")
    mikrofon_degeri = tk.BooleanVar(value=giris_veri["mikrofon_ac"])
    sistem_sesi_degeri = tk.BooleanVar(value=giris_veri["sistem_sesi_ac"])
    tk.Checkbutton(
        ses_cercevesi,
        text="Mikrofon" + ("" if giris_veri["mikrofon_cihaz_var"] else " (cihaz yok)"),
        variable=mikrofon_degeri,
    ).pack(side="left")
    tk.Checkbutton(
        ses_cercevesi,
        text="Bilgisayar Sesi" + ("" if giris_veri["sistem_cihaz_var"] else " (cihaz yok)"),
        variable=sistem_sesi_degeri,
    ).pack(side="left", padx=(10, 0))
    satir += 1

    # --- Kayıt Klasörü ---
    tk.Label(ana, text="Kayıt Klasörü:", anchor="w").grid(row=satir, column=0, sticky="w", pady=5)
    klasor_cercevesi = tk.Frame(ana)
    klasor_cercevesi.grid(row=satir, column=1, sticky="w")
    klasor_degeri = tk.StringVar(value=giris_veri["cikti_klasoru"])
    tk.Entry(klasor_cercevesi, textvariable=klasor_degeri, width=36).pack(side="left")

    def klasor_sec():
        mevcut = klasor_degeri.get()
        secilen = filedialog.askdirectory(
            parent=root,
            title="Kayıtların kaydedileceği klasörü seçin",
            initialdir=mevcut if Path(mevcut).exists() else str(Path.home()),
        )
        if secilen:
            klasor_degeri.set(secilen)

    tk.Button(klasor_cercevesi, text="Gözat...", command=klasor_sec).pack(side="left", padx=(6, 0))
    satir += 1

    # --- Klavye Kısayolları ---
    tk.Label(ana, text="Kayıt Başlat Kısayolu:", anchor="w").grid(row=satir, column=0, sticky="w", pady=5)
    baslat_kisayol_degeri = tk.StringVar(value=giris_veri["kisayol_baslat"])
    tk.Entry(ana, textvariable=baslat_kisayol_degeri, width=22).grid(row=satir, column=1, sticky="w")
    satir += 1

    tk.Label(ana, text="Kayıt Durdur Kısayolu:", anchor="w").grid(row=satir, column=0, sticky="w", pady=5)
    durdur_kisayol_degeri = tk.StringVar(value=giris_veri["kisayol_durdur"])
    tk.Entry(ana, textvariable=durdur_kisayol_degeri, width=22).grid(row=satir, column=1, sticky="w")
    satir += 1

    tk.Label(ana, text="(örn. ctrl+r, ctrl+shift+r, f9)", fg="gray", font=("", 8)).grid(
        row=satir, column=1, sticky="w"
    )
    satir += 1

    durum_etiketi = tk.Label(ana, text="", fg="red", wraplength=360, justify="left")
    durum_etiketi.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(4, 0))
    satir += 1

    def kaydet():
        g, y = cozunurluk_degerleri[cozunurluk_combo.get()]
        crf = kalite_degerleri[kalite_combo.get()]
        try:
            dakika = int(segment_combo.get().split()[0])
        except (ValueError, IndexError):
            durum_etiketi.config(text="Geçersiz segment süresi.")
            return

        yeni_klasor_metni = klasor_degeri.get().strip()
        if not yeni_klasor_metni:
            durum_etiketi.config(text="Kayıt klasörü boş olamaz.")
            return
        try:
            Path(yeni_klasor_metni).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            durum_etiketi.config(text=f"Klasör oluşturulamadı: {e}")
            return

        yeni_baslat = baslat_kisayol_degeri.get().strip().lower()
        yeni_durdur = durdur_kisayol_degeri.get().strip().lower()
        if not yeni_baslat or not yeni_durdur:
            durum_etiketi.config(text="Kısayol alanları boş olamaz.")
            return
        if yeni_baslat == yeni_durdur:
            durum_etiketi.config(text="Başlat ve durdur kısayolları aynı olamaz.")
            return

        sonuc["deger"] = {
            "kayit_modu": mod_degeri.get(),
            "segment_dakika": dakika,
            "genislik": g,
            "yukseklik": y,
            "crf": crf,
            "mikrofon_ac": mikrofon_degeri.get(),
            "sistem_sesi_ac": sistem_sesi_degeri.get(),
            "cikti_klasoru": yeni_klasor_metni,
            "kisayol_baslat": yeni_baslat,
            "kisayol_durdur": yeni_durdur,
        }
        root.destroy()

    def iptal():
        sonuc["deger"] = None
        root.destroy()

    buton_cercevesi = tk.Frame(ana)
    buton_cercevesi.grid(row=satir, column=0, columnspan=2, pady=(12, 0))
    tk.Button(buton_cercevesi, text="Kaydet", width=12, command=kaydet).pack(side="left", padx=5)
    tk.Button(buton_cercevesi, text="İptal", width=12, command=iptal).pack(side="left", padx=5)

    root.bind("<Escape>", lambda e: iptal())
    root.protocol("WM_DELETE_WINDOW", iptal)

    root.update_idletasks()
    p_genislik = root.winfo_width()
    p_yukseklik = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (p_genislik // 2)
    y_konum = (root.winfo_screenheight() // 2) - (p_yukseklik // 2)
    root.geometry(f"+{x}+{y_konum}")

    # Bu, kendi sürecimizin normal bir penceresi olduğu için (bkz.
    # fonksiyonun üstündeki açıklama), sadece standart yöntemler
    # yeterli — ekstra "zorlama" hilesine gerek yok.
    root.lift()
    root.attributes("-topmost", True)
    root.after(200, lambda: root.attributes("-topmost", False))
    root.focus_force()

    root.mainloop()
    return sonuc["deger"]


def ayarlar_penceresi_alt_surec_calistir(giris_yolu, cikis_yolu):
    """Komut satırı argümanı olarak çağrıldığında (bkz. dosyanın en
    altındaki __main__ bloğu) SADECE ayarlar penceresini gösterir,
    tepsi uygulamasının geri kalanını hiç başlatmaz. giris_yolu'ndaki
    JSON dosyasından mevcut ayarları okur; kullanıcı Kaydet'e basarsa
    yeni ayarları cikis_yolu'na JSON olarak yazar (İptal'de ya da
    pencere kapatılırsa cikis_yolu hiç oluşturulmaz)."""
    with open(giris_yolu, "r", encoding="utf-8") as f:
        giris_veri = json.load(f)

    sonuc = _ayarlar_penceresi_olustur(giris_veri)

    if sonuc is not None:
        with open(cikis_yolu, "w", encoding="utf-8") as f:
            json.dump(sonuc, f)


def _kilavuz_penceresi_olustur():
    """Kullanım kılavuzunu salt-okunur, kaydırılabilir bir pencerede
    gösterir. Ayarlar penceresiyle aynı nedenle (bkz. yukarısı) AYRI bir
    alt süreç olarak çalıştırılır, böylece pencere normal odak/tıklama
    davranışına sahip olur."""
    root = tk.Tk()
    root.title("DeskCamREC - Kullanım Kılavuzu")
    root.geometry("640x560")

    ana = tk.Frame(root, padx=12, pady=12)
    ana.pack(fill="both", expand=True)

    metin_cercevesi = tk.Frame(ana)
    metin_cercevesi.pack(fill="both", expand=True)

    kaydirici = tk.Scrollbar(metin_cercevesi)
    kaydirici.pack(side="right", fill="y")

    metin_kutusu = tk.Text(
        metin_cercevesi, wrap="word", yscrollcommand=kaydirici.set,
        font=("Segoe UI", 10), padx=8, pady=8,
    )
    metin_kutusu.insert("1.0", KILAVUZ_METNI)
    metin_kutusu.config(state="disabled")
    metin_kutusu.pack(side="left", fill="both", expand=True)
    kaydirici.config(command=metin_kutusu.yview)

    tk.Button(ana, text="Kapat", width=12, command=root.destroy).pack(pady=(10, 0))

    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")

    root.lift()
    root.attributes("-topmost", True)
    root.after(200, lambda: root.attributes("-topmost", False))
    root.focus_force()
    root.mainloop()


class KameraKaydedici:
    def __init__(self):
        self.kayit_aktif = False
        self.calisiyor = True
        self.kayit_thread = None
        self.icon = None

        # Çalışırken menüden değiştirilebilen ayarlar
        self.segment_dakika = VARSAYILAN_SEGMENT_DK
        self.genislik, self.yukseklik = VARSAYILAN_COZUNURLUK
        self.crf = VARSAYILAN_CRF
        self.kayit_modu = VARSAYILAN_KAYIT_MODU   # "kamera" veya "ekran"
        self.mikrofon_ac = False
        self.sistem_sesi_ac = False
        self.cikti_klasoru = VARSAYILAN_CIKTI_KLASORU
        self.ayarlar_degisti = False   # ayar değişince kayıt döngüsüne haber verir

        # Klavye kısayolları (Ayarlar penceresinden değiştirilebilir)
        self.kisayol_baslat = KISAYOL_KAYDI_BASLAT
        self.kisayol_durdur = KISAYOL_KAYDI_DURDUR
        self._kisayol_tanitici_baslat = None
        self._kisayol_tanitici_durdur = None

        # Ses yakalama için kalıcı bir PyAudio örneği (program boyunca açık
        # kalır). Varsayılan mikrofon/sistem sesi cihazları HER SEGMENT
        # başında yeniden sorgulanır (bkz. _yeni_segment_baslat), böylece
        # kullanıcı çıkış/giriş cihazını değiştirse bile güncel "varsayılan"
        # cihaz kullanılır. Burada sadece menüde "(cihaz bulunamadı)"
        # uyarısını göstermek için bir kerelik bir ön kontrol yapılır.
        self.pyaudio = pyaudio.PyAudio()
        on_kontrol_mikrofon = varsayilan_mikrofon_cihazi(self.pyaudio)
        on_kontrol_sistem = varsayilan_sistem_sesi_cihazi(self.pyaudio)
        self.mikrofon_cihaz_var = on_kontrol_mikrofon is not None
        self.sistem_cihaz_var = on_kontrol_sistem is not None
        print(f"Tespit edilen varsayılan mikrofon: {on_kontrol_mikrofon['name'] if on_kontrol_mikrofon else 'bulunamadı'}")
        print(f"Tespit edilen varsayılan sistem sesi: {on_kontrol_sistem['name'] if on_kontrol_sistem else 'bulunamadı'}")

        self.cikti_klasoru.mkdir(parents=True, exist_ok=True)

    # ---------- Segment / ses-video birleştirme yardımcıları ----------
    def _yeni_segment_baslat(self, genislik, yukseklik):
        """Yeni bir segment başlatır: video her zaman stdin üzerinden ham
        karelerle ffmpeg'e akıtılır. Mikrofon ve/veya sistem sesi
        etkinse, bunlar AYNI ANDA PyAudioWPatch ile ayrı WAV dosyalarına
        kaydedilir (ffmpeg'in dshow cihaz adı eşleştirmesine hiç
        ihtiyaç duyulmaz); segment kapanırken video+ses tek dosyada
        birleştirilir (bkz. _segmenti_kapat_arka_planda)."""
        # ffmpeg yolu EN BAŞTA çözülür (gerekirse burada ilk kez internetten
        # indirilir): böylece indirme/ağ hatası olursa hiçbir ses akışı
        # başlatılmadan ve dosya oluşturulmadan erken ve temiz şekilde
        # hata fırlatılır (çağıran kayit_dongusu bunu yakalayıp bekleyip
        # tekrar dener).
        ffmpeg_yolu = ffmpeg_yolunu_getir()

        zaman_damgasi = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        on_ek = "ekran" if self.kayit_modu == "ekran" else "kayit"
        kayit_klasoru = self.cikti_klasoru
        final_dosya = kayit_klasoru / f"{on_ek}_{zaman_damgasi}.mp4"

        ses_dosyalari = []
        ses_threadleri = []
        durdur_event = threading.Event()

        if self.mikrofon_ac and self.mikrofon_cihaz_var:
            mik_cihaz = varsayilan_mikrofon_cihazi(self.pyaudio)
            if mik_cihaz:
                mik_dosya = kayit_klasoru / f"{on_ek}_{zaman_damgasi}_mikrofon_gecici.wav"
                t = threading.Thread(
                    target=_ses_akisini_kaydet,
                    args=(self.pyaudio, mik_cihaz, mik_dosya, durdur_event),
                    daemon=True,
                )
                t.start()
                ses_threadleri.append(t)
                ses_dosyalari.append(mik_dosya)
            else:
                print("Uyarı: Varsayılan mikrofon şu an bulunamadı, bu segment mikrofonsuz kaydedilecek.")

        if self.sistem_sesi_ac and self.sistem_cihaz_var:
            sis_cihaz = varsayilan_sistem_sesi_cihazi(self.pyaudio)
            if sis_cihaz:
                sis_dosya = kayit_klasoru / f"{on_ek}_{zaman_damgasi}_sistem_gecici.wav"
                t = threading.Thread(
                    target=_ses_akisini_kaydet,
                    args=(self.pyaudio, sis_cihaz, sis_dosya, durdur_event),
                    daemon=True,
                )
                t.start()
                ses_threadleri.append(t)
                ses_dosyalari.append(sis_dosya)
            else:
                print("Uyarı: Varsayılan sistem sesi şu an bulunamadı, bu segment sistem sesi olmadan kaydedilecek.")

        # Ses varsa video GEÇİCİ bir dosyaya yazılır (sonra sesle
        # birleştirilecek); ses yoksa video doğrudan asıl dosya adına
        # yazılır (ekstra birleştirme adımına gerek kalmaz, daha hızlı).
        ses_beklenior = len(ses_dosyalari) > 0
        video_hedefi = (
            kayit_klasoru / f"{on_ek}_{zaman_damgasi}_video_gecici.mp4"
            if ses_beklenior else final_dosya
        )

        video_komut = [
            ffmpeg_yolu,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{genislik}x{yukseklik}",
            "-r", str(FPS),
            "-i", "-",
            "-an",
            "-vcodec", "libx264",
            "-preset", FFMPEG_PRESET,
            "-crf", str(self.crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(video_hedefi),
        ]
        video_proc = subprocess.Popen(
            video_komut,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        ses_metni = ", ses: " + ("+".join(
            (["mikrofon"] if self.mikrofon_ac and self.mikrofon_cihaz_var else [])
            + (["sistem sesi"] if self.sistem_sesi_ac and self.sistem_cihaz_var else [])
        ) or "yok")
        print(f"Yeni segment başladı: {final_dosya} ({self.kayit_modu}, {genislik}x{yukseklik}, CRF {self.crf}{ses_metni})")

        return {
            "video_proc": video_proc,
            "video_hedefi": video_hedefi,
            "final_dosya": final_dosya,
            "ses_dosyalari": ses_dosyalari,
            "ses_threadleri": ses_threadleri,
            "durdur_event": durdur_event,
        }

    def _video_ve_sesi_birlestir(self, video_dosyasi, ses_dosyalari, hedef_dosya):
        """Video-only geçici dosyayı, bir veya iki ses WAV dosyasıyla tek
        bir mp4'te birleştirir (iki ses varsa önce karıştırılır), sonra
        geçici dosyaları siler."""
        komut = [ffmpeg_yolunu_getir(), "-y", "-i", str(video_dosyasi)]
        for sd in ses_dosyalari:
            komut += ["-i", str(sd)]

        if len(ses_dosyalari) == 2:
            komut += [
                "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=longest[aout]",
                "-map", "0:v", "-map", "[aout]",
            ]
        else:
            komut += ["-map", "0:v", "-map", "1:a"]

        komut += [
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            str(hedef_dosya),
        ]

        try:
            subprocess.run(
                komut,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                timeout=120,
            )
        except Exception as e:
            print(f"Ses/görüntü birleştirilemedi: {e}")
        finally:
            for dosya in [video_dosyasi, *ses_dosyalari]:
                try:
                    dosya.unlink(missing_ok=True)
                except Exception:
                    pass

    def _segmenti_kapat_arka_planda(self, segment):
        """Bir segmentin video sürecini ve (varsa) ses akışlarını kayıt
        akışını kesmeden arka planda düzgünce sonlandırır; ses varsa
        video+sesi birleştirip geçici dosyaları temizler."""
        def kapat():
            try:
                segment["video_proc"].stdin.close()
            except OSError:
                pass
            segment["video_proc"].wait()

            segment["durdur_event"].set()
            for t in segment["ses_threadleri"]:
                t.join(timeout=5)

            gercek_ses_dosyalari = [d for d in segment["ses_dosyalari"] if d.exists() and d.stat().st_size > 44]

            if gercek_ses_dosyalari:
                self._video_ve_sesi_birlestir(
                    segment["video_hedefi"], gercek_ses_dosyalari, segment["final_dosya"]
                )
            elif segment["video_hedefi"] != segment["final_dosya"]:
                # Ses bekleniyordu ama hiç kayıt oluşmadı (ör. cihaz o an
                # koptu); geçici video dosyasını asıl isme taşı ki kayıt
                # kaybolmasın.
                try:
                    segment["video_hedefi"].rename(segment["final_dosya"])
                except Exception as e:
                    print(f"Geçici video dosyası taşınamadı: {e}")

        threading.Thread(target=kapat, daemon=True).start()

    # ---------- Kayıt döngüsü ----------
    def kayit_dongusu(self):
        while self.calisiyor:
            if not self.kayit_aktif:
                time.sleep(0.5)
                continue

            mod = self.kayit_modu
            maksimum_istendi = self.genislik is None  # "Maksimum (yerel çözünürlük)" seçili mi?

            cap = None
            ekran_yakalayici = None
            monitor = None

            if mod == "kamera":
                cap = cv2.VideoCapture(KAMERA_INDEX, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    print("Kamera açılamadı. 5 sn sonra tekrar denenecek.")
                    self.icon_guncelle(hata=True)
                    time.sleep(5)
                    continue

                if maksimum_istendi:
                    # Kameradan destekleyebileceği en yüksek çözünürlüğü
                    # iste; sürücü isteği kendi azami değerine göre
                    # otomatik olarak sınırlar/yuvarlar.
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
                    genislik = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or KAMERA_YEDEK_COZUNURLUK[0]
                    yukseklik = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or KAMERA_YEDEK_COZUNURLUK[1]
                else:
                    genislik, yukseklik = self.genislik, self.yukseklik
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, genislik)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, yukseklik)
            else:  # "ekran"
                try:
                    ekran_yakalayici = mss.mss()
                    monitor = ekran_yakalayici.monitors[1]  # ana ekran
                except Exception as e:
                    print(f"Ekran yakalama başlatılamadı: {e}")
                    self.icon_guncelle(hata=True)
                    time.sleep(5)
                    continue

                if maksimum_istendi:
                    # Ekranın GERÇEK çözünürlüğü kullanılır; böylece
                    # yazılar/simgeler okunaksız hale gelmez.
                    genislik, yukseklik = monitor["width"], monitor["height"]
                else:
                    genislik, yukseklik = self.genislik, self.yukseklik

            try:
                aktif_segment = self._yeni_segment_baslat(genislik, yukseklik)
            except Exception as e:
                # ffmpeg bulunamadı VEYA (exe boyutunu küçük tutmak için
                # gömülmediğinden) ilk kez internetten indirilmeye
                # çalışılırken ağ hatası oluştu. Her iki durumda da
                # kısa bir süre sonra otomatik olarak yeniden denenir;
                # internet geri geldiğinde kayıt kendiliğinden başlar.
                print(f"ffmpeg hazır değil (indirilemedi/bulunamadı): {e}")
                self.icon_guncelle(hata=True)
                if cap:
                    cap.release()
                if ekran_yakalayici:
                    ekran_yakalayici.close()
                time.sleep(5)
                continue

            self.icon_guncelle(kayit=True)
            self.ayarlar_degisti = False
            segment_baslangic = time.time()

            # GERÇEK ZAMANLI SENKRONİZASYON: her segmentin kendi video
            # zaman tabanı, o segment başladığı andan itibaren saatle
            # (wall clock) ölçülür. Her döngüde "şu ana kadar GERÇEKTE
            # kaç kare geçmiş olmalıydı" hesaplanır ve yazılan kare
            # sayısı buna eşitlenir (yakalama/encode geç kaldıysa aynı
            # kare tekrar yazılarak fark kapatılır). Böylece yakalama
            # veya kodlama yavaşlasa bile (özellikle yüksek çözünürlüklü
            # ekran kaydında), videonun süresi her zaman gerçek geçen
            # süreyle birebir eşleşir — eskiden burada sabit bir
            # time.sleep(1/FPS) kullanılıyordu, bu da işlem süresini
            # hesaba katmadığı için videonun olduğundan hızlı (1.5x-2x)
            # oynatılmasına neden oluyordu.
            kare_araligi = 1.0 / FPS
            video_baslangic_zamani = segment_baslangic
            yazilan_kare_sayisi = 0

            # Kamera/ekran kaynağı bir kez açılır ve kayıt aktif olduğu
            # sürece kapanmaz; segment süresi dolunca sadece ffmpeg süreci
            # (dosya) değişir, böylece dosyalar arasında hiçbir kesinti/
            # kare kaybı olmaz. Kullanıcı menüden ayar değiştirirse
            # (mod/çözünürlük/kalite/süre/ses) mevcut segment düzgünce
            # kapatılıp yeni ayarlarla devam edilir.
            while self.calisiyor and self.kayit_aktif and not self.ayarlar_degisti:
                if mod == "kamera":
                    ret, frame = cap.read()
                    if not ret:
                        break
                else:
                    try:
                        ham_goruntu = np.array(ekran_yakalayici.grab(monitor))
                        frame = cv2.cvtColor(ham_goruntu, cv2.COLOR_BGRA2BGR)
                    except Exception as e:
                        print(f"Ekran görüntüsü alınamadı: {e}")
                        break

                if frame.shape[1] != genislik or frame.shape[0] != yukseklik:
                    frame = cv2.resize(frame, (genislik, yukseklik))

                if (time.time() - segment_baslangic) >= self.segment_dakika * 60:
                    eski_segment = aktif_segment
                    try:
                        aktif_segment = self._yeni_segment_baslat(genislik, yukseklik)
                        segment_baslangic = time.time()
                        video_baslangic_zamani = segment_baslangic
                        yazilan_kare_sayisi = 0
                    except Exception as e:
                        print(f"Yeni segment başlatılamadı ({e}), mevcut segment ile devam ediliyor.")
                        aktif_segment = eski_segment
                    else:
                        self._segmenti_kapat_arka_planda(eski_segment)

                # Gerçek geçen süreye göre kaç kare yazılmış olmalıydı?
                olmasi_gereken_kare = int((time.time() - video_baslangic_zamani) / kare_araligi) + 1
                pipe_koptu = False
                while yazilan_kare_sayisi < olmasi_gereken_kare:
                    try:
                        aktif_segment["video_proc"].stdin.write(frame.tobytes())
                    except (BrokenPipeError, OSError):
                        pipe_koptu = True
                        break
                    yazilan_kare_sayisi += 1
                if pipe_koptu:
                    break

                bekleme = video_baslangic_zamani + (yazilan_kare_sayisi * kare_araligi) - time.time()
                if bekleme > 0:
                    time.sleep(bekleme)

            if cap:
                cap.release()
            if ekran_yakalayici:
                ekran_yakalayici.close()
            self._segmenti_kapat_arka_planda(aktif_segment)

            if not self.kayit_aktif:
                self.icon_guncelle(kayit=False)
            # self.ayarlar_degisti ise döngü baştan döner ve yeni ayarlarla
            # (mod dahil) kayıt otomatik olarak yeniden başlar.

    # ---------- Tepsi ikonu ----------
    def ikon_resmi_olustur(self, renk):
        img = Image.new("RGB", (64, 64), "white")
        d = ImageDraw.Draw(img)
        d.ellipse((8, 8, 56, 56), fill=renk)
        return img

    def icon_guncelle(self, kayit=None, hata=False):
        if self.icon is None:
            return
        if hata:
            self.icon.icon = self.ikon_resmi_olustur("orange")
            self.icon.title = "DeskCamREC - HATA (kaynak açılamadı)"
        elif kayit:
            self.icon.icon = self.ikon_resmi_olustur("red")
            self.icon.title = "DeskCamREC - Kayıt yapılıyor"
        else:
            self.icon.icon = self.ikon_resmi_olustur("gray")
            self.icon.title = "DeskCamREC - Durduruldu"

    def baslat_durdur(self, icon, item):
        self.kayit_aktif = not self.kayit_aktif
        if not self.kayit_aktif:
            self.icon_guncelle(kayit=False)

    def klasoru_ac(self, icon, item):
        if sys.platform == "win32":
            os.startfile(self.cikti_klasoru)

    # ---------- Klavye kısayolu işleyicileri ----------
    def _kisayol_kaydi_baslat(self):
        if not self.kayit_aktif:
            self.kayit_aktif = True
            print(f"[Kısayol] {self.kisayol_baslat.upper()} ile kayıt başlatıldı.")

    def _kisayol_kaydi_durdur(self):
        if self.kayit_aktif:
            self.kayit_aktif = False
            print(f"[Kısayol] {self.kisayol_durdur.upper()} ile kayıt durduruldu.")

    # ---------- Ayarlar penceresi (tüm ayarlar tek ekranda) ----------
    def ayarlar_penceresini_ac(self, icon=None, item=None):
        """Tepsi ikonuna tıklanınca (veya menüden 'Ayarlar...' seçilince)
        çağrılır. Pencereyi KENDİ sürecimizin arka plan thread'inde
        değil, AYRI/bağımsız bir alt süreçte açar (aynı deskcamrec.py/exe,
        "--ayarlar-penceresi" bayrağıyla yeniden başlatılır). Bu sayede
        pencere o sürecin normal ana penceresi olur ve tıklama/seçim
        girdileri sorunsuz çalışır — Windows'un arka plan süreçlerine
        odak vermeyi engellemesi hiç devreye girmez."""
        if getattr(self, "_ayarlar_penceresi_acik", False):
            return
        self._ayarlar_penceresi_acik = True
        try:
            self._ayarlar_penceresini_ac_ic()
        finally:
            self._ayarlar_penceresi_acik = False

    # ---------- Kullanım Kılavuzu (programın içinde) ----------
    def kilavuzu_ac(self, icon=None, item=None):
        """Tepsi menüsünden 'Kullanım Kılavuzu' seçilince çağrılır;
        kılavuzu AYRI bir alt süreçte gösterir (bkz. ayarlar_penceresini_ac
        ile aynı tasarım nedeni)."""
        if getattr(self, "_kilavuz_penceresi_acik", False):
            return
        self._kilavuz_penceresi_acik = True
        try:
            komut = [sys.executable]
            if not _calisiyor_mu_derlenmis_exe():
                komut.append(os.path.abspath(__file__))
            komut.append("--kilavuz")
            try:
                subprocess.run(
                    komut,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            except Exception as e:
                print(f"Kullanım kılavuzu açılamadı: {e}")
        finally:
            self._kilavuz_penceresi_acik = False

    def _ayarlar_penceresini_ac_ic(self):
        giris_veri = {
            "kayit_modu": self.kayit_modu,
            "segment_dakika": self.segment_dakika,
            "genislik": self.genislik,
            "yukseklik": self.yukseklik,
            "crf": self.crf,
            "mikrofon_ac": self.mikrofon_ac,
            "mikrofon_cihaz_var": self.mikrofon_cihaz_var,
            "sistem_sesi_ac": self.sistem_sesi_ac,
            "sistem_cihaz_var": self.sistem_cihaz_var,
            "cikti_klasoru": str(self.cikti_klasoru),
            "kisayol_baslat": self.kisayol_baslat,
            "kisayol_durdur": self.kisayol_durdur,
        }

        with tempfile.TemporaryDirectory(prefix="data_ayarlar_") as gecici_klasor:
            giris_yolu = Path(gecici_klasor) / "giris.json"
            cikis_yolu = Path(gecici_klasor) / "cikis.json"
            with open(giris_yolu, "w", encoding="utf-8") as f:
                json.dump(giris_veri, f)

            komut = [sys.executable]
            if not _calisiyor_mu_derlenmis_exe():
                komut.append(os.path.abspath(__file__))
            komut += ["--ayarlar-penceresi", str(giris_yolu), str(cikis_yolu)]

            try:
                subprocess.run(
                    komut,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            except Exception as e:
                print(f"Ayarlar penceresi açılamadı: {e}")
                return

            if not cikis_yolu.exists():
                print("Ayarlar penceresi iptal edildi, değişiklik yapılmadı.")
                return

            with open(cikis_yolu, "r", encoding="utf-8") as f:
                yeni = json.load(f)

        # Kısayolları önce dene; başarısızsa diğer ayarları da uygulamadan
        # önceki kısayollara geri dön.
        eski_baslat, eski_durdur = self.kisayol_baslat, self.kisayol_durdur
        self.kisayol_baslat = yeni["kisayol_baslat"]
        self.kisayol_durdur = yeni["kisayol_durdur"]
        if not self._kisayollari_uygula():
            self.kisayol_baslat, self.kisayol_durdur = eski_baslat, eski_durdur
            self._kisayollari_uygula()
            print("Yeni kısayollar geçersizdi, önceki kısayollara dönüldü.")

        yeni_klasor = Path(yeni["cikti_klasoru"])
        try:
            yeni_klasor.mkdir(parents=True, exist_ok=True)
            self.cikti_klasoru = yeni_klasor
        except Exception as e:
            print(f"Kayıt klasörü ayarlanamadı, eskisi korunuyor: {e}")

        self.kayit_modu = yeni["kayit_modu"]
        self.segment_dakika = yeni["segment_dakika"]
        self.genislik = yeni["genislik"]
        self.yukseklik = yeni["yukseklik"]
        self.crf = yeni["crf"]
        self.mikrofon_ac = yeni["mikrofon_ac"]
        self.sistem_sesi_ac = yeni["sistem_sesi_ac"]
        self.ayarlar_degisti = True
        print("Ayarlar güncellendi.")

    def _kisayollari_uygula(self):
        """Mevcut self.kisayol_baslat / self.kisayol_durdur değerlerine
        göre klavye kısayollarını (yeniden) kaydeder. Önceki kayıtlı
        kısayollar varsa önce kaldırılır. Başarılıysa True döner."""
        try:
            if self._kisayol_tanitici_baslat is not None:
                keyboard.remove_hotkey(self._kisayol_tanitici_baslat)
            if self._kisayol_tanitici_durdur is not None:
                keyboard.remove_hotkey(self._kisayol_tanitici_durdur)
        except Exception:
            pass
        self._kisayol_tanitici_baslat = None
        self._kisayol_tanitici_durdur = None

        try:
            self._kisayol_tanitici_baslat = keyboard.add_hotkey(self.kisayol_baslat, self._kisayol_kaydi_baslat)
            self._kisayol_tanitici_durdur = keyboard.add_hotkey(self.kisayol_durdur, self._kisayol_kaydi_durdur)
            print(f"Klavye kısayolları etkin: {self.kisayol_baslat.upper()} = Başlat, {self.kisayol_durdur.upper()} = Durdur")
            return True
        except Exception as e:
            print(f"Klavye kısayolları ayarlanamadı: {e}")
            return False

    def cikis(self, icon, item):
        self.calisiyor = False
        self.kayit_aktif = False
        icon.stop()

    def kayit_durumu_metni(self, item):
        return "Kaydı Durdur" if self.kayit_aktif else "Kaydı Başlat"

    # ---------- Ayar değiştirme işleyicileri ----------
    def _segment_ayarla(self, dakika):
        def islenici(icon, item):
            self.segment_dakika = dakika
            self.ayarlar_degisti = True
        return islenici

    def _segment_secili_mi(self, dakika):
        return lambda item: self.segment_dakika == dakika

    def _cozunurluk_ayarla(self, genislik, yukseklik):
        def islenici(icon, item):
            self.genislik = genislik
            self.yukseklik = yukseklik
            self.ayarlar_degisti = True
        return islenici

    def _cozunurluk_secili_mi(self, genislik, yukseklik):
        return lambda item: self.genislik == genislik and self.yukseklik == yukseklik

    def _kalite_ayarla(self, crf):
        def islenici(icon, item):
            self.crf = crf
            self.ayarlar_degisti = True
        return islenici

    def _kalite_secili_mi(self, crf):
        return lambda item: self.crf == crf

    def _mod_ayarla(self, mod):
        def islenici(icon, item):
            self.kayit_modu = mod
            self.ayarlar_degisti = True
        return islenici

    def _mod_secili_mi(self, mod):
        return lambda item: self.kayit_modu == mod

    def mikrofon_degistir(self, icon, item):
        self.mikrofon_ac = not self.mikrofon_ac
        if self.mikrofon_ac and not self.mikrofon_cihaz_var:
            print("Uyarı: Sistemde varsayılan bir mikrofon cihazı tespit edilemedi.")
        self.ayarlar_degisti = True

    def mikrofon_secili_mi(self, item):
        return self.mikrofon_ac

    def sistem_sesi_degistir(self, icon, item):
        self.sistem_sesi_ac = not self.sistem_sesi_ac
        if self.sistem_sesi_ac and not self.sistem_cihaz_var:
            print("Uyarı: Varsayılan çıkış (hoparlör/kulaklık) cihazının sesi yakalanamadı.")
        self.ayarlar_degisti = True

    def sistem_sesi_secili_mi(self, item):
        return self.sistem_sesi_ac

    def calistir(self):
        self.kayit_thread = threading.Thread(target=self.kayit_dongusu, daemon=True)
        self.kayit_thread.start()

        segment_menusu = pystray.Menu(*[
            Item(
                f"{dk} dakika",
                self._segment_ayarla(dk),
                checked=self._segment_secili_mi(dk),
                radio=True,
            )
            for dk in SEGMENT_SECENEKLERI_DK
        ])

        cozunurluk_menusu = pystray.Menu(*[
            Item(
                etiket,
                self._cozunurluk_ayarla(g, y),
                checked=self._cozunurluk_secili_mi(g, y),
                radio=True,
            )
            for etiket, g, y in COZUNURLUK_SECENEKLERI
        ])

        kalite_menusu = pystray.Menu(*[
            Item(
                etiket,
                self._kalite_ayarla(crf),
                checked=self._kalite_secili_mi(crf),
                radio=True,
            )
            for etiket, crf in KALITE_SECENEKLERI
        ])

        mod_menusu = pystray.Menu(*[
            Item(
                etiket,
                self._mod_ayarla(deger),
                checked=self._mod_secili_mi(deger),
                radio=True,
            )
            for etiket, deger in KAYIT_MODU_SECENEKLERI
        ])

        ses_menusu = pystray.Menu(
            Item(
                "Mikrofonu Ekle" + ("" if self.mikrofon_cihaz_var else " (cihaz bulunamadı)"),
                self.mikrofon_degistir,
                checked=self.mikrofon_secili_mi,
            ),
            Item(
                "Bilgisayar Sesini Ekle" + ("" if self.sistem_cihaz_var else " (cihaz bulunamadı)"),
                self.sistem_sesi_degistir,
                checked=self.sistem_sesi_secili_mi,
            ),
        )

        menu = pystray.Menu(
            # default=True: tepsi ikonuna sol tıklandığında DOĞRUDAN bu
            # öğe tetiklenir, böylece tüm ayarlar (kısayollar dahil) tek
            # ekrandan açılır. Sağ tık menüsünde de ayrıca listelenir.
            Item("⚙ Ayarlar...", self.ayarlar_penceresini_ac, default=True),
            pystray.Menu.SEPARATOR,
            Item(self.kayit_durumu_metni, self.baslat_durdur),
            Item("Kayıtlar klasörünü aç", self.klasoru_ac),
            pystray.Menu.SEPARATOR,
            Item("Kayıt Modu (Kamera / Ekran)", mod_menusu),
            Item("Kayıt süresi (segment)", segment_menusu),
            Item("Çözünürlük", cozunurluk_menusu),
            Item("Kalite / dosya boyutu", kalite_menusu),
            Item("Ses", ses_menusu),
            pystray.Menu.SEPARATOR,
            Item("📖 Kullanım Kılavuzu", self.kilavuzu_ac),
            Item("Çıkış", self.cikis),
        )

        self.icon = pystray.Icon(
            "deskcamrec",
            self.ikon_resmi_olustur("gray"),
            "DeskCamREC - Durduruldu",
            menu,
        )
        # Program açılışta otomatik olarak kayda başlar
        self.kayit_aktif = True

        self._kisayollari_uygula()

        self.icon.run()


if __name__ == "__main__":
    # Bu bayrakla çağrıldıysa, SADECE ayarlar penceresini göster ve çık;
    # tepsi uygulamasının geri kalanını (kamera/ekran/ses vb.) hiç
    # başlatma. Bkz. KameraKaydedici.ayarlar_penceresini_ac — bu alt
    # süreç, ana programın tepsi ikonundan tıklanarak başlatılır.
    if len(sys.argv) >= 4 and sys.argv[1] == "--ayarlar-penceresi":
        try:
            ayarlar_penceresi_alt_surec_calistir(sys.argv[2], sys.argv[3])
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            _hata_penceresi_goster("DeskCamREC - Ayarlar Penceresi Hatası", f"{e}")
        sys.exit(0)

    # Kullanım kılavuzunu AYRI bir süreçte göstermek için (bkz.
    # KameraKaydedici.kilavuzu_ac).
    if len(sys.argv) >= 2 and sys.argv[1] == "--kilavuz":
        try:
            _kilavuz_penceresi_olustur()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            _hata_penceresi_goster("DeskCamREC - Kılavuz Hatası", f"{e}")
        sys.exit(0)

    try:
        app = KameraKaydedici()
        app.calistir()
    except Exception as e:
        import traceback
        ayrinti = traceback.format_exc()
        print(ayrinti)
        _hata_penceresi_goster(
            "DeskCamREC - Beklenmeyen Hata",
            "Program beklenmeyen bir hatayla karşılaştı ve kapanacak:\n\n"
            f"{e}\n\n"
            "Teknik ayrıntı (destek için saklayın):\n"
            f"{ayrinti}",
        )
        sys.exit(1)
