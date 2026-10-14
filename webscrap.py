"""Save a rendered web page to Downloads/WEBSCRAP as a PDF."""

import argparse
import ctypes
import os
from pathlib import Path
import re
import sys
import time
import uuid
from datetime import datetime
from urllib.parse import urlsplit


class AccessRequired(RuntimeError):
    pass


def notify(message):
    """Show a native Windows message; use the terminal on other platforms."""
    if os.name == "nt":
        message_box = ctypes.windll.user32.MessageBoxW
        message_box.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p,
                               ctypes.c_wchar_p, ctypes.c_uint]
        message_box.restype = ctypes.c_int
        message_box(None, message, "WEBSCRAP", 0x30)
        return
    print(message, file=sys.stderr)


def scroll_to_end(page, timeout=120):
    """Wait for a stable document bottom, including delayed scroll loading."""
    deadline = time.monotonic() + timeout
    last_height = None
    stable = 0
    while time.monotonic() < deadline:
        page.evaluate("window.scrollBy(0, Math.max(300, window.innerHeight * 0.9))")
        page.wait_for_timeout(500)
        state = page.evaluate("""() => {
            const root = document.scrollingElement || document.documentElement;
            return {height: root.scrollHeight,
                    bottom: root.scrollTop + window.innerHeight >= root.scrollHeight - 2};
        }""")
        stable = stable + 1 if state["bottom"] and state["height"] == last_height else 0
        last_height = state["height"]
        if stable >= 4:
            return
    raise RuntimeError("페이지 끝을 확인하지 못해 PDF를 저장하지 않았습니다. 무한 스크롤 또는 계속 로딩되는 페이지인지 확인하세요.")


def is_naver_premium(url):
    return urlsplit(url).hostname == "contents.premium.naver.com"


def check_access(page, context, url):
    host = urlsplit(page.url).hostname or ""
    if host in {"nid.naver.com", "accounts.google.com"} or page.locator('input[type="password"]:visible').count():
        raise AccessRequired("로그인이 필요합니다. WEBSCRAP --login으로 로그인한 뒤 다시 실행하세요.")
    # Match actionable paywall prompts, not a site's ordinary navigation login link.
    prompts = ("구독하고 전체 콘텐츠 보기", "구독하고 전체보기", "구독 후 이용",
               "구독하고 읽기", "구매 후 이용", "이 콘텐츠를 보려면", "구독이 필요한 콘텐츠",
               "Subscribe to continue reading", "Subscribe to read the full article")
    text = page.locator("body").inner_text()
    if any(prompt.casefold() in text.casefold() for prompt in prompts):
        raise AccessRequired("구독 또는 구매가 필요한 안내가 표시되어 PDF 저장을 중단했습니다. Chrome에서 해당 콘텐츠의 이용 권한을 확인하세요.")


def downloads_folder():
    if os.name == "nt":
        # Windows Known Folder API also supports redirected Downloads folders.
        class GUID(ctypes.Structure):
            _fields_ = [("a", ctypes.c_uint32), ("b", ctypes.c_uint16),
                        ("c", ctypes.c_uint16), ("d", ctypes.c_ubyte * 8)]

        folder_id = GUID.from_buffer_copy(
            uuid.UUID("374DE290-123F-4565-9164-39C4925E467B").bytes_le)
        result = ctypes.c_void_p()
        shell = ctypes.WinDLL("shell32")
        shell.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), ctypes.c_uint32,
                                               ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        shell.SHGetKnownFolderPath.restype = ctypes.c_long
        if shell.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None,
                                      ctypes.byref(result)) == 0:
            try:
                return Path(ctypes.wstring_at(result.value))
            finally:
                ole = ctypes.WinDLL("ole32")
                ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
                ole.CoTaskMemFree(result)
    return Path.home() / "Downloads"


def save_pdf(url, output_dir=None, chrome=False, login=False, cdp_port=9222):
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
    from playwright.sync_api import sync_playwright

    destination = Path(output_dir) if output_dir else downloads_folder() / "WEBSCRAP"
    authenticated = chrome or login or is_naver_premium(url)
    with sync_playwright() as browser_api:
        browser = None
        if authenticated:
            try:
                browser = browser_api.chromium.connect_over_cdp(
                    f"http://127.0.0.1:{cdp_port}", timeout=5000)
            except Exception as error:
                raise AccessRequired("연결 가능한 Chrome이 없습니다. 일반 실행 중인 Chrome에는 자동 연결할 수 없습니다. 파일 폴더에서 .\\open-chrome.ps1을 실행한 후, 열린 Chrome에서 네이버에 로그인하고 다시 실행하세요.") from error
            if not browser.contexts:
                raise AccessRequired("Chrome에 사용 가능한 프로필이 없습니다.")
            context = browser.contexts[0]
        else:
            browser = browser_api.chromium.launch(
                executable_path=os.environ.get("WEBSCRAP_BROWSER") or None)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = None
        try:
            page = context.new_page()
            if authenticated:
                page.bring_to_front()
            response = page.goto(url, wait_until="load", timeout=60000)
            if response and response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}: {url}")
            if login:
                input("Chrome에서 로그인 후 이 PowerShell 창에서 Enter를 누르세요: ")
                return None
            if authenticated:
                check_access(page, context, url)
            page.emulate_media(media="screen")
            scroll_to_end(page)
            page.evaluate("""async () => {
                await Promise.race([
                    Promise.all([document.fonts.ready, ...Array.from(document.images).map(img =>
                        img.complete ? Promise.resolve() : new Promise(resolve => {
                            img.addEventListener('load', resolve, {once: true});
                            img.addEventListener('error', resolve, {once: true});
                        }))]),
                    new Promise(resolve => setTimeout(resolve, 5000))
                ]);
            }""")
            # Fonts/images can change page height after the first scroll pass.
            scroll_to_end(page)
            if authenticated:
                check_access(page, context, url)
            page.evaluate("window.scrollTo(0, 0)")
            title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", page.title()).strip(" .")[:100]
            name = title or urlsplit(url).hostname or "page"
            path = destination / f"{name}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.pdf"
            destination.mkdir(parents=True, exist_ok=True)
            page.pdf(path=str(path), format="A4", print_background=True,
                     margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"})
            return path
        finally:
            if authenticated:
                # The user owns Chrome and its existing tabs. Disconnect only.
                if page and not login:
                    page.close()
            else:
                context.close()
                browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", help="HTTP or HTTPS page URL")
    parser.add_argument("--chrome", action="store_true", help="Connect to an already running debugging-enabled Chrome")
    parser.add_argument("--login", action="store_true", help="Open a login tab in the connected Chrome; do not save a PDF")
    parser.add_argument("--cdp-port", type=int, default=9222, help="Local Chrome debugging port (default: 9222)")
    parser.add_argument("--output-dir", type=Path, help="Override Downloads/WEBSCRAP")
    args = parser.parse_args()
    if not 1 <= args.cdp_port <= 65535:
        parser.error("--cdp-port must be between 1 and 65535.")
    if not args.url:
        if not args.login:
            parser.error("A URL is required.")
        args.url = "https://nid.naver.com/nidlogin.login"
    parsed = urlsplit(args.url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        parser.error("URL must start with http:// or https:// and contain a host.")
    try:
        path = save_pdf(args.url, args.output_dir, args.chrome, args.login, args.cdp_port)
        print(f"Saved: {path}" if path else "Chrome remains open. Run WEBSCRAP with the article URL.")
    except Exception as error:
        print(f"WEBSCRAP failed: {error}", file=sys.stderr)
        if args.chrome or args.login or is_naver_premium(args.url):
            notify(str(error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
