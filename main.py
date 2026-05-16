import pyautogui
import time

# Safety: move mouse to top-left corner to stop the script
pyautogui.FAILSAFE = True

# Give yourself 5 seconds to click into Google Docs
time.sleep(5)

pyautogui.write("Hello, this text was typed by PyAutoGUI!", interval=0.3)