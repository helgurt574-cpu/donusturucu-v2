# Runs after the files are copied. The Python runtime is already included, so nothing is
# installed here: the window and every function are tested and the results are written down.
$root = $PSScriptRoot
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Start-Transcript -Path (Join-Path $root 'installation.log') -Append | Out-Null
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONUTF8 = '1'
$env:PATH = "$root\runtime\Library\bin;$root\runtime\Scripts;$root\runtime;" + $env:PATH
Write-Output 'Pencere baslatma testi yapiliyor.'
& "$root\runtime\python.exe" -B "$root\launch.py" --startup-test 2>&1 | Out-String | Write-Output
if ($LASTEXITCODE -ne 0) { Write-Output 'UYARI: pencere testi basarisiz. startup-error.txt dosyasina bakin.' }
Write-Output 'Tum islevler deneniyor (belge, OCR, ses, video, altyazi, konusma).'
& "$root\runtime\python.exe" -B "$root\launch.py" --self-test "$root\installation-test.json" 2>&1 | Out-String | Write-Output
if ($LASTEXITCODE -ne 0) { Write-Output 'UYARI: bazi testler basarisiz. Ayrintilar: installation-test.json' }
Write-Output 'Kurulum tamamlandi.'
Stop-Transcript | Out-Null
exit 0
