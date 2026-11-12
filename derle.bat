@echo off
setlocal

echo === Bu klasordeki dosyalar ===
dir /b *.py
echo.

if not exist "deskcamrec.py" (
    echo HATA: deskcamrec.py bu klasorde bulunamadi.
    echo Bu .bat dosyasini deskcamrec.py ile AYNI klasore koydugunuzdan emin olun.
    pause
    exit /b 1
)

echo === Python kontrol ediliyor ===
python --version
if errorlevel 1 (
    echo HATA: Python bulunamadi veya PATH'e ekli degil.
    pause
    exit /b 1
)

echo.
echo === Eski derleme kalintilari temizleniyor ===
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "DeskCamREC.spec" del /q "DeskCamREC.spec"

echo.
echo === Gerekli kutuphaneler kuruluyor ===
python -m pip install --upgrade pip
python -m pip install --upgrade pyinstaller opencv-python-headless pystray pillow imageio-ffmpeg numpy mss PyAudioWPatch keyboard

echo.
echo === Kutuphaneler bu Python ortaminda gercekten calisiyor mu kontrol ediliyor ===
python -c "import cv2, pystray, PIL, numpy, imageio_ffmpeg, mss, pyaudiowpatch, keyboard; print('TUM KUTUPHANELER OK')"
if errorlevel 1 (
    echo.
    echo === HATA: Bir veya daha fazla kutuphane bu Python ortaminda calismiyor ===
    echo Yukaridaki hatayi kopyalayip paylasin. PyInstaller derlemesi
    echo baslatilmayacak, cunku calismayan bir kutuphane exe'ye de
    echo dogru paketlenemez.
    pause
    exit /b 1
)

echo.
echo === EXE derleniyor (python -m PyInstaller kullaniliyor) ===
REM NOT (exe boyutu kucuk kalsin diye bilerek yapilan tasarim):
REM   - cv2 icin artik "opencv-python-headless" kullaniliyor (GUI/Qt
REM     kismi hic yok, bu program onu hic kullanmiyordu).
REM   - cv2 ve imageio_ffmpeg icin --collect-all BILEREK KULLANILMIYOR:
REM     cv2'nin kendi PyInstaller kancasi (hook) zaten calismasi icin
REM     gerekeni topluyor, --collect-all ise kullanilmayan ekstra veri
REM     dosyalarini da pakete katip exe'yi sismirir. imageio_ffmpeg'in
REM     icindeki ~70-80 MB'lik ffmpeg programi BILEREK exe'ye GOMULMUYOR;
REM     program ilk gercek kayit denemesinde ffmpeg'i resmi kaynaktan
REM     (GitHub Releases, HTTPS) otomatik indirip bilgisayara bir kere
REM     kaydeder, sonraki calistirmalarda tekrar inmez. Bu, kucuk exe +
REM     "gerekli eklentileri kendisi internetten guvenli sekilde kurar"
REM     isteginin karsiligidir.
REM   - hooks\hook-cv2.py (--additional-hooks-dir ile): cv2'nin Windows
REM     paketinde AYRI dosya olarak gelen opencv_videoio_ffmpeg*.dll
REM     eklentisini (~25-30 MB, lisans nedeniyle ayri dagitilir) ve
REM     kullanilmayan msmf/gstreamer eklentilerini disarida tutar. Bu
REM     program video dosyasi okuma/yazma icin cv2'yi HIC kullanmaz
REM     (sadece canli kamera yakalama icin CAP_DSHOW), bu yuzden
REM     guvenlidir.
REM   - Istege bagli EK kucultme: UPX kurulup PATH'e eklenirse (upx.exe,
REM     https://github.com/upx/upx/releases) PyInstaller onu otomatik
REM     fark edip exe'yi ek olarak sikistirir. Bu BAT dosyasi UPX'i
REM     SIZDEN ONAY ALMADAN indirmez; isterseniz kendiniz kurup PATH'e
REM     ekleyebilirsiniz.
if not exist "hooks\hook-cv2.py" (
    echo HATA: hooks\hook-cv2.py bulunamadi. Bu klasor GitHub deposundaki
    echo "hooks" alt klasoruyle birlikte kopyalanmis olmali.
    pause
    exit /b 1
)
python -m PyInstaller --noconfirm --onefile --windowed --clean ^
    --name "DeskCamREC" ^
    --additional-hooks-dir=hooks ^
    --hidden-import=PIL._tkinter_finder ^
    --hidden-import=pystray._win32 ^
    --hidden-import=keyboard._winkeyboard ^
    --hidden-import=keyboard._winmouse ^
    --hidden-import=keyboard.mouse ^
    --collect-all mss ^
    --collect-all pyaudiowpatch ^
    --collect-all keyboard ^
    deskcamrec.py

if errorlevel 1 (
    echo.
    echo === DERLEME BASARISIZ OLDU ===
    echo Yukaridaki hata mesajini kopyalayip paylasin.
    pause
    exit /b 1
)

echo.
if exist "dist\DeskCamREC.exe" (
    echo === BASARILI ===
    echo EXE dosyaniz: dist\DeskCamREC.exe
) else (
    echo === UYARI ===
    echo Derleme hata vermedi ama dist\DeskCamREC.exe bulunamadi.
    echo dist klasorunun icerigi:
    dir dist
)

pause
