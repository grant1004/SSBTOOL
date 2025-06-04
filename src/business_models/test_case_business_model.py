# src/business_models/test_case_model.py - 純新架構版本

import asyncio
from typing import Dict, Optional, List, Callable
from enum import Enum
from PySide6.QtCore import QObject, Signal

# 導入接口
from src.interfaces.device_interface import (
    IDeviceBusinessModel, DeviceType, DeviceStatus, DeviceConnectionResult
)

# 導入 MVC 基類
from src.mvc_framework.base_model import BaseBusinessModel

# 直接導入設備實現（移除 DeviceManager 中介）
from src.device.USBDevice import USBDevice
from src.device.PowerDevice import PowerDevice
from src.device.LoaderDevice import LoaderDevice

# class TestCaseBusinessModel(BaseBusinessModel, IDeviceBusinessModel):
