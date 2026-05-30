## WaveMash Desktop (PySide6)

NiceGUI(웹) 버전과 별개로, 로컬 프로그램 느낌의 데스크톱 UI를 제공합니다.

### 실행

```powershell
cd C:\Users\junno\OneDrive\Desktop\WaveMash
pip install -r requirements.txt
python -m desktop_app
```

### 특징

- YouTube/SoundCloud: `pipeline.process_url_sync`
- Spotify: `spotify_pipeline.process_spotify_url_sync`
- 아카이브: `archive.json` 읽기/쓰기, 파일 재생/폴더 열기/삭제

### Credits

BPM/Key fallback data provided by [GetSongBPM](https://getsongbpm.com/).

