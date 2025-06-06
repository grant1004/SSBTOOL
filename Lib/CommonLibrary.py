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

    @keyword("Send CAN Message")
    def send_can_message(self, can_id: Union[str, int], payload: str, node: int = 1, can_type: int = 0):
        """
        發送 CAN 訊息

        Args:
            can_id: CAN 訊息識別碼 (支援十進制或十六進制格式，如 '0x123' 或 '291')
            payload: 訊息數據
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
        高精度檢查接收到的 CAN 消息數據（絕對，不遺漏任何 packet）

        Args:
            expected_payload: 期望的 payload 數據 (可選，支持有無空格格式)
            expected_can_id: 期望的 CAN ID (可選，支持 0x207 或 207 格式)
            timeout: 超時時間（秒）
            **expected_fields: 其他期望的字段值 (例如: header="0xFFFF", node="1")

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
            device_type_str: 設備類型字符串 ("USB", "POWER", "LOADER")

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

    def _normalize_payload(self, payload_str):
        """
        標準化 payload 字符串格式

        Args:
            payload_str: 輸入的 payload 字符串，可能有或沒有空格

        Returns:
            標準化的 payload 字符串（大寫，每兩個字符用空格分隔）

        Examples:
            "FF00AA55" -> "FF 00 AA 55"
            "ff 00 aa 55" -> "FF 00 AA 55"
            "FF00 AA55" -> "FF 00 AA 55"
        """
        if not payload_str:
            return None

        # 移除所有空格並轉為大寫
        clean_payload = payload_str.replace(' ', '').upper()

        # 檢查是否為有效的十六進制字符串
        if not all(c in '0123456789ABCDEF' for c in clean_payload):
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
        解析 CAN 消息字符串，提取 CAN ID 和 Payload

        Args:
            message_str: 完整的消息字符串

        Returns:
            字典包含解析出的 can_id 和 payload，如果解析失敗返回 None

        Example:
            Input: "[2025-06-06 11:25:59.203] CAN Packet:\n  CAN ID: 0x207\n  Payload: 00 00 00 00 00 00 00 00"
            Output: {'can_id': '0x207', 'payload': '00 00 00 00 00 00 00 00'}
        """
        import re

        try:
            message_str = str(message_str)

            # 提取 CAN ID
            can_id_pattern = r'CAN ID:\s*(0x[0-9A-Fa-f]+|[0-9A-Fa-f]+)'
            can_id_match = re.search(can_id_pattern, message_str)

            # 提取 Payload
            payload_pattern = r'Payload:\s*([0-9A-Fa-f\s]+)'
            payload_match = re.search(payload_pattern, message_str)

            if can_id_match and payload_match:
                can_id_raw = can_id_match.group(1)
                payload_raw = payload_match.group(1).strip()

                # 標準化 CAN ID
                normalized_can_id = self._normalize_can_id(can_id_raw)

                # 標準化 Payload（移除多餘空格，統一格式）
                normalized_payload = ' '.join(payload_raw.split()).upper()

                return {
                    'can_id': normalized_can_id,
                    'payload': normalized_payload
                }
            else:
                self._log_warning(f"無法從消息中提取 CAN ID 或 Payload: {message_str}")
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
        的非同步消息檢查邏輯
        """
        # ==================== 初始化階段 ====================

        # 記錄的開始時間
        start_system_time = time.time()
        start_datetime = datetime.now()

        self._log_info(f"🎯 開始檢查 - 系統時間: {start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")

        # 準備期望值
        expected_values = await self._prepare_expected_values(expected_payload, expected_can_id, expected_fields)

        # 初始化追蹤變數
        processed_message_ids: Set[str] = set()
        baseline_message_count = 0
        total_checked_messages = 0
        polling_interval = 0.01  # 初始輪詢間隔：10ms
        max_polling_interval = 0.1  # 最大輪詢間隔：100ms

        # 性能監控
        performance_stats = {
            'polling_cycles': 0,
            'messages_processed': 0,
            'baseline_messages': 0,
            'new_messages_found': 0,
            'parsing_failures': 0
        }

        # ==================== 建立基準線 ====================

        try:
            # 獲取當前所有訊息作為基準線
            baseline_messages = usb_device.get_recent_messages(1000)  # 獲取更多歷史訊息
            if baseline_messages:
                baseline_message_count = len(baseline_messages)
                # 記錄所有基準線訊息的ID
                for msg in baseline_messages:
                    msg_id = self._generate_message_id(msg)
                    processed_message_ids.add(msg_id)

                performance_stats['baseline_messages'] = baseline_message_count
                self._log_info(f"📊 建立基準線: {baseline_message_count} 條歷史訊息")

            # 等待一小段時間，確保基準線建立完成
            await asyncio.sleep(0.005)  # 5ms

        except Exception as e:
            self._log_warning(f"建立基準線時發生錯誤: {e}")

        # ==================== 監控循環 ====================

        self._log_info(f"🔍 開始監控新訊息...")

        try:
            while (time.time() - start_system_time) < timeout:
                performance_stats['polling_cycles'] += 1
                cycle_start = time.time()
                new_messages = []  # 初始化 new_messages 變數

                try:
                    # 獲取當前所有訊息
                    current_messages = usb_device.get_recent_messages(1000)

                    if current_messages:
                        new_messages = await self._filter_new_messages(
                            current_messages, processed_message_ids, start_datetime
                        )

                        if new_messages:
                            performance_stats['new_messages_found'] += len(new_messages)
                            self._log_info(f"📥 發現 {len(new_messages)} 條新訊息")

                            # 處理新訊息
                            for message in new_messages:
                                total_checked_messages += 1
                                performance_stats['messages_processed'] += 1

                                # 記錄已處理
                                msg_id = self._generate_message_id(message)
                                processed_message_ids.add(msg_id)

                                # 解析並檢查訊息
                                check_result = await self._check_single_message(
                                    message, expected_values, total_checked_messages
                                )
                                # print( str(check_result) )

                                if check_result['success']:
                                    # 找到匹配的訊息！
                                    elapsed_time = time.time() - start_system_time
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

                    # ==================== 記憶體管理 ====================

                    # 每1000個循環清理一次記憶體
                    if performance_stats['polling_cycles'] % 1000 == 0:
                        await self._cleanup_memory(processed_message_ids)

                        # 顯示進度報告
                        elapsed = time.time() - start_system_time
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

        elapsed_time = time.time() - start_system_time
        timeout_msg = f"⏰ 檢查超時 ({elapsed_time:.3f}s)"

        if expected_values:
            timeout_msg += f"\n未找到期望的訊息: {expected_values}"
        else:
            timeout_msg += f"\n未收到任何有效的 CAN 訊息"

        timeout_msg += f"\n檢查統計: 總共檢查了 {total_checked_messages} 條新訊息"
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
        """檢查單一訊息"""
        try:
            # 解析訊息
            parsed_message = self._parse_can_message(message)


            if not parsed_message:
                return {'success': False, 'details': '無法解析訊息格式'}

            # 如果沒有期望值，任何有效訊息都算通過
            if not expected_values:
                return {
                    'success': True,
                    'details': f"CAN ID: {parsed_message.get('can_id', 'N/A')}, Payload: {parsed_message.get('payload', 'N/A')}"
                }

            # 檢查所有期望字段
            match_results = []
            has_match = False

            for expected_field, expected_value in expected_values.items():
                actual_value = parsed_message.get(expected_field)

                if actual_value is None:
                    match_results.append(f"{expected_field}: 字段不存在")
                    continue

                # 字段比較邏輯
                # print( f"expected_field: {expected_field}, expected_value: {expected_value}, actual_value: {actual_value}" )
                field_match = await self._compare_field_values(
                    expected_field, expected_value, actual_value
                )
                print(f"field_match: {field_match}")

                if field_match:
                    has_match = True
                    match_results.append(f"{expected_field}: {actual_value} ✓")
                else:
                    match_results.append(f"{expected_field}: 期望 {expected_value}, 實際 {actual_value} ✗")

            return {
                'success': has_match,
                'details': ', '.join(match_results) if has_match else None
            }

        except Exception as e:
            return {'success': False, 'details': f'檢查錯誤: {str(e)}'}

    async def _compare_field_values(self, field_name, expected_value, actual_value):
        """比較字段值"""
        try:
            print( f"field_name: {field_name}, expected_value: {expected_value}, actual_value: {actual_value}" )
            if field_name == 'payload':
                return actual_value == expected_value
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

    def _normalize_payload(self, payload_str):
        """
        標準化 payload 字符串格式

        Args:
            payload_str: 輸入的 payload 字符串，可能有或沒有空格

        Returns:
            標準化的 payload 字符串（大寫，每兩個字符用空格分隔）
        """
        if not payload_str:
            return None

        # 移除所有空格並轉為大寫
        clean_payload = payload_str.replace(' ', '').upper()

        # 檢查是否為有效的十六進制字符串
        if not all(c in '0123456789ABCDEF' for c in clean_payload):
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
        解析 CAN 消息字符串，提取所有字段

        Args:
            message_str: 完整的消息字符串

        Returns:
            字典包含解析出的所有字段，如果解析失敗返回 None
        """
        import re

        try:
            message_str = str(message_str)
            parsed_data = {}

            # 提取時間戳
            timestamp_pattern = r'\[([0-9\-\s:\.]+)\]'
            timestamp_match = re.search(timestamp_pattern, message_str)
            if timestamp_match:
                parsed_data['timestamp'] = timestamp_match.group(1).strip()

            # 提取封包類型
            packet_type_pattern = r'\]\s*([^:]+?):'
            packet_type_match = re.search(packet_type_pattern, message_str)
            if packet_type_match:
                parsed_data['packet_type'] = packet_type_match.group(1).strip()

            # 定義所有可能的字段模式
            field_patterns = {
                'header': r'Header:\s*(0x[0-9A-Fa-f]+|[0-9A-Fa-f]+)',
                'systick': r'Systick:\s*([0-9]+)',
                'node': r'Node:\s*([0-9]+)',
                'can_type': r'CAN Type:\s*([0-9]+)',
                'can_id': r'CAN ID:\s*(0x[0-9A-Fa-f]+|[0-9A-Fa-f]+)',
                'data_length': r'Data Length:\s*([0-9]+)',
                'payload': r'Payload:\s*([0-9A-Fa-f\s]+)',
                'crc32': r'CRC32:\s*([0-9A-Fa-f]+)'
            }

            # 解析每個字段
            for field_name, pattern in field_patterns.items():
                match = re.search(pattern, message_str, re.IGNORECASE)
                if match:
                    raw_value = match.group(1).strip()

                    # 根據字段類型進行標準化
                    if field_name == 'can_id':
                        try:
                            parsed_data[field_name] = self._normalize_can_id(raw_value)
                        except ValueError:
                            parsed_data[field_name] = raw_value
                    elif field_name == 'header':
                        # 標準化 Header 格式
                        if not raw_value.upper().startswith('0X'):
                            parsed_data[field_name] = f"0x{raw_value.upper()}"
                        else:
                            parsed_data[field_name] = raw_value.upper()
                    elif field_name == 'payload':
                        # 標準化 Payload 格式
                        normalized_payload = ' '.join(raw_value.split()).upper()
                        parsed_data[field_name] = normalized_payload
                    elif field_name == 'crc32':
                        # 標準化 CRC32 格式
                        parsed_data[field_name] = raw_value.upper()
                    else:
                        # 其他字段保持原樣
                        parsed_data[field_name] = raw_value

            # 檢查是否至少解析出了基本字段
            if 'can_id' in parsed_data or 'payload' in parsed_data:
                # 添加一些便於調試的信息
                parsed_data['_raw_message'] = message_str
                parsed_data['_parsed_fields_count'] = len([k for k in parsed_data.keys() if not k.startswith('_')])

                return parsed_data
            else:
                self._log_warning(f"無法從消息中提取基本字段 (CAN ID 或 Payload): {message_str}")
                return None

        except Exception as e:
            self._log_error(f"解析 CAN 消息時發生錯誤: {e}")
            return None