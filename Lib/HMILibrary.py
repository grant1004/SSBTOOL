from robot.api.deco import library, keyword
import sys
import os
from typing import Union, Optional
from enum import Enum
import time

# 獲取當前檔案所在目錄的路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from .BaseLibrary import BaseRobotLibrary
from src.interfaces.device_interface import DeviceType


class ButtonType(Enum):
    """按鈕類型枚舉"""
    UP = ("up", 2)  # 上鍵, bit 2
    DOWN = ("down", 3)  # 下鍵, bit 3
    LEFT = ("left", 1)  # 左鍵, bit 1
    RIGHT = ("right", 0)  # 右鍵, bit 0
    POWER = ("power", 4)  # 電源鍵, bit 4

    def __init__(self, name: str, bit_position: int):
        self.button_name = name
        self.bit_position = bit_position
        self.hex_value = 2 ** bit_position

    @classmethod
    def from_string(cls, button_str: str):
        """從字符串獲取按鈕類型"""
        button_str = button_str.lower().strip()
        for button in cls:
            if button.button_name == button_str:
                return button
        raise ValueError(f"不支援的按鈕類型: {button_str}")


class ActionType(Enum):
    """動作類型枚舉"""
    SHORT = ("short", 0.2, 0.2)  # 短按: 按下時間, 釋放等待時間
    LONG = ("long", 3.0, 0.2)  # 長按: 按下時間, 釋放等待時間
    UP = ("up", 0.0, 0.0)  # 按下: 只發送按下信號
    DOWN = ("down", 0.0, 0.0)  # 釋放: 只發送釋放信號

    def __init__(self, action_name: str, press_duration: float, release_wait: float):
        self.action_name = action_name
        self.press_duration = press_duration
        self.release_wait = release_wait

    @classmethod
    def from_string(cls, action_str: str):
        """從字符串獲取動作類型"""
        action_str = action_str.lower().strip()
        for action in cls:
            if action.action_name == action_str:
                return action
        raise ValueError(f"不支援的動作類型: {action_str}")


