# src/device/USBDevice.py - 修正時序問題版本

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
from typing import Optional, List, NamedTuple


class TimestampedMessage(NamedTuple):
    """帶時間戳的消息"""
    message_str: str
    receive_time: float  # 使用 time.time() 的時間戳
    can_packet: object  # 原始 CanPacket 對象


class USBDevice(DeviceBase):
    """修正時序問題的 USB 設備 - 確保只檢查指定時間後的消息"""

    def __init__(self):
        super().__init__()
        self.device = None
        self.ep_out = None
        self.ep_in = None
        self.interface = None
        self._logger = logging.getLogger(__name__)
        self.vendor_id = 0x5458
        self.product_id = 0x1222

        # 🔧 修正：使用帶時間戳的消息緩存
        self._auto_receive_thread = None
        self._stop_receive_flag = threading.Event()
        self._timestamped_messages = deque(maxlen=1000)  # 存儲 TimestampedMessage
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
            self.enable_logging()
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
            self.disable_logging()

            if self.device:
                usb.util.dispose_resources(self.device)

            self.device = None
            self.ep_out = None
            self.ep_in = None
            self.interface = None
            self._connected = False

            # 清空緩存
            with self._cache_lock:
                self._timestamped_messages.clear()

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
                if self._timestamped_messages:
                    # 返回最新的字符串數據
                    return self._timestamped_messages[-1].message_str.encode('utf-8')
                return b""
        except Exception as e:
            self._logger.debug(f'從緩存獲取數據失敗: {str(e)}')
            return b""

    def get_recent_messages(self, count: int = 10) -> List[str]:
        """
        🔧 修正：獲取最近的訊息（用於 check_payload）
        這個方法會被 CommonLibrary 調用，返回字符串格式
        """
        try:
            with self._cache_lock:
                if count >= len(self._timestamped_messages):
                    return [msg.message_str for msg in self._timestamped_messages]
                else:
                    return [msg.message_str for msg in list(self._timestamped_messages)[-count:]]
        except Exception as e:
            self._logger.debug(f'獲取最近訊息失敗: {str(e)}')
            return []

    def get_messages_after_time(self, start_time: float, count: int = 1000) -> List[str]:
        """
        🚀 新增：獲取指定時間之後的消息（這是關鍵方法）

        Args:
            start_time: 開始時間（time.time() 格式）
            count: 最大數量

        Returns:
            List[str]: 在指定時間之後接收到的消息列表
        """
        try:
            with self._cache_lock:
                # 篩選出在指定時間之後接收到的消息
                filtered_messages = [
                    msg.message_str
                    for msg in self._timestamped_messages
                    if msg.receive_time > start_time
                ]

                # 限制數量
                if count < len(filtered_messages):
                    filtered_messages = filtered_messages[-count:]

                # self._logger.debug(
                #     f"獲取 {start_time} 之後的消息: 找到 {len(filtered_messages)} 條新消息"
                # )

                return filtered_messages

        except Exception as e:
            self._logger.debug(f'獲取指定時間後消息失敗: {str(e)}')
            return []

    def get_baseline_message_count(self) -> int:
        """
        🚀 新增：獲取當前消息數量（用於建立基準線）
        """
        try:
            with self._cache_lock:
                return len(self._timestamped_messages)
        except Exception:
            return 0

    def clear_message_cache(self):
        """
        🚀 新增：清空消息緩存（可選功能）
        """
        try:
            with self._cache_lock:
                self._timestamped_messages.clear()
                self._logger.debug("消息緩存已清空")
        except Exception as e:
            self._logger.debug(f'清空緩存失敗: {str(e)}')

    def get_recent_can_packets(self, count: int = 10) -> List[object]:
        """獲取最近的 CanPacket 對象（如果需要原始對象）"""
        try:
            with self._cache_lock:
                if count >= len(self._timestamped_messages):
                    return [msg.can_packet for msg in self._timestamped_messages]
                else:
                    return [msg.can_packet for msg in list(self._timestamped_messages)[-count:]]
        except Exception as e:
            self._logger.debug(f'獲取最近 CanPacket 失敗: {str(e)}')
            return []

    def find_message_by_criteria(self, criteria: dict, timeout: float = 5.0) -> Optional[str]:
        """根據條件查找訊息"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 檢查現有緩存
            with self._cache_lock:
                for timestamped_msg in reversed(self._timestamped_messages):
                    if self._message_matches_criteria(timestamped_msg.message_str, criteria):
                        return timestamped_msg.message_str

            # 短暫等待新數據
            time.sleep(0.01)  # 10ms

        return None

    def _message_matches_criteria(self, message: str, criteria: dict) -> bool:
        """檢查訊息是否符合條件"""
        try:
            # 解析字符串消息
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

    def _parse_message_for_matching(self, message: str) -> Optional[dict]:
        """解析訊息用於匹配（簡化版本）"""
        try:
            parsed = {}

            # 提取 CAN ID
            if 'CAN ID:' in message:
                start = message.find('CAN ID:') + 8
                end = message.find('\n', start)
                if end == -1:
                    end = start + 10
                parsed['can_id'] = message[start:end].strip()

            # 提取 Payload
            if 'Payload:' in message:
                start = message.find('Payload:') + 8
                end = message.find('\n', start)
                if end == -1:
                    end = start + 50
                parsed['payload'] = message[start:end].strip()

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
        """🔧 修正：自動接收工作線程 - 記錄準確的接收時間"""
        self._logger.debug("自動接收工作線程開始運行")

        while not self._stop_receive_flag.is_set() and self._connected:
            try:
                self._stats['total_reads'] += 1

                # 嘗試讀取數據
                data = self.ep_in.read(25, timeout=100)  # 100ms 超時

                if data:
                    data_bytes = bytes(data)
                    # 🔧 關鍵：記錄數據接收的準確時間
                    receive_time = time.time()

                    # 解析數據
                    try:
                        parsed_data = CanFrame.Parser.parse(data_bytes)
                        if parsed_data:
                            # 轉換為字符串格式，但使用準確的接收時間
                            message_str = self._convert_can_packet_to_string(parsed_data, receive_time)

                            # 🔧 關鍵：創建帶時間戳的消息對象
                            timestamped_msg = TimestampedMessage(
                                message_str=message_str,
                                receive_time=receive_time,
                                can_packet=parsed_data
                            )

                            # 加入緩存
                            with self._cache_lock:
                                self._timestamped_messages.append(timestamped_msg)
                                self._stats['cache_size'] = len(self._timestamped_messages)

                            # 寫入日誌（如果啟用）
                            if self._enable_logging:
                                self._write_to_log(message_str)

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

    def _convert_can_packet_to_string(self, can_packet, receive_time: float) -> str:
        """
        🔧 修正：將 CanPacket 對象轉換為字符串格式，使用準確的接收時間

        Args:
            can_packet: CanPacket 對象
            receive_time: 準確的接收時間（time.time() 格式）
        """
        try:
            # 檢查 can_packet 是否已經是字符串
            if isinstance(can_packet, str):
                return can_packet

            # 如果 can_packet 有 __str__ 方法，直接使用
            if hasattr(can_packet, '__str__'):
                # 但要確保時間戳是準確的接收時間
                msg_str = str(can_packet)
                # 如果消息中包含時間戳，替換為準確的接收時間
                accurate_timestamp = datetime.fromtimestamp(receive_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                if '[' in msg_str and ']' in msg_str:
                    # 替換現有的時間戳
                    import re
                    msg_str = re.sub(r'\[[^\]]+\]', f'[{accurate_timestamp}]', msg_str, count=1)
                else:
                    # 添加時間戳前綴
                    msg_str = f'[{accurate_timestamp}] {msg_str}'
                return msg_str

            # 如果是字節類型，嘗試解碼
            if isinstance(can_packet, bytes):
                return can_packet.decode('utf-8', errors='ignore')

            # 如果是 CanPacket 對象，嘗試提取屬性
            if hasattr(can_packet, '__dict__'):
                # 🔧 使用準確的接收時間而不是當前時間
                accurate_timestamp = datetime.fromtimestamp(receive_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

                # 嘗試獲取常見的 CAN 相關屬性
                message_parts = [f"[{accurate_timestamp}] CAN Message:"]

                # 常見的 CanPacket 屬性
                attributes_to_check = [
                    'header', 'systick', 'node', 'can_type',
                    'can_id', 'dlc', 'data_length', 'payload', 'crc32'
                ]

                for attr in attributes_to_check:
                    if hasattr(can_packet, attr):
                        value = getattr(can_packet, attr)
                        if value is not None:
                            # 特殊格式化處理
                            if attr == 'can_id':
                                if isinstance(value, int):
                                    formatted_value = f"0x{value:X}"
                                else:
                                    formatted_value = str(value)
                            elif attr in ['header', 'crc32']:
                                if isinstance(value, int):
                                    formatted_value = f"0x{value:X}"
                                else:
                                    formatted_value = str(value)
                            elif attr == 'payload':
                                if isinstance(value, (bytes, bytearray)):
                                    formatted_value = ' '.join(f"{b:02X}" for b in value)
                                elif isinstance(value, list):
                                    formatted_value = ' '.join(f"{b:02X}" for b in value)
                                else:
                                    formatted_value = str(value)
                            else:
                                formatted_value = str(value)

                            message_parts.append(f"{attr.replace('_', ' ').title()}: {formatted_value}")

                return '\n'.join(message_parts)

            # 最後的備案：直接轉換為字符串，但添加準確時間戳
            accurate_timestamp = datetime.fromtimestamp(receive_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            return f'[{accurate_timestamp}] {str(can_packet)}'

        except Exception as e:
            # 如果轉換失敗，返回基本信息但使用準確時間戳
            accurate_timestamp = datetime.fromtimestamp(receive_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            self._logger.debug(f'CanPacket 轉換失敗: {e}')
            return f"[{accurate_timestamp}] CAN Message: <conversion_error: {type(can_packet).__name__}>"

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
                self._log_file.write(f"{data}\n")
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
            current_cache_size = len(self._timestamped_messages)

        runtime = time.time() - self._stats['start_time'] if self._stats['start_time'] else 0
        total_reads = max(self._stats['total_reads'], 1)

        return {
            'runtime_seconds': runtime,
            'total_reads': self._stats['total_reads'],
            'successful_reads': self._stats['successful_reads'],
            'timeout_errors': self._stats['timeout_errors'],
            'success_rate': (self._stats['successful_reads'] / total_reads) * 100,
            'cache_size': current_cache_size,
            'cache_max_size': self._timestamped_messages.maxlen,
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