# Özel PyInstaller hook'u: cv2 (opencv-python-headless) için varsayılan
# toplama davranışını daraltır.
#
# Bu program cv2'yi SADECE canlı kamera görüntüsü yakalamak için
# (cv2.VideoCapture(..., cv2.CAP_DSHOW)) kullanır. Video DOSYASI okuma/
# yazma hiç yapılmaz (tüm kodlama ayrı bir ffmpeg sürecine stdin ile
# ham kare akıtılarak yapılır). Bu nedenle OpenCV'nin Windows
# paketinde LİSANS nedeniyle AYRI bir eklenti DOSYASI olarak gelen
# "opencv_videoio_ffmpeg*.dll" (tek başına ~25-30 MB) ve kullanılmayan
# diğer videoio eklentileri (msmf/gstreamer/openh264) programın
# çalışması için GEREKLİ DEĞİLDİR; dışarıda bırakılması derlenmiş
# exe'nin boyutunu önemli ölçüde küçültür, cv2.CAP_DSHOW ile canlı
# kamera yakalamayı ETKİLEMEZ (o, cv2'nin ana/çekirdek kütüphanesine
# statik olarak gömülüdür, ayrı eklenti dosyası değildir).
#
# ÖNEMLİ DÜZELTME: cv2'nin kendi yükleyicisi (cv2/__init__.py),
# config.py / config-3.py dosyalarını normal bir "import" ile değil,
# dosya yolundan DİNAMİK olarak okuyarak yükler. collect_dynamic_libs()
# SADECE ikili (.dll/.pyd) dosyaları toplar, bu .py yapılandırma
# dosyalarını (ve cv2'nin ihtiyaç duyduğu diğer veri/hidden-import
# bilgilerini) KAPSAMAZ — önceki sürüm bu yüzden "config.py bulunamadı"
# hatasıyla açılışı engelliyordu. Bunun yerine collect_all() kullanılır
# (--collect-all cv2 ile TAM OLARAK AYNI, kanıtlanmış doğru yöntem);
# sadece elde edilen "binaries" listesinden istenmeyen eklenti
# DLL'leri süzülür, "datas" ve "hiddenimports" OLDUĞU GİBİ bırakılır.
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("cv2")

_DISARIDA_TUTULACAK_ANAHTAR_KELIMELER = ("ffmpeg", "msmf", "gstreamer", "openh264")

binaries = [
    (kaynak, hedef)
    for (kaynak, hedef) in binaries
    if not any(anahtar in kaynak.lower() for anahtar in _DISARIDA_TUTULACAK_ANAHTAR_KELIMELER)
]
