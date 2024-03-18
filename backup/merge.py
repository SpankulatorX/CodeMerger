import sys
import logging
from gui import FileMergerApp
from PyQt5.QtWidgets import QApplication


def run_gui():
    app = QApplication([])
    window = FileMergerApp(files=[])
    window.show()
    return app.exec_()


if __name__ == "__main__":
    logging.basicConfig(filename='merge.log', level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    exit_code = run_gui()
    sys.exit(exit_code)
