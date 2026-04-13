import ctypes
import time
import os

def test_mci():
    mci = ctypes.windll.winmm
    file = os.path.abspath("Knight Rider.mp3")
    print(f"Testing MCI with: {file}")
    
    # Open
    res = mci.mciSendStringW(f'open "{file}" type mpegvideo alias music', None, 0, None)
    if res != 0:
        print(f"Error opening: {res}")
        return
    
    # Play
    res = mci.mciSendStringW('play music', None, 0, None)
    if res != 0:
        print(f"Error playing: {res}")
        return
        
    print("Playing for 5 seconds...")
    time.sleep(5)
    
    # Close
    mci.mciSendStringW('close music', None, 0, None)
    print("Done.")

if __name__ == "__main__":
    test_mci()
