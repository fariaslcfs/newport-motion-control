import sys
import logging
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    app = QApplication(sys.argv)
    
    # Configure style
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
