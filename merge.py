import os
import sys
import logging
from gui import FileMergerApp
from PyQt5.QtWidgets import QApplication

logging.basicConfig(level=logging.INFO)


def run_gui():
    app = QApplication([])
    window = FileMergerApp(files=[])
    window.show()
    return app.exec_()


if __name__ == "__main__":
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "merge.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.info(f"Logging to {log_file}")

    exit_code = run_gui()
    sys.exit(exit_code)