@library
class HMILibrary(BaseRobotLibrary):
    """
    HMI 測試庫 - 重構版

    提供統一的按鈕控制接口，支援多種按鈕和動作類型

    支援的按鈕類型：
    - up, down, left, right, power

    支援的動作類型：
    - short: 短按 (0.2秒按下 + 0.2秒等待)
    - long: 長按 (3.0秒按下 + 0.2秒等待)
    - up: 只按下不釋放
    - down: 只釋放按鈕
    """

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    # HMI 按鈕控制的 CAN 配置
    HMI_CAN_ID = "0x1000"
    HMI_NODE = 0
    HMI_CAN_TYPE = 1

    # 按鈕狀態追蹤
    _button_states = {
        ButtonType.UP: False,
        ButtonType.DOWN: False,
        ButtonType.LEFT: False,
        ButtonType.RIGHT: False,
        ButtonType.POWER: False
    }

    def __init__(self):
        super().__init__()
        self._logger_prefix = "HMILibrary"
        self._log_info("HMI Library initialized with unified button control")

    # ==================== 核心按鈕控制方法 ====================

    @keyword("Button Click")
    def button_click(self, button: str = "up", action: str = "short"):
        """
        統一的按鈕控制方法

        Args:
            button: 按鈕類型
                options: up|down|left|right|power
                default: up
                description: 選擇要操作的按鈕
            action: 動作類型
                options: short|long|up|down
                default: short
                description: 選擇按鈕動作類型

        Returns:
            bool: 操作是否成功

        Examples:
            | Button Click | up    | short |  # 上鍵短按
            | Button Click | power | long  |  # 電源鍵長按
            | Button Click | left  | up    |  # 左鍵按下不釋放
            | Button Click | left  | down  |  # 左鍵釋放
        """
        try:
            # 驗證設備連接
            self._validate_device_model()
            if not self.device_model.is_device_available(DeviceType.USB):
                raise RuntimeError("USB 設備不可用，無法執行按鈕操作")

            # 解析參數
            button_type = ButtonType.from_string(button)
            action_type = ActionType.from_string(action)

            self._log_info(f"執行按鈕操作: {button_type.button_name} {action_type.action_name}")

            # 執行對應的按鈕動作
            if action_type == ActionType.SHORT:
                self._perform_short_press(button_type)
            elif action_type == ActionType.LONG:
                self._perform_long_press(button_type)
            elif action_type == ActionType.UP:
                self._perform_button_down(button_type)
            elif action_type == ActionType.DOWN:
                self._perform_button_up(button_type)

            self._log_success(f"按鈕操作完成: {button_type.button_name} {action_type.action_name}")
            return True

        except Exception as e:
            error_msg = f"按鈕操作失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    @keyword("Button Short Press")
    def button_short_press(self, button: str):
        """
        按鈕短按操作

        Args:
            button: 按鈕類型
                options: up|down|left|right|power
                default: up
                description: 選擇要短按的按鈕

        Examples:
            | Button Short Press | up    |
            | Button Short Press | power |
        """
        self.button_click(button, "short")

    @keyword("Button Long Press")
    def button_long_press(self, button: str):
        """
        按鈕長按操作

        Args:
            button: 按鈕類型
                options: up|down|left|right|power
                default: power
                description: 選擇要長按的按鈕

        Examples:
            | Button Long Press | power |
            | Button Long Press | up    |
        """
        self.button_click(button, "long")

    @keyword("Button Press Down")
    def button_press_down(self, button: str):
        """
        按下按鈕（不釋放）

        Args:
            button: 按鈕類型
                options: up|down|left|right|power
                default: up
                description: 選擇要按下的按鈕

        Examples:
            | Button Press Down | left |
        """
        self.button_click(button, "up")

    @keyword("Button Release")
    def button_release(self, button: str):
        """
        釋放按鈕

        Args:
            button: 按鈕類型
                options: up|down|left|right|power
                default: up
                description: 選擇要釋放的按鈕

        Examples:
            | Button Release | left |
        """
        self.button_click(button, "down")

    @keyword("Navigation Sequence")
    def navigation_sequence(self, direction_sequence: str, press_type: str = "short"):
        """
        導航按鈕序列操作

        Args:
            direction_sequence: 方向序列
                description: 使用逗號分隔的方向序列
                example: up,down,left,right
            press_type: 按壓類型
                options: short|long
                default: short
                description: 每個方向按鈕的按壓類型

        Examples:
            | Navigation Sequence | up,down,left,right | short |
            | Navigation Sequence | up,up,right,down   | long  |
        """
        try:
            directions = [d.strip() for d in direction_sequence.split(",")]

            self._log_info(f"開始執行導航序列: {directions} ({press_type})")

            for direction in directions:
                if direction.lower() not in ["up", "down", "left", "right"]:
                    raise ValueError(f"無效的方向: {direction}")
                self.button_click(direction, press_type)
                time.sleep(0.1)  # 導航間隔

            self._log_success(f"導航序列執行完成")

        except Exception as e:
            error_msg = f"導航序列執行失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    @keyword("All Buttons Off")
    def all_buttons_off(self):
        """
        釋放所有按鈕

        Examples:
            | All Buttons Off |
        """
        try:
            self._validate_device_model()

            # 發送全部釋放信號
            self._send_button_can_message("00 00")

            # 更新所有按鈕狀態為未按下
            for button_type in self._button_states:
                self._button_states[button_type] = False

            self._log_success("所有按鈕已釋放")

        except Exception as e:
            error_msg = f"釋放所有按鈕失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    # ==================== 狀態查詢方法 ====================

    @keyword("Get Button State")
    def get_button_state(self, button: str) -> bool:
        """
        獲取按鈕狀態

        Args:
            button: 按鈕類型
                options: up|down|left|right|power
                description: 選擇要查詢狀態的按鈕

        Returns:
            bool: True 表示按下，False 表示未按下

        Examples:
            | ${state} | Get Button State | power |
            | Should Be True | ${state} |
        """
        try:
            button_type = ButtonType.from_string(button)
            state = self._button_states[button_type]
            self._log_info(f"按鈕 {button_type.button_name} 狀態: {'按下' if state else '未按下'}")
            return state

        except Exception as e:
            self._log_error(f"獲取按鈕狀態失敗: {str(e)}")
            return False

    # ==================== 私有輔助方法 ====================

    def _perform_short_press(self, button_type: ButtonType):
        """執行短按操作"""
        # 按下
        self._perform_button_down(button_type)
        time.sleep(ActionType.SHORT.press_duration)

        # 釋放
        self._perform_button_up(button_type)
        time.sleep(ActionType.SHORT.release_wait)

    def _perform_long_press(self, button_type: ButtonType):
        """執行長按操作"""
        # 按下
        self._perform_button_down(button_type)
        time.sleep(ActionType.LONG.press_duration)

        # 釋放
        self._perform_button_up(button_type)
        time.sleep(ActionType.LONG.release_wait)

    def _perform_button_down(self, button_type: ButtonType):
        """按下按鈕"""
        payload = self._generate_button_payload(button_type, True)
        self._send_button_can_message(payload)
        self._button_states[button_type] = True
        self._log_debug(f"按下 {button_type.button_name} 按鈕")

    def _perform_button_up(self, button_type: ButtonType):
        """釋放按鈕"""
        self._send_button_can_message("00 00")  # 全部釋放

        # 更新所有按鈕狀態為釋放
        for bt in self._button_states:
            self._button_states[bt] = False

        self._log_debug(f"釋放 {button_type.button_name} 按鈕")

    def _generate_button_payload(self, button_type: ButtonType, is_pressed: bool) -> str:
        """生成按鈕 CAN payload"""
        if not is_pressed:
            return "00 00"

        # 計算當前按下的按鈕組合
        combined_value = 0
        for bt, state in self._button_states.items():
            if state or bt == button_type:  # 包含即將按下的按鈕
                combined_value |= bt.hex_value

        # 如果是新按下的按鈕，添加到組合中
        if button_type not in [bt for bt, state in self._button_states.items() if state]:
            combined_value |= button_type.hex_value

        # 轉換為十六進制 payload (LSB 格式)
        hex_str = f"{combined_value:04X}"
        low_byte = hex_str[-2:]
        high_byte = hex_str[-4:-2] if len(hex_str) > 2 else "00"

        return f"{low_byte} {high_byte}"

    def _send_button_can_message(self, payload: str):
        """發送按鈕 CAN 訊息"""
        try:
            usb_device = self.device_model._device_instances.get(DeviceType.USB)
            if not usb_device:
                raise RuntimeError("無法獲取 USB 設備實例")

            # 生成 CAN 命令 (使用 CANPacketGenerator)
            from src.utils import CANPacketGenerator

            # 轉換 CAN ID
            can_id = int(self.HMI_CAN_ID, 16)

            # 轉換 payload
            payload_bytes = bytes.fromhex(payload.replace(" ", ""))

            # 生成命令
            cmd = CANPacketGenerator.generate(
                node=self.HMI_NODE,
                can_id=can_id,
                payload=payload,
                can_type=self.HMI_CAN_TYPE
            )

            # 發送命令
            result = usb_device.send_command(cmd)
            if not result:
                raise RuntimeError(f"CAN 訊息發送失敗")

            self._log_debug(f"發送 HMI CAN 訊息: ID={self.HMI_CAN_ID}, Payload={payload}")

        except Exception as e:
            raise RuntimeError(f"發送按鈕 CAN 訊息失敗: {str(e)}")

    def close(self):
        """清理資源"""
        try:
            self._log_info("開始清理 HMI Library 資源...")

            # 釋放所有按鈕
            try:
                self.all_buttons_off()
            except:
                pass

            # 調用父類清理
            super().close()

            self._log_success("HMI Library 資源清理完成")

        except Exception as e:
            self._log_error(f"清理資源時發生錯誤: {e}")