import sys
import time
import threading
import webbrowser
import uvicorn

def open_browser():
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"\n>>> Opening Civiora Portal in your browser: {url} ...\n")
    webbrowser.open(url)

if __name__ == "__main__":
    # Start thread to open browser
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Uvicorn server
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
