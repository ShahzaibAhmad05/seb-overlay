import os
import sys
import time
import threading
import signal
import pyperclip
import pyautogui
import keyboard

# === PyQt5 UI ===
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt5.QtGui import QFont

# === Gemini imports ===
import google.generativeai as genai

# === OCR imports ===
import pytesseract
from PIL import ImageGrab

# ========= Configuration =========
GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"

SHOW_HOTKEY = "f8"         # show the latest answer in a popup
LETTER_HOTKEY = "l"        # also show popup when pressing 'l' (lowercase only)
SCREENSHOT_HOTKEY = "m"    # press 'm' to OCR screenshot and send to Gemini
POPUP_MS = 500             # how long the popup is visible (milliseconds)
MARGIN_PX = 14             # margin from screen edges
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 8

# Screenshot region (left, top, right, bottom). Adjust as needed.
REGION_BBOX = (0, 0, pyautogui.size()[0], pyautogui.size()[1])

# If on Windows, specify the Tesseract path (update if needed)
# Comment out if Tesseract is already on PATH
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

PROMPT_TEMPLATE = """You are given a multiple-choice question copied by the user.
Reply with a SINGLE concise correct option LETTER, or the OPTION TEXT IF THE LETTER IS NOT GIVEN.
No explanations. Example: "B"

Question:
{question}
"""

# ========= Globals =========
last_answer = "No answer yet"

app = None
toast_window = None
toast_bridge = None
COUNTER_VAR = 0

gemini_client = None
gemini_model_name = None


def save_string(text: str) -> None:
    with open(f"record_mcq.txt", "a") as file:
        file.write(text + "\n\n\n")


# ========= Optional: ignore SIGINT so Ctrl+C in terminals doesn't kill the app =========
def _ignore_sigint(sig, frame):
    print("[INFO] SIGINT received (Ctrl+C) — exiting...")
    if app is not None:
        app.quit()
    else:
        sys.exit(0)
try:
    signal.signal(signal.SIGINT, _ignore_sigint)
except Exception:
    pass

