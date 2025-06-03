from abc import ABCMeta
from PySide6.QtCore import QObject


class QObjectABCMeta(type(QObject), ABCMeta):
    """
    統一的元類，解決 QObject 和 ABC 的衝突

    這個元類允許類同時：
    1. 繼承 QObject（獲得信號槽機制）
    2. 作為抽象基類（ABC）
    3. 避免元類衝突
    """
    pass