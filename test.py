import threading
import sys
import traceback


def repeat():
    try:
        print("in repeat method...")
        print('hi')
        timer = threading.Timer(10, repeat)
        # add_script_run_ctx(timer)
        raise Exception
        timer.start()
    except Exception as e:
        print(sys.exc_info())
        print(traceback.format_exc())
        timer = threading.Timer(10, repeat)
        timer.start()


repeat()
