import os
import sys
import threading
from cy_app import *

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

if __name__ == "__main__":
    event = threading.Event()

    fastapi_thread = threading.Thread(target=start_service)
    gradio_thread = threading.Thread(target=start_gradio, args=(True,))

    fastapi_thread.start()
    gradio_thread.start()

    fastapi_thread.join()
    gradio_thread.join()