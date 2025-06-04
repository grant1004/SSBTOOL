import sys
import os

# 導入新的架構組件
from src.interfaces.device_interface import DeviceType, DeviceStatus

# 獲取當前檔案所在目錄的路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import time
import asyncio
from robot.api.deco import library, keyword
from src.utils import CANPacketGenerator
from .BaseLibrary import BaseRobotLibrary
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

    @keyword
    def send_can_message(self, can_id: int, payload: str, node: int = 1, can_type: int = 0):
        """
        發送 CAN 訊息

        Args:
            can_id: CAN 訊息識別碼 (支援十進制或十六進制格式，如 '0x123' 或 '291')
            payload: 訊息負載數據
            node: 目標節點編號 (1=公共, 0=私有)
            can_type: CAN 訊息類型 (0=標準, 1=擴展)

        Returns:
            bool: 發送是否成功

        Examples:
            | Send CAN Message | 0x123 | FF00 | 1 | 0 |
            | Send CAN Message | 291   | AA55 |   |   |
        """
        try:
            payload = payload.replace("\"", "").replace("'", "").strip()
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
    def check_payload(self, expected_payload=None, timeout=5):
        """
        檢查接收到的 payload 數據

        Args:
            expected_payload: 期望的 payload 數據 (可選)
            timeout: 超時時間（秒）

        Examples:
            | Check Payload |
            | Check Payload | FF00AA55 |
            | Check Payload | ${expected_data} | 10 |
        """
        try:
            self._validate_device_model()

            # 檢查 USB 設備是否可用
            if not self.device_model.is_device_available(DeviceType.USB):
                raise RuntimeError("USB 設備不可用，無法檢查 payload")

            usb_device = self.device_model._device_instances.get(DeviceType.USB)
            if not usb_device:
                raise RuntimeError("無法獲取 USB 設備實例")

            # 檢查設備是否支持數據接收
            if not hasattr(usb_device, 'get_recent_messages'):
                self._log_warning("USB 設備不支持消息歷史功能，跳過 payload 檢查")
                return True

            self._log_info(f"開始檢查 payload，超時時間: {timeout} 秒")

            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # 獲取最近的消息
                    recent_messages = usb_device.get_recent_messages(10)

                    if recent_messages:
                        latest_message = recent_messages[-1]
                        self._log_info(f"收到最新消息: {latest_message}")

                        if expected_payload:
                            # 如果指定了期望的 payload，進行比較
                            if expected_payload.upper() in str(latest_message).upper():
                                self._log_success(f"Payload 檢查通過: {latest_message}")
                                return True
                        else:
                            # 如果沒有指定期望值，只要有消息就算通過
                            self._log_success(f"收到 payload: {latest_message}")
                            return True

                except Exception as e:
                    self._log_warning(f"檢查 payload 時發生錯誤: {e}")

                time.sleep(0.1)  # 短暫等待後重試

            # 超時
            if expected_payload:
                raise RuntimeError(f"在 {timeout} 秒內未收到期望的 payload: {expected_payload}")
            else:
                self._log_warning(f"在 {timeout} 秒內未收到任何 payload")
                return False

        except Exception as e:
            error_msg = f"Payload 檢查失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    @keyword
    def start_listening(self):
        """
        開始監聽設備訊息

        啟動 USB 設備的消息監聽功能，開始記錄接收到的數據

        Examples:
            | Start Listening |
        """
        try:
            self._validate_device_model()

            # 檢查 USB 設備是否可用
            if not self.device_model.is_device_available(DeviceType.USB):
                device_status = self.device_model.get_device_status(DeviceType.USB)
                raise RuntimeError(f"USB 設備不可用，當前狀態: {device_status.value}")

            usb_device = self.device_model._device_instances.get(DeviceType.USB)
            if not usb_device:
                raise RuntimeError("無法獲取 USB 設備實例")

            # 檢查設備是否支持監聽功能
            if not hasattr(usb_device, 'start_listening'):
                raise RuntimeError("USB 設備不支持監聽功能")

            # 檢查是否已經在監聽
            if hasattr(usb_device, 'is_listening') and usb_device.is_listening():
                self._log_warning("USB 設備已在監聽中")
                return True

            # 開始監聽
            result = usb_device.start_listening()

            if result:
                self._log_success("USB 設備監聽已啟動")
            else:
                raise RuntimeError("監聽啟動失敗")

            return result

        except Exception as e:
            error_msg = f"監聽啟動失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    @keyword
    def stop_listening(self):
        """
        停止監聽設備訊息

        停止 USB 設備的消息監聽功能

        Examples:
            | Stop Listening |
        """
        try:
            self._validate_device_model()

            usb_device = self.device_model._device_instances.get(DeviceType.USB)
            if not usb_device:
                self._log_warning("無法獲取 USB 設備實例，可能已經斷開連接")
                return True

            # 檢查設備是否支持停止監聽功能
            if not hasattr(usb_device, 'stop_listening'):
                self._log_warning("USB 設備不支持停止監聽功能")
                return True

            # 檢查是否正在監聽
            if hasattr(usb_device, 'is_listening') and not usb_device.is_listening():
                self._log_info("USB 設備已停止監聽")
                return True

            # 停止監聽
            result = usb_device.stop_listening()
            self._log_success("USB 設備監聽已停止")

            return result

        except Exception as e:
            error_msg = f"監聽停止失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    @keyword
    def get_device_status(self, device_type_str: str):
        """
        獲取設備狀態

        Args:
            device_type_str: 設備類型字符串 ("USB", "POWER", "LOADER")

        Returns:
            str: 設備狀態字符串

        Examples:
            | ${status} | Get Device Status | USB |
            | Should Be Equal | ${status} | CONNECTED |
        """
        try:
            self._validate_device_model()

            # 轉換字符串到 DeviceType 枚舉
            device_type_map = {
                "USB": DeviceType.USB,
                "POWER": DeviceType.POWER,
                "LOADER": DeviceType.LOADER
            }

            device_type = device_type_map.get(device_type_str.upper())
            if not device_type:
                raise ValueError(f"不支持的設備類型: {device_type_str}")

            status = self.device_model.get_device_status(device_type)
            self._log_info(f"設備 {device_type_str} 狀態: {status.value}")

            return status.value

        except Exception as e:
            error_msg = f"獲取設備狀態失敗: {str(e)}"
            self._log_error(error_msg)
            return "ERROR"

    @keyword
    def wait_for_device_ready(self, device_type_str: str, timeout: int = 30):
        """
        等待設備準備就緒

        Args:
            device_type_str: 設備類型字符串
            timeout: 超時時間（秒）

        Examples:
            | Wait For Device Ready | USB |
            | Wait For Device Ready | POWER | 60 |
        """
        try:
            self._validate_device_model()

            device_type_map = {
                "USB": DeviceType.USB,
                "POWER": DeviceType.POWER,
                "LOADER": DeviceType.LOADER
            }

            device_type = device_type_map.get(device_type_str.upper())
            if not device_type:
                raise ValueError(f"不支持的設備類型: {device_type_str}")

            self._log_info(f"等待設備 {device_type_str} 準備就緒，超時時間: {timeout} 秒")

            start_time = time.time()
            check_interval = 0.5  # 每 0.5 秒檢查一次

            while time.time() - start_time < timeout:
                if self.device_model.is_device_available(device_type):
                    elapsed_time = time.time() - start_time
                    self._log_success(f"設備 {device_type_str} 已準備就緒，耗時: {elapsed_time:.1f} 秒")
                    return True

                # 顯示進度
                elapsed = time.time() - start_time
                if int(elapsed) % 5 == 0 and elapsed > 0:  # 每5秒顯示一次進度
                    current_status = self.device_model.get_device_status(device_type)
                    self._log_info(f"等待中... 當前狀態: {current_status.value} ({elapsed:.0f}/{timeout}s)")

                time.sleep(check_interval)

            # 超時
            current_status = self.device_model.get_device_status(device_type)
            raise RuntimeError(
                f"等待設備 {device_type_str} 準備就緒超時 ({timeout} 秒)，當前狀態: {current_status.value}")

        except Exception as e:
            error_msg = f"等待設備準備就緒失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    @keyword
    def verify_device_connection(self, device_type_str: str):
        """
        驗證設備連接狀態

        驗證指定設備是否正確連接並可用

        Args:
            device_type_str: 設備類型字符串

        Examples:
            | Verify Device Connection | USB |
        """
        try:
            status = self.get_device_status(device_type_str)

            if status == "CONNECTED":
                self._log_success(f"設備 {device_type_str} 連接驗證通過")
                return True
            else:
                raise RuntimeError(f"設備 {device_type_str} 連接驗證失敗，當前狀態: {status}")

        except Exception as e:
            error_msg = f"設備連接驗證失敗: {str(e)}"
            self._log_error(error_msg)
            raise RuntimeError(error_msg)

    # ==================== 輔助方法 ====================

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