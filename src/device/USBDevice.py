# src/device/USBDevice.py - 自動接收版本

import usb.core
import usb.util
import asyncio
import threading
import time
from queue import Queue, Empty
from collections import deque
from src.device import DeviceBase
import logging
import src.CanFrame as CanFrame
from datetime import datetime
from typing import Optional, List


class USBDevice(DeviceBase):
    """自動接收版本的 USB 設備 - 連接後立即開始背景接收"""

    def __init__(self):
        super().__init__()
        self.device = None
        self.ep_out = None
        self.ep_in = None
        self.interface = None
        self._logger = logging.getLogger(__name__)
        self.vendor_id = 0x5458
        self.product_id = 0x1222

        # 自動接收機制
        self._auto_receive_thread = None
        self._stop_receive_flag = threading.Event()
        self._message_cache = deque(maxlen=1000)  # 緩存最近1000條訊息
        self._cache_lock = threading.Lock()

        # 日誌記錄（可選）
        self._log_file = None
        self._enable_logging = False
        self._log_dir = "logs"

        # 錯誤控制
        self._last_error_log_time = 0
        self._error_log_interval = 30
        self._consecutive_timeouts = 0

        # 統計資訊
        self._stats = {
            'total_reads': 0,
            'successful_reads': 0,
            'timeout_errors': 0,
            'cache_size': 0,
            'start_time': None
        }

    async def connect(self, port: str = None) -> bool:
        """連接 USB 設備並自動開始接收數據"""
        try:
            # 尋找並連接設備
            self.device = usb.core.find(
                idVendor=self.vendor_id,
                idProduct=self.product_id
            )

            if self.device is None:
                self._logger.error(f'設備未找到 (VID=0x{self.vendor_id:04X}, PID=0x{self.product_id:04X})')
                return False

            # 設置配置
            self.device.set_configuration()
            cfg = self.device.get_active_configuration()
            self.interface = cfg[(1, 0)]

            # 找到端點
            self.ep_out = usb.util.find_descriptor(
                self.interface,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            self.ep_in = usb.util.find_descriptor(
                self.interface,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )

            if not all([self.ep_out, self.ep_in]):
                self._logger.error('無法找到必要的端點')
                return False

            # 清空緩衝區和重置統計
            self._clear_input_buffer()
            self._reset_stats()
            self._connected = True

            # 🚀 關鍵：立即開始自動接收
            self._start_auto_receive()

            self._logger.info('USB 設備連接成功，已自動開始數據接收')
            return True

        except Exception as e:
            self._logger.error(f'連接失敗: {str(e)}')
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """斷開連接並停止自動接收"""
        try:
            # 停止自動接收
            self._stop_auto_receive()

            # 關閉日誌檔案
            self._close_log_file()

            if self.device:
                usb.util.dispose_resources(self.device)

            self.device = None
            self.ep_out = None
            self.ep_in = None
            self.interface = None
            self._connected = False

            # 清空緩存
            with self._cache_lock:
                self._message_cache.clear()

            self._logger.info('USB 設備已斷開連接')

        except Exception as e:
            self._logger.error(f'斷開連接時發生錯誤: {str(e)}')

    def send_command(self, command: bytes, get: bool = False) -> bool:
        """發送命令到 USB 設備"""
        if not self._connected:
            raise ConnectionError("設備未連接")

        try:
            bytes_written = self.ep_out.write(command)
            self._logger.debug(f'成功發送 {bytes_written} 字節: {command.hex(" ").upper()}')
            return True

        except Exception as e:
            self._logger.error(f'發送命令失敗: {str(e)}')
            return False

    def receive_data(self) -> bytes:
        """從緩存中獲取最新數據（立即返回）"""
        if not self._connected:
            return b""

        try:
            with self._cache_lock:
                if self._message_cache:
                    # 返回最新的數據
                    return self._message_cache[-1]
                return b""
        except Exception as e:
            self._logger.debug(f'從緩存獲取數據失敗: {str(e)}')
            return b""

    def get_recent_messages(self, count: int = 10) -> List[bytes]:
        """獲取最近的訊息（用於 check_payload）"""
        try:
            with self._cache_lock:
                if count >= len(self._message_cache):
                    return list(self._message_cache)
                else:
                    return list(self._message_cache)[-count:]
        except Exception as e:
            self._logger.debug(f'獲取最近訊息失敗: {str(e)}')
            return []

    def find_message_by_criteria(self, criteria: dict, timeout: float = 5.0) -> Optional[bytes]:
        """
        根據條件查找訊息（優化版 check_payload）

        Args:
            criteria: 查找條件，例如 {'can_id': '0x207', 'payload': 'FF00AA55'}
            timeout: 超時時間（秒）

        Returns:
            找到的訊息或 None
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 檢查現有緩存
            with self._cache_lock:
                for message in reversed(self._message_cache):  # 從最新開始查找
                    if self._message_matches_criteria(message, criteria):
                        return message

            # 短暫等待新數據
            time.sleep(0.01)  # 10ms

        return None

    def _message_matches_criteria(self, message: bytes, criteria: dict) -> bool:
        """檢查訊息是否符合條件"""
        try:
            # 這裡需要根據您的 CanFrame.Parser 實現來解析
            # 假設解析後返回字典格式
            parsed = self._parse_message_for_matching(message)
            if not parsed:
                return False

            for key, expected_value in criteria.items():
                actual_value = parsed.get(key)
                if actual_value != expected_value:
                    return False

            return True
        except Exception:
            return False

    def _parse_message_for_matching(self, message: bytes) -> Optional[dict]:
        """解析訊息用於匹配（簡化版本）"""
        try:
            # 這裡應該根據您的實際訊息格式來實現
            # 暫時返回基本結構
            message_str = str(message)

            # 基本的 CAN ID 和 Payload 提取邏輯
            parsed = {}

            # 提取 CAN ID
            if 'CAN ID:' in message_str:
                start = message_str.find('CAN ID:') + 8
                end = message_str.find('\n', start)
                if end == -1:
                    end = start + 10
                parsed['can_id'] = message_str[start:end].strip()

            # 提取 Payload
            if 'Payload:' in message_str:
                start = message_str.find('Payload:') + 8
                end = message_str.find('\n', start)
                if end == -1:
                    end = start + 50
                parsed['payload'] = message_str[start:end].strip()

            return parsed if parsed else None

        except Exception:
            return None

    def _start_auto_receive(self):
        """啟動自動接收線程"""
        if self._auto_receive_thread and self._auto_receive_thread.is_alive():
            return

        self._stop_receive_flag.clear()
        self._auto_receive_thread = threading.Thread(
            target=self._auto_receive_worker,
            name="USB_AutoReceiver",
            daemon=True
        )
        self._auto_receive_thread.start()
        self._stats['start_time'] = time.time()
        self._logger.info("自動接收線程已啟動")

    def _stop_auto_receive(self):
        """停止自動接收線程"""
        if self._auto_receive_thread and self._auto_receive_thread.is_alive():
            self._stop_receive_flag.set()
            self._auto_receive_thread.join(timeout=2.0)
            self._logger.info("自動接收線程已停止")

    def _auto_receive_worker(self):
        """自動接收工作線程"""
        self._logger.debug("自動接收工作線程開始運行")

        while not self._stop_receive_flag.is_set() and self._connected:
            try:
                self._stats['total_reads'] += 1

                # 嘗試讀取數據
                data = self.ep_in.read(25, timeout=100)  # 100ms 超時

                if data:
                    data_bytes = bytes(data)

                    # 解析數據
                    try:
                        parsed_data = CanFrame.Parser.parse(data_bytes)
                        if parsed_data:
                            # 加入緩存
                            with self._cache_lock:
                                self._message_cache.append(parsed_data)
                                self._stats['cache_size'] = len(self._message_cache)

                            # 寫入日誌（如果啟用）
                            if self._enable_logging:
                                self._write_to_log(parsed_data)

                            self._stats['successful_reads'] += 1
                            self._consecutive_timeouts = 0

                    except Exception as e:
                        self._logger.debug(f'數據解析失敗: {e}')

            except usb.core.USBError as e:
                if e.errno == 110:  # 超時（正常）
                    self._stats['timeout_errors'] += 1
                    self._consecutive_timeouts += 1
                    self._handle_timeout_logging()
                elif e.errno == 19:  # 設備斷開
                    self._logger.warning("設備連接丟失，停止自動接收")
                    self._connected = False
                    break
                else:
                    self._handle_other_error(e)

            except Exception as e:
                self._handle_other_error(e)
                time.sleep(0.1)

        self._logger.debug("自動接收工作線程結束")

    def _handle_timeout_logging(self):
        """處理超時日誌（智能控制）"""
        if self._consecutive_timeouts == 100:
            self._logger.info("自動接收: 連續100次超時（正常現象，設備無數據）")
        elif self._consecutive_timeouts % 1000 == 0 and self._consecutive_timeouts > 0:
            success_rate = (self._stats['successful_reads'] / max(self._stats['total_reads'], 1)) * 100
            self._logger.debug(f"自動接收狀態: 成功率 {success_rate:.1f}%, 緩存 {self._stats['cache_size']} 條")

    def _handle_other_error(self, error):
        """處理其他錯誤"""
        current_time = time.time()
        if current_time - self._last_error_log_time > self._error_log_interval:
            self._logger.warning(f'自動接收錯誤: {str(error)}')
            self._last_error_log_time = current_time

    # ==================== 日誌功能（可選） ====================

    def enable_logging(self, log_file: Optional[str] = None):
        """啟用數據日誌記錄"""
        if not log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"{self._log_dir}/USBDevice_Auto_{timestamp}.txt"

        try:
            import os
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            self._log_file = open(log_file, 'w', encoding='utf-8')
            self._enable_logging = True
            self._log_file.write(f"自動接收日誌開始: {datetime.now()}\n")
            self._log_file.write("-" * 50 + "\n")
            self._log_file.flush()
            self._logger.info(f"數據日誌已啟用: {log_file}")
        except Exception as e:
            self._logger.error(f"啟用日誌失敗: {e}")

    def disable_logging(self):
        """禁用數據日誌記錄"""
        self._enable_logging = False
        self._close_log_file()
        self._logger.info("數據日誌已禁用")

    def _write_to_log(self, data):
        """寫入日誌"""
        if self._log_file and self._enable_logging:
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                self._log_file.write(f"[{timestamp}] {data}\n")
                self._log_file.flush()
            except Exception as e:
                self._logger.debug(f'寫入日誌失敗: {e}')

    def _close_log_file(self):
        """關閉日誌檔案"""
        if self._log_file:
            try:
                self._log_file.write(f"\n自動接收日誌結束: {datetime.now()}\n")
                self._log_file.close()
                self._log_file = None
            except Exception:
                pass

    # ==================== 統計和狀態 ====================

    def get_statistics(self) -> dict:
        """獲取統計資訊"""
        with self._cache_lock:
            current_cache_size = len(self._message_cache)

        runtime = time.time() - self._stats['start_time'] if self._stats['start_time'] else 0
        total_reads = max(self._stats['total_reads'], 1)

        return {
            'runtime_seconds': runtime,
            'total_reads': self._stats['total_reads'],
            'successful_reads': self._stats['successful_reads'],
            'timeout_errors': self._stats['timeout_errors'],
            'success_rate': (self._stats['successful_reads'] / total_reads) * 100,
            'cache_size': current_cache_size,
            'cache_max_size': self._message_cache.maxlen,
            'reads_per_second': self._stats['total_reads'] / max(runtime, 1),
            'connected': self.is_connected,
            'logging_enabled': self._enable_logging
        }

    def _clear_input_buffer(self):
        """清空輸入緩衝區"""
        if not self.ep_in:
            return
        try:
            while True:
                try:
                    self.ep_in.read(25, timeout=10)
                except usb.core.USBError:
                    break
        except Exception:
            pass

    def _reset_stats(self):
        """重置統計資訊"""
        self._stats = {
            'total_reads': 0,
            'successful_reads': 0,
            'timeout_errors': 0,
            'cache_size': 0,
            'start_time': None
        }
        self._consecutive_timeouts = 0

    def cleanup(self) -> bool:
        """清理資源"""
        try:
            asyncio.get_event_loop().run_until_complete(self.disconnect())
            return True
        except Exception as e:
            self._logger.error(f'清理過程中發生錯誤: {str(e)}')
            return False

    @property
    def status(self) -> str:
        """獲取設備狀態"""
        if not self._connected:
            return "disconnected"
        try:
            if self.device:
                cfg = self.device.get_active_configuration()
                return "connected_auto_receiving"
        except:
            self._connected = False
        return "disconnected"

    @property
    def is_connected(self) -> bool:
        """檢查設備是否已連接"""
        if not self.device or not self._connected:
            return False
        try:
            device_check = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
            if device_check is None:
                self._connected = False
                self.device = None
                return False
            return True
        except Exception:
            self._connected = False
            self.device = None
            return False