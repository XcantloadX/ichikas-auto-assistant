import os
import sys

def myexcepthook(type, value, traceback, oldhook=sys.excepthook):
    print("============= 发生错误 =============")
    oldhook(type, value, traceback)
    if os.name == 'nt':
        os.system("pause")
    else:
        input("Press RETURN. ")

sys.excepthook = myexcepthook

from iaa.application.qt.index import main

if __name__ == "__main__":
  main() 
