import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import ui

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet( ui.Theme.get_style_sheet() )
    window = ui.MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()