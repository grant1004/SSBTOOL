from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


def change_icon_color(icon, color):
    px = icon.pixmap(16, 16)

    painter = QPainter(px)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(px.rect(), QColor(color))
    painter.end()

    return QIcon(px)


def setup_click_animation(button: QPushButton) -> QPushButton:
   anim = QPropertyAnimation(button, b"geometry")
   anim.setDuration(100)

   def on_pressed():
       geo = button.geometry()
       anim.setStartValue(geo)
       anim.setEndValue(QRect(geo.x() + 2, geo.y() + 2,
                            geo.width() - 4, geo.height() - 4))
       anim.start()

   def on_released():
       geo = button.geometry()
       anim.setStartValue(geo)
       anim.setEndValue(QRect(geo.x() - 2, geo.y() - 2,
                            geo.width() + 4, geo.height() + 4))
       anim.start()

   button.pressed.connect(on_pressed)
   button.released.connect(on_released)
   return button

