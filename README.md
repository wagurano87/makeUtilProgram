# WEBSCRAP

PowerShell에서 웹 페이지 URL을 입력하면 렌더링한 페이지 전체를 여러 장의 A4 PDF로 저장하는 Python 도구입니다. 기본 저장 위치는 Windows의 다운로드 폴더 아래 `WEBSCRAP`이며, 폴더는 자동 생성됩니다. 제목·시간·고유 번호로 파일명을 만들어 기존 PDF를 덮어쓰지 않습니다.

## Windows 설치

Python 3.10 이상을 설치하세요(`py` 실행기 포함). 이 저장소 폴더에서 PowerShell로 한 번 실행합니다.

```powershell
.\install.ps1
```

스크립트 실행 정책으로 차단되면 현재 PowerShell 창에만 적용한 후 다시 실행하세요.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\install.ps1
```

설치 스크립트는 가상환경, Playwright, Chromium을 설치하고 현재 PowerShell의 `$PROFILE`에 `WEBSCRAP` 함수를 추가합니다. 이후 같은 종류의 PowerShell을 열면 어느 폴더에서든 사용할 수 있습니다. Windows PowerShell과 PowerShell 7의 프로필은 별도이므로 각각 설치 스크립트를 실행해야 합니다. 설치 폴더를 옮겼다면 새 위치에서 다시 실행하세요. Python과 브라우저 다운로드에는 인터넷 연결이 필요합니다.

## 사용

```powershell
WEBSCRAP "https://example.com"
WEBSCRAP "https://example.com" --output-dir "D:\PDF"
```

성공하면 저장 경로가 출력됩니다. 실패하면 오류 메시지와 종료 코드 1을 반환합니다. 프로필을 변경하지 않고 실행하려면:

```powershell
.\.venv\Scripts\python.exe .\webscrap.py "https://example.com"
```

## 로그인 및 유료 콘텐츠: 열린 Chrome 연결

네이버 프리미엄 URL은 이미 실행 중인, **원격 디버깅이 활성화된 Chrome**의 세션에 연결합니다. 쿠키 이름만으로 로그인을 판정하지 않습니다. 페이지의 로그인 화면·알려진 구독 안내를 감지하면 알림을 띄우고 중단합니다. 확인 창 없이 스크롤이 끝에 도달하고 페이지 높이가 약 2초 동안 안정된 것을 확인하면 PDF를 자동 저장합니다. 사이트별 안내를 완벽하게 감지할 수는 없으므로 로그인·구독 권한 자체를 보장하지는 않습니다.

### 처음 준비하기

Google Chrome을 설치하고, 다운로드한 파일 폴더에서 실행하세요.

```powershell
.\open-chrome.ps1
```

열린 Chrome에서 네이버에 로그인하고 **Chrome을 열어 둔 채** 다음을 실행하세요.

```powershell
WEBSCRAP "https://contents.premium.naver.com/quantopia/koreanfinancetimes/contents/260930100604126ut"
```

이미 로그인했던 WEBSCRAP 프로필을 재사용하므로 로그인이 유지되어 있다면 다시 로그인할 필요가 없습니다. 예전 방식의 전용 Chrome이 열려 있다면 그 창을 먼저 닫고 `open-chrome.ps1`을 실행하세요. 프로그램은 기존 탭을 닫거나 Chrome을 종료하지 않으며, PDF를 위해 만든 탭만 정리합니다. Chrome을 닫은 후에는 `open-chrome.ps1`로 다시 열면 됩니다.

**평소 일반 방식으로 실행한 Chrome에는 자동 연결할 수 없습니다.** Chrome 136 이상에서는 기본 프로필의 원격 디버깅도 제한하므로 전용 프로필 `%LOCALAPPDATA%\WEBSCRAP\ChromeProfile`을 사용합니다. 기본 Chrome의 로그인 정보를 가져오거나 복사하지 않습니다. 전용 프로필은 이전 버전과 같은 경로여서 기존 WEBSCRAP 로그인 정보를 재사용합니다. 디버깅은 로컬 주소 `127.0.0.1:9222`에서만 연결하며, 프로필 폴더를 공유하거나 포트를 외부로 공개하지 마세요.

다른 사이트도 열린 Chrome의 로그인 상태를 사용하려면:

```powershell
WEBSCRAP "https://example.com/login" --login
WEBSCRAP "https://example.com/article" --chrome
```

`--login`은 연결된 Chrome에 로그인 탭을 열고, PowerShell에서 Enter를 누르면 탭을 그대로 둡니다. `--cdp-port`로 다른 로컬 디버깅 포트를 지정할 수도 있습니다. CAPTCHA·쿠키 동의·접힌 내용은 Chrome에서 직접 처리해야 합니다. 사이트별 로그인·유료벽을 완벽하게 자동 판별할 수는 없습니다.

페이지를 스크롤해 지연 로딩을 유도하고 배경색과 이미지를 포함해 PDF를 만듭니다. 긴 페이지는 여러 장으로 나뉩니다. 각 스크롤 확인 단계는 최대 120초 동안 진행하며, 끝에 도달하지 못하면 오류를 알리고 PDF를 저장하지 않습니다. 이미지·폰트 로딩 후에도 페이지 끝을 다시 확인합니다. 동영상이나 페이지 내부의 별도 스크롤 영역은 완전히 담기지 않을 수 있습니다.

## Linux 개발 및 검증

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PLAYWRIGHT_BROWSERS_PATH=0 .venv/bin/python -m playwright install chromium
# Chromium 실행에 필요한 OS 라이브러리가 없으면:
# .venv/bin/python -m playwright install-deps chromium
.venv/bin/python webscrap.py "https://example.com" --output-dir /tmp/webscrap-pdf
```

이미 설치된 Chromium으로 검증하려면 `WEBSCRAP_BROWSER=/usr/bin/chromium` 환경 변수를 지정할 수 있습니다.

## 보안 및 공유

프로그램 소스와 설치 파일은 공유할 수 있지만 Chrome 프로필, 로그인 쿠키, 개인정보가 포함된 PDF는 공유하지 마세요. 받는 사람은 자신의 PC에서 설치하고 자신의 계정으로 로그인해야 합니다. 유료 콘텐츠 PDF의 저장·재배포는 해당 서비스의 약관과 권리를 확인하세요.

원격 디버깅은 로그인된 브라우저를 제어할 수 있는 통로이며 별도의 비밀번호 인증이 없습니다. 같은 PC의 다른 프로그램이 접근할 수 있으므로 신뢰하는 개인 PC에서 사용하고, 작업이 끝나면 전용 Chrome 창을 모두 닫으세요. PowerShell만 닫으면 Chrome이 계속 실행될 수 있습니다. 포트를 외부에 공개하거나 포트 포워딩하지 마세요. 전용 Chrome에서는 필요한 사이트만 사용하고 Chrome과 Python을 최신 상태로 유지하세요.

현재 프로그램에는 로그인 정보나 PDF를 별도 서버로 업로드하는 기능이 없습니다. Chrome은 대상 사이트와 페이지가 사용하는 서버에 접속하며, 다운로드 폴더의 클라우드 동기화 설정에 따라 PDF가 별도로 동기화될 수 있습니다.
