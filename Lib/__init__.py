import os
import sys

# 將當前目錄(Lib)添加到sys.path，只添加一次
lib_dir = os.path.dirname(os.path.abspath(__file__))
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)



from .CommonLibrary import CommonLibrary
from .PEL500 import PEL500
from .HMILibrary import HMILibrary
from .UDP6730 import UDP6730
from .SSB_Dongle import AsyncCDC, CanPacket
from .BatteryLibrary import BatteryLibrary
from .BaseLibrary import BaseRobotLibrary

__all__ = [
    "CommonLibrary",
    "AsyncCDC",
    "CanPacket",
    "PEL500",
    "HMILibrary",
    "UDP6730",
    "BatteryLibrary",
    "BaseRobotLibrary"
]