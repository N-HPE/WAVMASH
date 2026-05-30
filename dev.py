import os
import sys
import time
import subprocess

def get_mtimes():
    mtimes = {}
    # 감시할 폴더 및 파일 확장자 설정
    for root, _, files in os.walk("desktop_app"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                mtimes[path] = os.path.getmtime(path)
    return mtimes

def main():
    print("🚀 [Dev Mode] 코드가 변경되면 자동으로 앱을 재시작합니다...")
    current_mtimes = get_mtimes()
    
    # 앱 실행
    process = subprocess.Popen([sys.executable, "-m", "desktop_app"])
    
    try:
        while True:
            time.sleep(0.5)  # 0.5초마다 파일 변경 확인
            new_mtimes = get_mtimes()
            
            if new_mtimes != current_mtimes:
                print("\n🔄 코드 변경이 감지되었습니다! 앱을 재시작합니다...\n")
                process.terminate()
                process.wait()
                # 새 코드로 앱 다시 실행
                process = subprocess.Popen([sys.executable, "-m", "desktop_app"])
                current_mtimes = new_mtimes
            
            # 사용자가 앱을 수동으로 끄면 감시자도 같이 종료
            if process.poll() is not None:
                print("👋 앱이 종료되어 감시 모드를 마칩니다.")
                break
    except KeyboardInterrupt:
        process.terminate()

if __name__ == "__main__":
    main()