# ========= Gemini config & client =========
def _load_gemini_config_from_file(path: str = "keysGemini.txt"):
    """
    Expect keysGemini.txt like:

    GEMINI_API_KEY=YOUR-KEY
    GEMINI_MODEL=gemini-2.0-flash
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        lines = []

    cfg = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()

    api_key = cfg.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    model = cfg.get("GEMINI_MODEL", "") or os.getenv("GEMINI_MODEL", GEMINI_DEFAULT_MODEL)

    if not api_key:
        print("[ERROR] Missing GEMINI_API_KEY in keysGemini.txt (or environment variable GEMINI_API_KEY).")
        return None, None

    return api_key, model

def _ensure_gemini_client():
    global gemini_client, gemini_model_name
    if gemini_client is not None and gemini_model_name is not None:
        return gemini_client, gemini_model_name

    api_key, model = _load_gemini_config_from_file()
    if not api_key or not model:
        return None, None

    try:
        genai.configure(api_key=api_key)
        gemini_client = genai.GenerativeModel(
            model_name=model,
            system_instruction="You are an expert MCQ solver. Reply with ONLY a single capital letter (A, B, C, D, etc)."
        )
        gemini_model_name = model
        print(f"[INFO] Gemini client initialized with model '{model}'.")
        return gemini_client, gemini_model_name
    except Exception as e:
        print("[ERROR] Failed to create Gemini client:", e)
        return None, None

def _extract_gemini_text(response) -> str:
    text = (getattr(response, "text", "") or "").strip()
    if text:
        return text

    # Fallback for responses where `.text` is empty but candidates still include parts.
    try:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) if content else None
            if not parts:
                continue
            for part in parts:
                p_text = (getattr(part, "text", "") or "").strip()
                if p_text:
                    return p_text
    except Exception:
        pass

    return ""


def get_gemini_answer(question_text: str) -> str:
    print("[INFO] Sending prompt to Gemini...")
    client, model = _ensure_gemini_client()
    if client is None or model is None:
        return "Gemini error: configuration or client not initialized (check keysGemini.txt)."

    try:
        prompt = PROMPT_TEMPLATE.format(question=question_text.strip())
        resp = client.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0,
            ),
        )

        text = _extract_gemini_text(resp)
        print("[INFO] Gemini responded:", text)
        return text if text else "No response"
    except Exception as e:
        print("[ERROR] Gemini API call failed:", e)
        return f"Gemini error: {e}"

# ========= PyQt5 toast window =========
class ToastWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.label = QLabel("", self)
        font = QFont(FONT_FAMILY, FONT_SIZE)
        self.label.setFont(font)
        self.label.setStyleSheet(
            "QLabel { color: #000000; background-color: rgb(240, 240, 240); "
            "padding: 1px 3px; border-radius: 6px; }"
        )

    def show_toast(self, text: str, duration_ms: int = POPUP_MS):
        print(f"[INFO] ToastWindow.show_toast: '{text}' ({duration_ms} ms)")
        single_line = text.replace("\n", " ").strip()
        self.label.setText(single_line)
        self.label.adjustSize()

        # Size based on label
        win_w = max(160, self.label.width())
        win_h = max(36, self.label.height())

        screen_w, screen_h = pyautogui.size()
        x = screen_w - win_w - int(MARGIN_PX * 2.2)
        y = screen_h - win_h + int(MARGIN_PX / 2.2)

        self.setGeometry(int(x), int(y), win_w, win_h)
        self.label.move(0, 0)

        self.show()
        QTimer.singleShot(duration_ms, self.hide)

class ToastBridge(QObject):
    # text, duration_ms
    requestToast = pyqtSignal(str, int)

    def __init__(self, window: ToastWindow):
        super().__init__()
        self.window = window
        self.requestToast.connect(self._on_request_toast)

    def _on_request_toast(self, text: str, ms: int):
        self.window.show_toast(text, ms)

def build_ui():
    global app, toast_window, toast_bridge
    app = QApplication.instance() or QApplication([])
    toast_window = ToastWindow()
    toast_bridge = ToastBridge(toast_window)
    print("[INFO] PyQt5 UI built successfully.")

def schedule_toast(text: str, ms: int = POPUP_MS):
    global toast_bridge
    if toast_bridge is None:
        print(f"[TOAST] {text}")
        return
    print(f"[DEBUG] schedule_toast emit: '{text}' ({ms} ms)")
    # This is thread-safe; Qt routes it to the GUI thread
    toast_bridge.requestToast.emit(text, ms)

# ========= Clipboard helpers =========
def _safe_paste():
    try:
        return pyperclip.paste() or ""
    except Exception as e:
        print("[ERROR] pyperclip.paste failed:", e)
        return ""

def _wait_clipboard_new_content(prev_text: str, timeout=1.0):
    """Wait up to `timeout` seconds for clipboard to change; return text or ''."""
    print("[DEBUG] Waiting for clipboard to update...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        cur = _safe_paste()
        if cur.strip() and cur != (prev_text or ""):
            print("[DEBUG] Detected new clipboard content.")
            return cur
        time.sleep(0.05)
    print("[WARN] Clipboard did not change within timeout.")
    return ""

# ========= Hotkey handlers =========
def on_detected_copy_combo():
    """Called after we detect Ctrl+C or Cmd+C on 'c' key release."""
    prev = _safe_paste()

    # Give the OS a moment to perform the copy
    time.sleep(0.12)

    # Race-proof: wait until clipboard changes (up to 1s)
    clip = _wait_clipboard_new_content(prev, timeout=1.0) or _safe_paste()

    if not clip.strip():
        print("[WARN] Clipboard empty or unchanged after copy.")
        schedule_toast("Clipboard empty")
        return

    print("[INFO] Clipboard captured (first 120 chars):")
    print(clip[:120] + ("..." if len(clip) > 120 else ""))
    save_string(clip)

    def worker():
        global last_answer, COUNTER_VAR
        ans = get_gemini_answer(clip)
        last_answer = ans
        COUNTER_VAR += 1
        save_string(last_answer)
        print("[INFO] Saved last answer:", last_answer)
        # Uncomment to show immediately:
        # schedule_toast(last_answer)

    threading.Thread(target=worker, daemon=True).start()

def _on_c_released(event):
    # Fire only if Ctrl or Command was down at release time
    ctrl = keyboard.is_pressed('ctrl')
    cmd  = keyboard.is_pressed('command') or keyboard.is_pressed('cmd')
    if ctrl or cmd:
        combo = "Ctrl+C" if ctrl else "Cmd+C"
        print(f"[INFO] Detected {combo} via key-release hook.")
        on_detected_copy_combo()

def on_show_hotkey():
    print("[INFO] Show hotkey pressed. Displaying last answer.")
    schedule_toast(f"{last_answer} ({COUNTER_VAR})")

def on_letter_release(event=None):
    print("[INFO] 'l' key released -> showing last answer.")
    schedule_toast(f"{last_answer} ({COUNTER_VAR})")

# ========= Screenshot->OCR->Gemini flow =========
def capture_ocr_text(bbox=REGION_BBOX) -> str:
    """Grab a region screenshot and return OCR text (empty string on failure)."""
    try:
        # Small delay to avoid capturing our own popup if it was just shown
        time.sleep(0.15)
        img = ImageGrab.grab(bbox=bbox)
        text = pytesseract.image_to_string(img)
        return (text or "").strip()
    except Exception as e:
        print("[ERROR] Screenshot/OCR failed:", e)
        return ""

def on_screenshot_hotkey():
    """Hotkey handler for 'm': OCR screenshot, send to Gemini."""
    print("[INFO] 'm' pressed — capturing screenshot and performing OCR...")

    def worker():
        global last_answer, COUNTER_VAR
        question_text = capture_ocr_text(REGION_BBOX)
        if not question_text:
            print("[WARN] No OCR text captured.")
            return
        print("[INFO] OCR text (first 120 chars):")
        print(question_text[:120] + ("..." if len(question_text) > 120 else ""))
        save_string(question_text)

        ans = get_gemini_answer(question_text)
        last_answer = ans
        COUNTER_VAR += 1
        save_string(last_answer)
        print("[INFO] Saved last answer (from screenshot):", last_answer)
        # Uncomment to show right away:
        # schedule_toast(last_answer, 1200)

    threading.Thread(target=worker, daemon=True).start()

# ========= Main =========
def main():
    global app
    build_ui()

    # Hotkeys
    keyboard.on_release_key(SCREENSHOT_HOTKEY, lambda e: on_screenshot_hotkey(), suppress=False)

    # Only LOWERCASE 'l' to avoid double firing
    keyboard.on_release_key(LETTER_HOTKEY, lambda e: on_letter_release(), suppress=False)

    # Also allow F8 to show last answer
    keyboard.add_hotkey(SHOW_HOTKEY, on_show_hotkey, suppress=False)

    # Also bind screenshot OCR hotkey via add_hotkey
    keyboard.add_hotkey(SCREENSHOT_HOTKEY, on_screenshot_hotkey, suppress=False, trigger_on_release=True)

    print("===================================")
    print("MCQ Helper (Gemini) Running")
    print(f"OCR Screenshot: '{SCREENSHOT_HOTKEY}'")
    print(f"Show Answer: {SHOW_HOTKEY} or '{LETTER_HOTKEY}'")
    print("===================================")

    # Test startup toast
    schedule_toast(
        f"MCQ helper (Gemini) active — OCR '{SCREENSHOT_HOTKEY}', show '{LETTER_HOTKEY}'",
        500
    )

    # Start PyQt event loop
    app.exec_()

if __name__ == "__main__":
    main()
