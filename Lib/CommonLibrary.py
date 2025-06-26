import re
import sys
import os
from typing import Union, Set, List, Dict, Any, Optional

# 導入新的架構組件
from src.interfaces.device_interface import DeviceType, DeviceStatus

# 獲取當前檔案所在目錄的路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import time
import asyncio
from datetime import datetime, timedelta
from robot.api.deco import library, keyword
from src.utils import CANPacketGenerator
from Lib.BaseLibrary import BaseRobotLibrary
from robot.utils import timestr_to_secs


@library(scope='GLOBAL')
class CommonLibrary(BaseRobotLibrary):
    """
    通用測試庫 - 重構版本
    提供 CAN 通信、設備控制和基礎測試功能
    """

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        # 調用父類初始化
        super().__init__()
        # 父類已經設置了 _logger_prefix，這裡可以覆蓋為更具體的名稱
        self._logger_prefix = "CommonLibrary"
        self._log_info("CommonLibrary initialized with new MVC architecture")

    # region ===================== robot keyword ==================================
    @keyword("Send CAN Message")
    def send_can_message(self, can_id: Union[str, int], payload: str, node: int = 1, can_type: int = 0):
        """
        發送 CAN 訊息

        Args:
            can_id: CAN 訊息識別碼 (支援十進制或十六進制格式，如 '0x123' 或 '291')
            payload: 訊息數據
            node: 目標節點編號 (1=公共, 0=私有)
            can_type: CAN 訊息類型 (0=標準, 1=擴展)

        Examples:
            | Send CAN Message | 0x123 | FF00 | 1 | 0 |
            | Send CAN Message | 291   | AA55 |   |   |

        Returns:
            bool: 發送是否成功


        """
        try:
            payload = payload.replace("\"", "").replace("'", "").strip()
            can_id = can_id.replace( "\"", "").replace("'", "").strip()
            # 1. 驗證設備業務模型
            self._validate_device_model()

            # 2. 檢查 USB 設備是否可用
            if not self.device_model.is_device_available(DeviceType.USB):
                device_status = self.device_model.get_device_status(DeviceType.USB)
                raise RuntimeError(f"USB 設備不可用，當前狀態: {device_status.value}")

            # 3. 檢查是否可以執行 CAN 通信操作
            if not self.device_model.can_perform_operation(DeviceType.USB, "can_communication"):
                raise RuntimeError("USB 設備當前無法執行 CAN 通信操作")

            # 4. 獲取 USB 設備實例
            usb_device = self.device_model._device_instances.get(DeviceType.USB)
            if not usb_device:
                raise RuntimeError("無法獲取 USB 設備實例")

            # 5. 參數驗證和轉換
            can_id_int = self._convert_can_id(can_id)
            payload_validated = self._validate_payload(payload)
            node = int(node)
            can_type = int(can_type)

            # 6. 生成 CAN 封包
            cmd = CANPacketGenerator.generate(
                node=node,
                can_id=can_id_int,
                payload=payload_validated,
                can_type=can_type
            )

            # 7. 發送命令
            result = usb_device.send_command(cmd)

            if not result:
                raise RuntimeError(f"CAN 訊息發送失敗 - ID: 0x{can_id_int:X}")

            # 8. 記錄成功
            self._log_success(
                f"CAN 訊息發送成功 - ID: 0x{can_id_int:X}, Node: {node}, "
                f"Type: {can_type}, Payload: {payload_validated}"
            )

            return True

        except Exception as e:
            error_msg = f"CAN 訊息發送失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    @keyword
    def delay(self, seconds, reason=None):
        """
        暫停執行指定的秒數

        Args:
            seconds: 暫停的秒數，可以是整數、浮點數或時間字符串 (如 '2.5s', '1m 30s')
            reason: 可選參數，記錄暫停原因

        Examples:
            | Delay | 2.5 |
            | Delay | 1m 30s | Waiting for device initialization |
            | Delay | 5 | Allow system to stabilize |
        """
        try:
            # 轉換時間參數
            if isinstance(seconds, str):
                seconds_float = timestr_to_secs(seconds)
            else:
                seconds_float = float(seconds)

            if seconds_float < 0:
                raise ValueError("延遲時間不能為負數")

            # 記錄暫停信息
            if reason:
                self._log_info(f"延遲 {seconds_float} 秒: {reason}")
            else:
                self._log_info(f"延遲 {seconds_float} 秒")

            # 使用非阻塞方式實現延遲
            start_time = time.time()
            end_time = start_time + seconds_float
            sleep_interval = 0.1  # 每次睡眠 0.1 秒

            while time.time() < end_time:
                remaining_time = end_time - time.time()
                actual_sleep = min(sleep_interval, remaining_time)

                if actual_sleep > 0:
                    time.sleep(actual_sleep)
                else:
                    break

            actual_duration = time.time() - start_time
            self._log_success(f"延遲完成，實際時間: {actual_duration:.2f} 秒")

        except Exception as e:
            error_msg = f"延遲執行失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    @keyword
    def check_payload(self, expected_payload=None, expected_can_id=None, timeout=5, **expected_fields):
        """
        高精度檢查接收到的 CAN 消息數據

        Args:
            expected_payload: 期望的 payload 數據
                description: 期望的 payload 數據，支援 XX 通配符表示不關心的位置
                example: FF XX AA 55
            expected_can_id: 期望的 CAN ID
                description: 期望的 CAN 訊息識別碼，支援 0x207 或 207 格式
                example: 0x207
            timeout: 超時時間
                default: 5
                description: 等待接收訊息的超時時間（秒）
            **expected_fields: 其他期望字段
                description: 其他期望的字段值（如 header=0xFFFF, node=1, crc32=3A00A141）

        特性:
            - 記錄開始檢查的時間
            - 檢查所有在開始時間後收到的訊息
            - 絕對，不遺漏任何 packet
            - 非同步處理，性能優化
            - 智能輪詢和記憶體管理

        Examples:
            基本用法:
            | Check Payload |
            | Check Payload | FF00AA55 |
            | Check Payload | FF 00 AA 55 |
            | Check Payload | FF00AA55 | 0x207 |

            擴展用法 - 檢查其他字段:
            | Check Payload | FF00AA55 | 0x207 | header=0xFFFF |
            | Check Payload | FF00AA55 | 0x207 | node=1 | data_length=8 |
            | Check Payload | ${EMPTY} | ${EMPTY} | systick=1452363 |
            | Check Payload | ${EMPTY} | ${EMPTY} | crc32=3A00A141 | node=1 |
            | Check Payload | FF XX AA 55 |         # 第2個byte不關心
            | Check Payload | XX 00 XX XX |         # 只檢查第2個byte為00
            | Check Payload | FF XX XX 55 | 0x207 | # 只檢查第1和第4個byte

        支持的字段:
            - timestamp: 時間戳
            - packet_type: 封包類型
            - header: Header值
            - systick: Systick值
            - node: Node值
            - can_type: CAN Type值
            - can_id: CAN ID值
            - data_length: Data Length值
            - payload: Payload數據
            - crc32: CRC32值

        Returns:
            True : 收到訊息, False : 時限內未收到訊息
        """
        try:
            self._validate_device_model()

            # 檢查 USB 設備是否可用
            if not self.device_model.is_device_available(DeviceType.USB):
                raise RuntimeError("USB 設備不可用，無法檢查 payload")

            usb_device = self.device_model._device_instances.get(DeviceType.USB)
            if not usb_device:
                raise RuntimeError("無法獲取 USB 設備實例")

            if not hasattr(usb_device, 'get_recent_messages'):
                self._log_warning("USB 設備不支持消息歷史功能，跳過檢查")
                return True

            # 使用 asyncio 運行檢查
            result =  asyncio.run(
                self._precise_message_check(
                    usb_device, expected_payload, expected_can_id, timeout, expected_fields
                ))

            if not result:
                error_msg = f"CAN 消息檢查失敗 - 在 {timeout} 秒內未收到期望的訊息"
                self._log_error(error_msg)
                raise RuntimeError(error_msg)  # 這裡拋出異常讓測試FAIL

        except Exception as e:
            error_msg = f"CAN 消息檢查失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)
    
    @keyword
    def power_set_voltage(self, voltage: float):
        """Set output voltage

        Args:
            voltage (float): Voltage value in Volts
        """
        # 2. 檢查 POWER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.POWER):
            device_status = self.device_model.get_device_status(DeviceType.POWER)
            raise RuntimeError(f"POWER 設備不可用，當前狀態: {device_status.value}")

            # 4. 獲取 USB 設備實例
        power_device = self.device_model._device_instances.get(DeviceType.POWER)
        if not power_device:
            raise RuntimeError("無法獲取 POWER 設備實例")

        
        # 7. 發送命令
        result = power_device.set_voltage(voltage)

        if not result:
            raise RuntimeError(f"發送失敗 : VOLT {voltage}")

    @keyword
    def power_output_on(self):
        """power_output_on

        """
        # 2. 檢查 POWER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.POWER):
            device_status = self.device_model.get_device_status(DeviceType.POWER)
            raise RuntimeError(f"POWER 設備不可用，當前狀態: {device_status.value}")

            # 4. 獲取 USB 設備實例
        power_device = self.device_model._device_instances.get(DeviceType.POWER)
        if not power_device:
            raise RuntimeError("無法獲取 POWER 設備實例")


        # 7. 發送命令
        result = power_device.output_on()

        if not result:
            raise RuntimeError(f"發送失敗.")

    @keyword
    def power_output_off(self):
        """
        power_output_off

        """
        # 2. 檢查 POWER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.POWER):
            device_status = self.device_model.get_device_status(DeviceType.POWER)
            raise RuntimeError(f"POWER 設備不可用，當前狀態: {device_status.value}")

            # 4. 獲取 USB 設備實例
        power_device = self.device_model._device_instances.get(DeviceType.POWER)
        if not power_device:
            raise RuntimeError("無法獲取 POWER 設備實例")

        # 7. 發送命令
        result = power_device.output_off()

        if not result:
            raise RuntimeError(f"發送失敗.")

    @keyword
    def loader_Output_On(self):
        """
                loader_Output_On

        """
        # 2. 檢查 POWER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.LOADER):
            device_status = self.device_model.get_device_status(DeviceType.LOADER)
            raise RuntimeError(f"POWER 設備不可用，當前狀態: {device_status.value}")

            # 4. 獲取 USB 設備實例
        loader_device = self.device_model._device_instances.get(DeviceType.LOADER)
        if not loader_device:
            raise RuntimeError("無法獲取 POWER 設備實例")

        # 7. 發送命令
        result = loader_device.load_on()

        if not result:
            raise RuntimeError(f"發送失敗.")

    @keyword
    def loader_Output_Off(self):
        """
                loader_Output_Off

        """
        # 2. 檢查 POWER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.LOADER):
            device_status = self.device_model.get_device_status(DeviceType.LOADER)
            raise RuntimeError(f"POWER 設備不可用，當前狀態: {device_status.value}")

            # 4. 獲取 USB 設備實例
        loader_device = self.device_model._device_instances.get(DeviceType.LOADER)
        if not loader_device:
            raise RuntimeError("無法獲取 POWER 設備實例")

        # 7. 發送命令
        result = loader_device.load_off()

        if not result:
            raise RuntimeError(f"發送失敗.")

    @keyword
    def loader_Set_Mode(self, mode):
        """
        設定電子負載操作模式

        Args:
            mode: 操作模式
                options: CC|CR|CV|CP
                description: CC=定電流, CR=定電阻, CV=定電壓, CP=定功率

        Examples:
            | loader_Set_Mode | CC |
            | loader_Set_Mode | CV |
        """
        # 檢查 LOADER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.LOADER):
            device_status = self.device_model.get_device_status(DeviceType.LOADER)
            raise RuntimeError(f"LOADER 設備不可用，當前狀態: {device_status.value}")

        # 獲取 LOADER 設備實例
        loader_device = self.device_model._device_instances.get(DeviceType.LOADER)
        if not loader_device:
            raise RuntimeError("無法獲取 LOADER 設備實例")

        # 發送命令
        result = loader_device.set_mode(mode)

        if not result:
            raise RuntimeError(f"設定模式失敗: {mode}")

    @keyword
    def loader_Set_Current(self, current_str, level="HIGH"):
        """
        設定電子負載電流值 (CC模式)

        Args:
            current_str: 電流值
                description: 電流值，單位為 mA
                example: 5000
            level: 電流範圍
                options: HIGH|LOW
                default: HIGH
                description: HIGH=高電流範圍, LOW=低電流範圍

        Examples:
            | loader_Set_Current | 5000 | HIGH |
            | loader_Set_Current | 1000 | LOW  |
        """
        # 檢查 LOADER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.LOADER):
            device_status = self.device_model.get_device_status(DeviceType.LOADER)
            raise RuntimeError(f"LOADER 設備不可用，當前狀態: {device_status.value}")

        # 獲取 LOADER 設備實例
        loader_device = self.device_model._device_instances.get(DeviceType.LOADER)
        if not loader_device:
            raise RuntimeError("無法獲取 LOADER 設備實例")

        # 轉換單位並發送命令
        current = float(current_str) / 1000  # Convert mA to A
        result = loader_device.set_current(current, level)

        if not result:
            raise RuntimeError(f"設定電流失敗: {current_str}mA ({level})")

    @keyword
    def loader_Set_Resistance(self, resistance_str, level="HIGH"):
        """
        設定電子負載電阻值 (CR模式)

        Args:
            resistance_str: 電阻值
                description: 電阻值，單位為 Ω
                example: 10
            level: 電阻範圍
                options: HIGH|LOW
                default: HIGH
                description: HIGH=高電阻範圍, LOW=低電阻範圍

        Examples:
            | loader_Set_Resistance | 10  | HIGH |
            | loader_Set_Resistance | 100 | LOW  |
        """
        # 檢查 LOADER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.LOADER):
            device_status = self.device_model.get_device_status(DeviceType.LOADER)
            raise RuntimeError(f"LOADER 設備不可用，當前狀態: {device_status.value}")

        # 獲取 LOADER 設備實例
        loader_device = self.device_model._device_instances.get(DeviceType.LOADER)
        if not loader_device:
            raise RuntimeError("無法獲取 LOADER 設備實例")

        # 發送命令
        resistance = float(resistance_str)  # Already in Ω
        result = loader_device.set_resistance(resistance, level)

        if not result:
            raise RuntimeError(f"設定電阻失敗: {resistance_str}Ω ({level})")

    @keyword
    def loader_Set_Voltage(self, voltage_str, level="HIGH"):
        """
        設定電子負載電壓值 (CV模式)

        Args:
            voltage_str: 電壓值
                description: 電壓值，單位為 mV
                example: 5000
            level: 電壓範圍
                options: HIGH|LOW
                default: HIGH
                description: HIGH=高電壓範圍, LOW=低電壓範圍

        Examples:
            | loader_Set_Voltage | 5000 | HIGH |
            | loader_Set_Voltage | 3300 | LOW  |
        """
        # 檢查 LOADER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.LOADER):
            device_status = self.device_model.get_device_status(DeviceType.LOADER)
            raise RuntimeError(f"LOADER 設備不可用，當前狀態: {device_status.value}")

        # 獲取 LOADER 設備實例
        loader_device = self.device_model._device_instances.get(DeviceType.LOADER)
        if not loader_device:
            raise RuntimeError("無法獲取 LOADER 設備實例")

        # 轉換單位並發送命令
        voltage = float(voltage_str) / 1000  # Convert mV to V
        result = loader_device.set_voltage(voltage, level)

        if not result:
            raise RuntimeError(f"設定電壓失敗: {voltage_str}mV ({level})")

    @keyword
    def loader_Set_Power(self, power_str, level="HIGH"):
        """
        設定電子負載功率值 (CP模式)

        Args:
            power_str: 功率值
                description: 功率值，單位為 mW
                example: 1000
            level: 功率範圍
                options: HIGH|LOW
                default: HIGH
                description: HIGH=高功率範圍, LOW=低功率範圍

        Examples:
            | loader_Set_Power | 1000 | HIGH |
            | loader_Set_Power | 500  | LOW  |
        """
        # 檢查 LOADER 設備是否可用
        if not self.device_model.is_device_available(DeviceType.LOADER):
            device_status = self.device_model.get_device_status(DeviceType.LOADER)
            raise RuntimeError(f"LOADER 設備不可用，當前狀態: {device_status.value}")

        # 獲取 LOADER 設備實例
        loader_device = self.device_model._device_instances.get(DeviceType.LOADER)
        if not loader_device:
            raise RuntimeError("無法獲取 LOADER 設備實例")

        # 轉換單位並發送命令
        power = float(power_str) / 1000  # Convert mW to W
        # print( power )
        result = loader_device.set_power(power, level)

        if not result:
            raise RuntimeError(f"設定功率失敗: {power_str}mW ({level})")


    # 擴展的關鍵字方法 - 提供更多選項
    # @keyword("Check Payload Advanced")
    # def check_payload_advanced(self, expected_payload=None, expected_can_id=None,
    #                            timeout=5, wildcard_char='XX', exact_length=True, **expected_fields):
    #     """
    #     高級 payload 檢查，支援通配符和更多選項
    # 
    #     Args:
    #         expected_payload: 期望的 payload 數據
    #             description: 期望的 payload 數據，支援通配符表示不關心的位置
    #             example: FF XX AA 55
    #         expected_can_id: 期望的 CAN ID
    #             description: 期望的 CAN 訊息識別碼，支援十進制或十六進制格式
    #             example: 0x207
    #         timeout: 超時時間
    #             default: 5
    #             description: 等待接收訊息的超時時間（秒）
    #         wildcard_char: 通配符字符
    #             options: XX|??|--
    #             default: XX
    #             description: 用於表示不關心位置的通配符字符
    #         exact_length: 精確長度匹配
    #             options: True|False
    #             default: True
    #             description: 是否要求 payload 長度完全匹配
    #         **expected_fields: 其他期望字段
    #             description: 其他期望的字段值，如 header、node、crc32 等
    # 
    #     Returns:
    #         bool: 檢查是否成功
    # 
    #     Examples:
    #         | Check Payload Advanced | FF XX AA 55 |           |   |       |      # 使用 XX 通配符
    #         | Check Payload Advanced | FF ?? AA 55 | 0x207     | 5 | ??    |      # 使用 ?? 通配符
    #         | Check Payload Advanced | FF -- AA 55 | 0x207     | 5 | --    |      # 使用 -- 通配符
    #     """
    #     try:
    #         # 如果指定了不同的通配符格式，先轉換
    #         if expected_payload and wildcard_char != 'XX':
    #             expected_payload = self._convert_wildcard_format(
    #                 expected_payload, from_format=wildcard_char, to_format='XX'
    #             )
    # 
    #         # 調用原始的 check_payload 方法
    #         return self.check_payload(expected_payload, expected_can_id, timeout, **expected_fields)
    # 
    #     except Exception as e:
    #         error_msg = f"高級 Payload 檢查失敗: {str(e)}"
    #         self._log_error(error_msg)
    #         raise RuntimeError(error_msg)
    #
    # @keyword
    # def wait_for_device_ready(self, device_type_str: str, timeout: int = 30):
    #     """
    #     等待設備準備就緒
    # 
    #     Args:
    #         device_type_str: 設備類型字符串
    #         timeout: 超時時間（秒）
    # 
    #     Examples:
    #         | Wait For Device Ready | USB |
    #         | Wait For Device Ready | POWER | 60 |
    #     """
    #     try:
    #         self._validate_device_model()
    # 
    #         device_type_map = {
    #             "USB": DeviceType.USB,
    #             "POWER": DeviceType.POWER,
    #             "LOADER": DeviceType.LOADER
    #         }
    # 
    #         device_type_str = device_type_str.strip().replace('\"', '')
    #         device_type = device_type_map.get(device_type_str.upper())
    #         if not device_type:
    #             raise ValueError(f"不支持的設備類型: {device_type_str}")
    # 
    #         self._log_info(f"等待設備 {device_type_str} 準備就緒，超時時間: {timeout} 秒")
    # 
    #         start_time = time.time()
    #         check_interval = 0.5  # 每 0.5 秒檢查一次
    # 
    #         while time.time() - start_time < timeout:
    #             if self.device_model.is_device_available(device_type):
    #                 elapsed_time = time.time() - start_time
    #                 self._log_success(f"設備 {device_type_str} 已準備就緒，耗時: {elapsed_time:.1f} 秒")
    #                 return True
    # 
    #             # 顯示進度
    #             elapsed = time.time() - start_time
    #             if int(elapsed) % 5 == 0 and elapsed > 0:  # 每5秒顯示一次進度
    #                 current_status = self.device_model.get_device_status(device_type)
    #                 self._log_info(f"等待中... 當前狀態: {current_status.value} ({elapsed:.0f}/{timeout}s)")
    # 
    #             time.sleep(check_interval)
    # 
    #         # 超時
    #         current_status = self.device_model.get_device_status(device_type)
    #         raise RuntimeError(
    #             f"等待設備 {device_type_str} 準備就緒超時 ({timeout} 秒)，當前狀態: {current_status.value}")
    # 
    #     except Exception as e:
    #         error_msg = f"等待設備準備就緒失敗: {str(e)}"
    #         self._log_error(error_msg)
    #         raise RuntimeError(error_msg)
    # 
    # @keyword
    # def verify_device_connection(self, device_type_str: str):
    #     """
    #     驗證設備連接狀態
    # 
    #     驗證指定設備是否正確連接並可用
    # 
    #     Args:
    #         device_type_str: 設備類型字符串 ("USB", "POWER", "LOADER")
    # 
    #     Examples:
    #         | Verify Device Connection | USB |
    #     """
    #     try:
    #         status = self.get_device_status(device_type_str)
    # 
    #         if status == "CONNECTED":
    #             self._log_success(f"設備 {device_type_str} 連接驗證通過")
    #             return True
    #         else:
    #             raise RuntimeError(f"設備 {device_type_str} 連接驗證失敗，當前狀態: {status}")
    # 
    #     except Exception as e:
    #         error_msg = f"設備連接驗證失敗: {str(e)}"
    #         self._log_error(error_msg)
    #         raise RuntimeError(error_msg)

    # endregion


    # region ==================== 輔助方法 ====================================
    def _convert_can_id(self, can_id) -> int:
        """轉換 CAN ID 為整數格式"""
        if isinstance(can_id, int):
            return can_id
        elif isinstance(can_id, str):
            can_id = can_id.strip()
            if can_id.startswith('0x') or can_id.startswith('0X'):
                return int(can_id, 16)
            else:
                return int(can_id)
        else:
            raise ValueError(f"無效的 CAN ID 格式: {can_id}")

    def _validate_payload(self, payload) -> str:
        """驗證和格式化 payload"""
        if isinstance(payload, bytes):
            return payload.hex().upper()
        elif isinstance(payload, str):
            # 移除空格和分隔符
            cleaned = payload.replace(' ', '').replace('-', '').replace(':', '')
            # 驗證是否為有效的十六進制字符串
            try:
                int(cleaned, 16)
                return cleaned.upper()
            except ValueError:
                raise ValueError(f"無效的 payload 格式: {payload}")
        else:
            raise ValueError(f"Payload 必須是字符串或字節，得到: {type(payload)}")

    def _normalize_payload(self, payload_str):
        """
        標準化 payload 字符串格式，支援 XX 通配符

        Args:
            payload_str: 輸入的 payload 字符串
                description: 可能有或沒有空格的 payload 字符串，支援 XX 表示 don't care

        Returns:
            標準化的 payload 字符串（大寫，每兩個字符用空格分隔）

        Examples:
            "FF00AA55" -> "FF 00 AA 55"
            "ff xx aa 55" -> "FF XX AA 55"
            "FF XX AA55" -> "FF XX AA 55"
        """
        if not payload_str:
            return None

        # 移除所有空格並轉為大寫
        clean_payload = payload_str.replace(' ', '').upper()

        # 檢查是否為有效的十六進制字符串或包含通配符
        valid_chars = '0123456789ABCDEFX'
        if not all(c in valid_chars for c in clean_payload):
            raise ValueError(f"無效的 payload 格式: {payload_str}")

        # 確保長度為偶數
        if len(clean_payload) % 2 != 0:
            raise ValueError(f"Payload 長度必須為偶數: {payload_str}")

        # 每兩個字符插入一個空格
        formatted_payload = ' '.join(clean_payload[i:i + 2] for i in range(0, len(clean_payload), 2))

        return formatted_payload

    def _normalize_can_id(self, can_id_str):
        """
        標準化 CAN ID 格式

        Args:
            can_id_str: 輸入的 CAN ID 字符串，可能是 "0x207", "207", "0X207" 等

        Returns:
            標準化的 CAN ID 字符串（十六進制格式，如 "0x207"）
        """
        if not can_id_str:
            return None

        can_id_str = str(can_id_str).strip()

        try:
            # 如果以 0x 或 0X 開頭，直接解析
            if can_id_str.lower().startswith('0x'):
                can_id_int = int(can_id_str, 16)
            else:
                # 假設是十進制或十六進制數字
                try:
                    # 先嘗試十六進制解析
                    can_id_int = int(can_id_str, 16)
                except ValueError:
                    # 如果失敗，嘗試十進制解析
                    can_id_int = int(can_id_str, 10)

            # 轉換為標準的十六進制格式
            return f"0x{can_id_int:X}"

        except ValueError:
            raise ValueError(f"無效的 CAN ID 格式: {can_id_str}")

    def _parse_can_message(self, message_str):
        """
        解析 CAN 消息字符串 - 簡單修正版本
        使用按行處理的方式避免跨行匹配問題
        """
        import re

        try:
            message_str = str(message_str)
            parsed_data = {}

            # 按行處理
            lines = message_str.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 時間戳行
                timestamp_match = re.match(r'\[([0-9\-\s:\.]+)\]\s*(.+)', line)
                if timestamp_match:
                    parsed_data['timestamp'] = timestamp_match.group(1).strip()
                    remainder = timestamp_match.group(2)
                    if ':' in remainder:
                        parsed_data['packet_type'] = remainder.split(':')[0].strip()
                    continue

                # 字段行 - 簡單的冒號分割
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        field_key = parts[0].strip().lower().replace(' ', '_')
                        field_value = parts[1].strip()

                        # 根據字段名稱進行特殊處理
                        if field_key == 'can_id':
                            try:
                                parsed_data['can_id'] = self._normalize_can_id(field_value)
                            except:
                                parsed_data['can_id'] = field_value
                        elif field_key == 'payload':
                            # 🔧 Payload 特殊處理：清理並標準化
                            normalized = ' '.join(field_value.split()).upper()
                            parsed_data['payload'] = normalized
                        elif field_key == 'header':
                            if not field_value.upper().startswith('0X'):
                                parsed_data['header'] = f"0x{field_value.upper()}"
                            else:
                                parsed_data['header'] = field_value.upper()
                        elif field_key == 'crc32':
                            parsed_data['crc32'] = field_value.upper()
                        else:
                            parsed_data[field_key] = field_value

            # 檢查基本字段
            if 'can_id' in parsed_data or 'payload' in parsed_data:
                parsed_data['_raw_message'] = message_str
                parsed_data['_parsed_fields_count'] = len([k for k in parsed_data.keys() if not k.startswith('_')])
                return parsed_data
            else:
                self._log_warning(f"無法從消息中提取基本字段: {message_str}")
                return None

        except Exception as e:
            self._log_error(f"解析 CAN 消息時發生錯誤: {e}")
            return None

    def close(self):
        """清理資源"""
        try:
            self._log_info("開始清理 CommonLibrary 資源...")

            # 停止所有監聽
            try:
                self.stop_listening()
            except:
                pass  # 忽略停止監聽的錯誤

            # 調用父類清理
            super().close()

            self._log_success("CommonLibrary 資源清理完成")

        except Exception as e:
            self._log_error(f"清理資源時發生錯誤: {e}")

    async def _precise_message_check(self, usb_device, expected_payload, expected_can_id, timeout, expected_fields):
        """
        🔧 修正版：精確的非同步消息檢查邏輯 - 確保只檢查指定時間後的消息
        """
        # ==================== 初始化階段 ====================

        # 🔧 關鍵：記錄檢查開始的準確時間
        start_time = time.time()
        start_datetime = datetime.now()

        self._log_info(f"🎯 開始檢查 - 系統時間: {start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        self._log_info(f"🎯 基準時間戳: {start_time}")

        # 準備期望值
        expected_values = await self._prepare_expected_values(expected_payload, expected_can_id, expected_fields)

        # 初始化追蹤變數
        total_checked_messages = 0
        polling_interval = 0.01  # 初始輪詢間隔：10ms
        max_polling_interval = 0.1  # 最大輪詢間隔：100ms

        # 性能監控
        performance_stats = {
            'polling_cycles': 0,
            'messages_processed': 0,
            'new_messages_found': 0,
            'parsing_failures': 0
        }

        # ==================== 建立基準線 ====================

        baseline_count = 0
        try:
            # 🔧 新方法：如果設備支持獲取基準線消息數量
            if hasattr(usb_device, 'get_baseline_message_count'):
                baseline_count = usb_device.get_baseline_message_count()
                self._log_info(f"📊 建立基準線: {baseline_count} 條歷史訊息將被忽略")
            else:
                # 舊方法：獲取當前所有訊息作為基準線
                baseline_messages = usb_device.get_recent_messages(1000)
                baseline_count = len(baseline_messages) if baseline_messages else 0
                self._log_info(f"📊 建立基準線: {baseline_count} 條歷史訊息")

            # 等待一小段時間，確保基準線建立完成
            await asyncio.sleep(0.01)  # 10ms

        except Exception as e:
            self._log_warning(f"建立基準線時發生錯誤: {e}")

        # ==================== 監控循環 ====================

        self._log_info(f"🔍 開始監控 {start_time} 時間戳之後的新訊息...")

        try:
            while (time.time() - start_time) < timeout:
                performance_stats['polling_cycles'] += 1
                cycle_start = time.time()
                new_messages = []

                try:
                    # 🔧 關鍵改進：只獲取指定時間之後的消息
                    if hasattr(usb_device, 'get_messages_after_time'):
                        # 使用新的精確方法
                        new_messages = usb_device.get_messages_after_time(start_time, 100)

                        if new_messages:
                            performance_stats['new_messages_found'] += len(new_messages)
                            self._log_info(f"📥 發現 {len(new_messages)} 條新訊息（基準時間後）")
                    else:
                        # 🔧 備用方法：使用傳統方式但改進過濾邏輯
                        all_messages = usb_device.get_recent_messages(1000)
                        if all_messages and len(all_messages) > baseline_count:
                            # 只取超出基準線的新消息
                            new_messages = all_messages[baseline_count:]
                            performance_stats['new_messages_found'] += len(new_messages)
                            self._log_info(f"📥 發現 {len(new_messages)} 條新訊息（傳統方式）")

                        # 更新基準線計數
                        if all_messages:
                            baseline_count = len(all_messages)

                    # 處理新訊息
                    if new_messages:
                        for message in new_messages:
                            total_checked_messages += 1
                            performance_stats['messages_processed'] += 1

                            # 解析並檢查訊息
                            check_result = await self._check_single_message(
                                message, expected_values, total_checked_messages
                            )

                            if check_result['success']:
                                # 找到匹配的訊息！
                                elapsed_time = time.time() - start_time
                                success_msg = (
                                    f"✅ 檢查成功! "
                                    f"用時: {elapsed_time:.3f}s, "
                                    f"檢查了 {total_checked_messages} 條新訊息"
                                )

                                # 顯示詳細結果
                                if check_result['details']:
                                    success_msg += f"\n匹配結果: {check_result['details']}"

                                # 顯示性能統計
                                success_msg += f"\n性能統計: {self._format_performance_stats(performance_stats, elapsed_time)}"

                                self._log_success(success_msg)
                                return True

                    # ==================== 智能輪詢間隔調整 ====================

                    cycle_duration = time.time() - cycle_start

                    # 根據處理時間動態調整輪詢間隔
                    if new_messages:
                        # 有新訊息時，加快輪詢頻率
                        polling_interval = max(0.005, polling_interval * 0.8)
                    else:
                        # 沒有新訊息時，逐漸降低輪詢頻率
                        polling_interval = min(max_polling_interval, polling_interval * 1.1)

                    # 確保不會過度輪詢
                    if cycle_duration < polling_interval:
                        await asyncio.sleep(polling_interval - cycle_duration)

                    # ==================== 進度報告 ====================

                    # 每1000個循環顯示進度報告
                    if performance_stats['polling_cycles'] % 1000 == 0:
                        elapsed = time.time() - start_time
                        remaining = timeout - elapsed
                        self._log_info(
                            f"📊 進度報告: "
                            f"已檢查 {total_checked_messages} 條新訊息, "
                            f"剩餘時間 {remaining:.1f}s, "
                            f"輪詢間隔 {polling_interval * 1000:.1f}ms"
                        )

                except Exception as e:
                    performance_stats['parsing_failures'] += 1
                    self._log_warning(f"輪詢循環中發生錯誤: {e}")
                    # 錯誤時稍微延長等待時間
                    await asyncio.sleep(0.02)

        except asyncio.CancelledError:
            self._log_warning("檢查被取消")
            raise

        # ==================== 超時處理 ====================

        elapsed_time = time.time() - start_time
        timeout_msg = f"⏰ 檢查超時 ({elapsed_time:.3f}s)"

        if expected_values:
            timeout_msg += f"\n未找到期望的訊息: {expected_values}"
        else:
            timeout_msg += f"\n在基準時間 {start_time} 之後未收到任何有效的 CAN 訊息"

        timeout_msg += f"\n檢查統計: 總共檢查了 {total_checked_messages} 條新訊息"
        timeout_msg += f"\n基準線: {baseline_count} 條歷史訊息被忽略"
        timeout_msg += f"\n性能統計: {self._format_performance_stats(performance_stats, elapsed_time)}"

        if total_checked_messages == 0:
            self._log_warning(timeout_msg)
            return False
        else:
            raise RuntimeError(timeout_msg)

    async def _prepare_expected_values(self, expected_payload, expected_can_id, expected_fields):
        """準備期望值字典"""
        expected_values = {}

        if expected_payload:
            expected_values['payload'] = self._normalize_payload(expected_payload)
        if expected_can_id:
            expected_values['can_id'] = self._normalize_can_id(expected_can_id)

        for field, value in expected_fields.items():
            if value:
                expected_values[field] = str(value).strip()

        if expected_values:
            self._log_info("🎯 期望值:")
            for field, value in expected_values.items():
                self._log_info(f"  {field}: {value}")
        else:
            self._log_info("🎯 未指定期望值，只要收到有效 CAN 訊息即可")

        return expected_values

    def _generate_message_id(self, message):
        """生成訊息的唯一ID"""
        # 使用訊息內容的hash作為唯一識別
        return hash(str(message))

    async def _filter_new_messages(self, current_messages, processed_message_ids, start_datetime):
        """過濾出新訊息（在開始時間之後且未處理過的）"""
        new_messages = []

        for message in current_messages:
            msg_id = self._generate_message_id(message)

            # 跳過已處理的訊息
            if msg_id in processed_message_ids:
                continue

            # 檢查訊息時間戳（如果可解析的話）
            try:
                parsed = self._parse_can_message(message)
                if parsed and 'timestamp' in parsed:
                    msg_time = datetime.strptime(parsed['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                    if msg_time > start_datetime:
                        new_messages.append(message)
                        continue
            except:
                pass

            # 如果無法解析時間戳，假設是新訊息（保守策略）
            new_messages.append(message)

        return new_messages

    async def _check_single_message(self, message, expected_values, message_count):
        """
        檢查單一訊息 - 完整版本

        Args:
            message: 原始訊息字符串
            expected_values: 期望值字典
            message_count: 訊息計數（用於調試）

        Returns:
            dict: {'success': bool, 'details': str}
        """
        try:
            # 1. 解析訊息
            parsed_message = self._parse_can_message(message)

            if not parsed_message:
                return {
                    'success': False,
                    'details': '無法解析訊息格式',
                    'debug_info': f"原始訊息: {message[:100]}..."
                }

            # 2. 如果沒有期望值，任何有效訊息都算通過
            if not expected_values:
                return {
                    'success': True,
                    'details': f"CAN ID: {parsed_message.get('can_id', 'N/A')}, Payload: {parsed_message.get('payload', 'N/A')}",
                    'debug_info': f"無期望值檢查，訊息解析成功"
                }

            # 3. 檢查所有期望字段
            field_results = {}
            overall_success = True
            missing_fields = []

            self._log_info(f"開始檢查訊息 #{message_count}，期望字段數: {len(expected_values)}")

            # 逐一檢查每個期望字段
            for expected_field, expected_value in expected_values.items():
                actual_value = parsed_message.get(expected_field)

                # 檢查字段是否存在
                if actual_value is None:
                    field_results[expected_field] = {
                        'status': 'missing',
                        'expected': expected_value,
                        'actual': None,
                        'match': False
                    }
                    missing_fields.append(expected_field)
                    overall_success = False
                    self._log_warning(f"字段 '{expected_field}' 在訊息中不存在")
                    continue

                # 執行字段比較
                try:
                    field_match = await self._compare_field_values(
                        expected_field, expected_value, actual_value
                    )

                    field_results[expected_field] = {
                        'status': 'checked',
                        'expected': expected_value,
                        'actual': actual_value,
                        'match': field_match
                    }

                    if field_match:
                        self._log_info(f"✓ {expected_field}: {actual_value} 匹配成功")
                    else:
                        self._log_error(f"✗ {expected_field}: 期望 '{expected_value}', 實際 '{actual_value}' 不匹配")
                        overall_success = False

                except Exception as field_error:
                    field_results[expected_field] = {
                        'status': 'error',
                        'expected': expected_value,
                        'actual': actual_value,
                        'match': False,
                        'error': str(field_error)
                    }
                    overall_success = False
                    self._log_error(f"✗ {expected_field}: 比較時發生錯誤 - {str(field_error)}")

            # 4. 生成詳細結果
            result_details = []

            # 成功的字段
            successful_fields = [
                f"{field}: {info['actual']} ✓"
                for field, info in field_results.items()
                if info['match']
            ]

            # 失敗的字段
            failed_fields = [
                f"{field}: 期望 {info['expected']}, 實際 {info['actual']} ✗"
                for field, info in field_results.items()
                if not info['match'] and info['status'] == 'checked'
            ]

            # 缺失的字段
            missing_field_details = [
                f"{field}: 字段不存在 ✗"
                for field in missing_fields
            ]

            # 錯誤的字段
            error_fields = [
                f"{field}: 比較錯誤 ({info.get('error', 'unknown')}) ✗"
                for field, info in field_results.items()
                if info['status'] == 'error'
            ]

            # 組合所有結果詳情
            result_details.extend(successful_fields)
            result_details.extend(failed_fields)
            result_details.extend(missing_field_details)
            result_details.extend(error_fields)

            # 5. 記錄檢查總結
            if overall_success:
                summary = f"訊息 #{message_count} 檢查成功，所有 {len(expected_values)} 個字段都匹配"
                self._log_success(summary)
            else:
                failed_count = len(failed_fields) + len(missing_fields) + len(error_fields)
                summary = f"訊息 #{message_count} 檢查失敗，{failed_count}/{len(expected_values)} 個字段不匹配"
                self._log_error(summary)

            # 6. 返回結果
            return {
                'success': overall_success,
                'details': ', '.join(result_details) if result_details else 'No details',
                'debug_info': {
                    'message_count': message_count,
                    'expected_fields_count': len(expected_values),
                    'successful_fields_count': len(successful_fields),
                    'failed_fields_count': len(failed_fields),
                    'missing_fields_count': len(missing_fields),
                    'error_fields_count': len(error_fields),
                    'field_results': field_results,
                    'parsed_message_keys': list(parsed_message.keys()),
                    'raw_message_preview': message[:200] + "..." if len(message) > 200 else message
                }
            }

        except Exception as e:
            error_msg = f'檢查訊息時發生嚴重錯誤: {str(e)}'
            self._log_error(error_msg)
            import traceback
            self._log_error(f"錯誤堆疊: {traceback.format_exc()}")

            return {
                'success': False,
                'details': error_msg,
                'debug_info': {
                    'exception_type': type(e).__name__,
                    'exception_message': str(e),
                    'message_count': message_count,
                    'raw_message_preview': message[:200] + "..." if len(message) > 200 else message
                }
            }

    async def _compare_field_values(self, field_name, expected_value, actual_value):
        """
        比較字段值 - 修改版，支援 payload 通配符

        Args:
            field_name: 字段名稱
                description: 要比較的字段名稱（如 'payload', 'can_id', 'header' 等）
            expected_value: 期望值
                description: 期望的字段值，payload 字段支援 XX 通配符
            actual_value: 實際值
                description: 實際接收到的字段值
        """
        try:
            if field_name == 'payload':
                # 使用新的通配符比較方法
                return self._compare_payload_with_wildcards(expected_value, actual_value)
            elif field_name in ['can_id', 'header']:
                # 十六進制字段比較
                normalized_expected = self._normalize_can_id(
                    expected_value) if field_name == 'can_id' else expected_value.upper()
                return actual_value.upper() == normalized_expected.upper()
            else:
                # 一般字段比較
                return str(actual_value).strip() == str(expected_value).strip()
        except:
            return str(actual_value) == str(expected_value)

    async def _cleanup_memory(self, processed_message_ids):
        """記憶體清理"""
        # 限制已處理訊息ID的數量，避免記憶體無限增長
        max_processed_ids = 10000
        if len(processed_message_ids) > max_processed_ids:
            # 保留最近的一半ID
            ids_list = list(processed_message_ids)
            processed_message_ids.clear()
            processed_message_ids.update(ids_list[-max_processed_ids // 2:])

    def _format_performance_stats(self, stats, elapsed_time):
        """格式化性能統計"""
        return (
            f"輪詢週期: {stats['polling_cycles']}, "
            f"處理訊息: {stats['messages_processed']}, "
            f"新訊息: {stats['new_messages_found']}, "
            f"平均處理速度: {stats['messages_processed'] / elapsed_time:.1f} msg/s"
        )

    def _compare_payload_with_wildcards(self, expected_payload, actual_payload):
        """
        比較 payload，支援 XX 作為 don't care

        Args:
            expected_payload: 期望的 payload
                description: 期望的 payload 字符串，可包含 XX 通配符表示不關心該位置
            actual_payload: 實際收到的 payload
                description: 從設備實際接收到的 payload 字符串

        Returns:
            bool: 是否匹配

        Examples:
            expected: "FF XX AA 55", actual: "FF 12 AA 55" -> True
            expected: "FF XX AA 55", actual: "FF 12 AA 66" -> False
        """
        if not expected_payload or not actual_payload:
            return expected_payload == actual_payload

        # 將兩個 payload 都分割成 bytes
        expected_bytes = expected_payload.split()
        actual_bytes = actual_payload.split()

        # 長度檢查
        if len(expected_bytes) != len(actual_bytes):
            self._log_warning(f"Payload 長度不匹配: 期望 {len(expected_bytes)} bytes, 實際 {len(actual_bytes)} bytes")
            return False

        # 逐個 byte 比較
        mismatched_positions = []
        matched_positions = []
        ignored_positions = []

        for i, (expected_byte, actual_byte) in enumerate(zip(expected_bytes, actual_bytes)):
            if expected_byte.upper() == 'XX':
                # Don't care，跳過這個 byte
                ignored_positions.append(f"位置 {i}: {actual_byte} (ignored)")
                continue
            elif expected_byte.upper() != actual_byte.upper():
                # 不匹配
                mismatched_positions.append(f"位置 {i}: 期望 {expected_byte}, 實際 {actual_byte}")
            else:
                # 匹配
                matched_positions.append(f"位置 {i}: {actual_byte}")

        # 🔧 詳細的日誌記錄
        if mismatched_positions:
            mismatch_details = '; '.join(mismatched_positions)
            self._log_error(f"Payload 不匹配: {mismatch_details}")

            # 顯示完整的比較結果
            if matched_positions:
                match_details = '; '.join(matched_positions)
                self._log_info(f"匹配的位置: {match_details}")
            if ignored_positions:
                ignore_details = '; '.join(ignored_positions)
                self._log_info(f"忽略的位置: {ignore_details}")

            return False

        # 🔧 成功時的詳細記錄
        all_details = []
        if matched_positions:
            all_details.extend([f"{pos} ✓" for pos in matched_positions])
        if ignored_positions:
            all_details.extend([f"{pos}" for pos in ignored_positions])

        success_msg = f"Payload 匹配成功: {'; '.join(all_details)}"
        self._log_success(success_msg)
        return True

    def _convert_wildcard_format(self, payload_str, from_format='auto', to_format='XX'):
        """
        轉換不同的通配符格式

        Args:
            payload_str: 原始 payload 字符串
                description: 包含通配符的原始 payload 字符串
            from_format: 原始格式
                options: auto|XX|??|--
                default: auto
                description: 原始通配符格式，auto 表示自動檢測
            to_format: 目標格式
                options: XX|??|--
                default: XX
                description: 要轉換到的目標通配符格式

        Returns:
            轉換後的 payload 字符串
        """
        if not payload_str:
            return payload_str

        # 支援的通配符格式
        wildcard_patterns = ['XX', '??', '--', '..']

        if from_format == 'auto':
            # 自動檢測
            for pattern in wildcard_patterns:
                if pattern in payload_str.upper():
                    from_format = pattern
                    break
            else:
                return payload_str  # 沒有通配符

        # 轉換格式
        if from_format != to_format:
            payload_str = payload_str.replace(from_format, to_format)

        return payload_str

    # endregion