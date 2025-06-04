from robot.api.deco import library, keyword
from robot.api import logger
import sys
import os

from Lib import UDP6730, PEL500

# 獲取當前檔案所在目錄的路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
# 將該路徑加入到 Python 的模組搜尋路徑中
if current_dir not in sys.path:
    sys.path.append(current_dir)

from SSB_Dongle import AsyncCDC, CanPacket
from typing import Dict, List
import time
import asyncio

@library
class CommonLibrary:
    """CAN Monitor Library for Robot Framework

    這個庫提供與 CAN 設備通訊的功能。
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'

    def __init__(self,debug=True, loader_port="COM37", power_supply_port = "COM41"):
        self.monitor = None
        self.loop = None
        self._message_callback = None
        self._received_messages = []
        self._message_buffers: Dict[str, List[CanPacket]] = {}  # 使用普通字典
        self._loader_port = loader_port
        self.loader = None
        self._loader_connected = False
        self._power_supply_connected = False
        self.debug = debug
        self.power_supply = None
        self._power_supply_port = power_supply_port

    def _init_loader(self):
        """初始化 loader 連接"""
        if not self._loader_connected:
            try:
                self.loader = PEL500(port=self._loader_port)
                self._loader_connected = True
            except Exception as e:
                raise RuntimeError(f"Failed to initialize loader on port {self._loader_port}: {str(e)}")

    def _init_power_supply(self):
        """初始化電源供應器連接"""
        if not self._power_supply_connected:
            try:
                self.power_supply = UDP6730(port=self._power_supply_port)
                self._power_supply_connected = True
                return True
            except Exception as e:
                raise RuntimeError(f"Failed to initialize power supply on port {self._power_supply_port}: {str(e)}")
        return False


    @keyword
    def disconnect_loader(self):
        """斷開 loader 連接"""
        if self._loader_connected and self.loader:
            try:
                self.loader.close()
            except Exception as e:
                print(f"Warning: Error while closing loader: {str(e)}")
            finally:
                self.loader = None
                self._loader_connected = False

    @keyword
    def disconnect_power_supply(self):
        """斷開 loader 連接"""
        if self._power_supply_connected and self.power_supply:
            try:
                self.power_supply.close()
            except Exception as e:
                print(f"Warning: Error while closing loader: {str(e)}")
            finally:
                self.power_supply = None
                self._power_supply_connected = False

    def _run_coroutine(self, coroutine):
        """執行協程"""
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        return self.loop.run_until_complete(coroutine)

    async def _message_handler(self, packet):
        """處理接收到的訊息"""
        if packet:
            # 確保 can_id 存在於緩存中
            if packet.can_id not in self._message_buffers:
                self._message_buffers[packet.can_id] = []
            # 儲存訊息
            self._message_buffers[packet.can_id].append(packet)
            logger.debug(f"收到訊息 - ID: {packet.can_id}, 完整數據: {packet.systick}, Payload: {packet.payload}")

    @keyword
    def check_message_payload(self, can_id: str, start_bit: str = None, end_bit: str = None,
                              expected_dec: str = None, byte_order: str = "LSB"):
        """檢查特定 CAN ID 的訊息，可選擇是否檢查 payload

        Args:
            can_id: CAN ID 字串 (例如: "0x123")
            start_bit: 起始位元字串 (從"0"開始)，可選
            end_bit: 結束位元字串，可選
            expected_dec: 預期的十進制值字串，可選
            byte_order: 要檢查的位元組順序，"LSB" 或 "MSB"
        """
        messages = self._message_buffers.get(can_id, [])
        if self.debug:
            print("size of message=", len(messages))

        # 如果只需要確認有沒有收到 CAN ID
        if start_bit is None or end_bit is None or expected_dec is None:
            if len(messages) > 0:
                logger.info(f"已收到 CAN ID {can_id} 的訊息，共 {len(messages)} 筆")
                return True
            else:
                raise AssertionError(f"未收到 CAN ID: {can_id} 的訊息")

        logger.info(
            f"檢查 CAN ID {can_id} 的訊息，bits {start_bit}-{end_bit}，預期值: {expected_dec}，位元組順序: {byte_order}")
        if self.debug:
            print(
                f"檢查 CAN ID {can_id} 的訊息，bits {start_bit}-{end_bit}，預期值: {expected_dec}，位元組順序: {byte_order}")

        try:
            # 轉換輸入參數
            start_bit_int = int(start_bit)
            end_bit_int = int(end_bit)
            expected_dec_int = int(expected_dec)

            # 驗證輸入值
            if start_bit_int < 0 or end_bit_int < 0:
                raise ValueError("起始位元和結束位元不能為負數")
            if start_bit_int > end_bit_int:
                raise ValueError("起始位元不能大於結束位元")

        except ValueError as e:
            logger.error(f"參數轉換失敗: {e}")
            raise ValueError(f"無效的參數值: start_bit={start_bit}, end_bit={end_bit}, expected_dec={expected_dec}")

        # 初始化計數器
        match_count = 0
        mismatch_count = 0
        error_count = 0
        error_msg = None

        for packet in messages:
            try:
                # 從 CanPacket 獲取 payload 字串
                payload_str = packet.payload
                hex_values = payload_str.split()

                # 計算需要的位元組數
                start_byte = start_bit_int // 8
                end_byte = (end_bit_int // 8) + 1

                if end_byte > len(hex_values):
                    error_count += 1
                    error_msg = f"Payload 長度不足，需要 {end_byte} 位元組，但收到資訊只有 {len(hex_values)} 位元組"
                    raise ValueError(error_msg)

                # 取出需要的位元組
                relevant_hex_values = hex_values[start_byte:end_byte]

                # 根據 byte_order 決定如何組合位元組
                if byte_order.upper() == "LSB":
                    # 對於 LSB，保持原始順序
                    value_str = ''.join(relevant_hex_values[::-1])  # 反轉順序並連接
                else:
                    # 對於 MSB，反轉順序
                    value_str = ''.join(relevant_hex_values)

                # 將十六進制字串轉換為整數
                actual_value = int(value_str, 16)

                # 計算要提取的位元
                total_bits = end_bit_int - start_bit_int + 1
                # 創建掩碼並提取值
                mask = (1 << total_bits) - 1
                actual_value = actual_value & mask

                logger.debug(f"Payload: {payload_str}")
                logger.debug(f"Relevant bytes: {' '.join(relevant_hex_values)}")
                logger.debug(f"Combined value: {value_str}")
                logger.debug(f"Actual value: {actual_value}")

                if actual_value == expected_dec_int:
                    match_count += 1
                    logger.debug(f"實際值: {actual_value}，預期值: {expected_dec} -> pass")
                    if self.debug:
                        print(f"實際值: {actual_value}，預期值: {expected_dec} -> pass")
                else:
                    mismatch_count += 1
                    logger.debug(f"實際值: {actual_value}，預期值: {expected_dec} -> fail")
                    if self.debug:
                        print(f"實際值: {actual_value}，預期值: {expected_dec} -> fail")

            except Exception as e:
                error_count += 1
                logger.error(f"處理 payload 時發生錯誤: {e}, payload: {packet}")
                continue

        # 輸出統計信息
        stats_message = (f"\n統計信息:\n"
                         f"總訊息數: {len(messages)}\n"
                         f"匹配數: {match_count}\n"
                         f"不匹配數: {mismatch_count}\n"
                         f"錯誤數: {error_count}")

        if int(mismatch_count) > int(0.2 * len(messages)):
            raise AssertionError(f"不匹配數超過20%，開啟debug查看詳細內容:{stats_message}")
        else:
            logger.info(stats_message)

        if self.debug:
            print(stats_message)

        if match_count > 0:
            return True
        elif len(messages) == 0:
            raise AssertionError(f"未找到匹配的CAN ID: {can_id}")
        elif error_msg:
            raise ValueError(error_msg)
        else:
            raise AssertionError(f"未找到匹配的值。{stats_message}")
    @keyword
    def get_collected_messages(self, can_id: str):
        """獲取特定 CAN ID 收集到的所有訊息"""
        return self._message_buffers.get(can_id, [])

    @keyword
    def clear_message_buffer(self, can_id: str = None):
        """清除訊息緩存"""
        if can_id is None:
            self._message_buffers.clear()
        elif can_id in self._message_buffers:
            self._message_buffers[can_id].clear()

    @keyword
    def connect_to_can_device(self):
        """連接到 CAN 設備"""
        logger.info('Connecting to CAN device...')
        # self._init_loader()
        # self._init_power_supply()
        self.monitor = AsyncCDC()
        result = self._run_coroutine(self.monitor.connect())
        if not result:
            raise ConnectionError("無法連接到 CAN 設備")
        self._run_coroutine(self.monitor.start())
        logger.info('Connected to CAN device')

    @keyword
    def disconnect_from_can_device(self):
        """斷開 CAN 設備連接"""
        if self.monitor:
            self._run_coroutine(self.monitor.stop())
            self.monitor = None

    @keyword
    def subscribe_and_collect(self, can_id: str, header: str = "0xFFFF", timeout: str = "5.0"):
        """訂閱特定 CAN ID 並收集指定時間的訊息

        Args:
            can_id: CAN ID
            header: 標頭，預設為 "0xFFFF"
            timeout: 收集時間（秒），接受字符串格式，例如 "5.0"
        """
        try:
            timeout_float = float(timeout)
        except ValueError:
            logger.error(f"無效的 timeout 值: {timeout}，必須是可轉換為浮點數的字符串")
            raise ValueError(f"無效的 timeout 值: {timeout}")

        logger.info(f"開始收集 CAN ID {can_id} header: {header} 的訊息，時間: {timeout}秒")

        # 初始化或清空此 ID 的緩存
        self._message_buffers[can_id] = []

        # 訂閱並開始收集
        self.subscribe_to_can_id(can_id, header)

        async def collect_messages():
            start_time = self.loop.time()
            while (self.loop.time() - start_time) < timeout_float:
                await asyncio.sleep(0.001)

        # 執行收集
        self.loop.run_until_complete(collect_messages())

        # 獲取收集到的訊息
        messages = self._message_buffers.get(can_id, [])
        logger.info(f"收集完成，共收到 {len(messages)} 筆訊息")
        if self.debug == True:
            print(f"收集完成，共收到 {len(messages)} 筆訊息")

        return messages

    @keyword
    def unsubscribe_to_can_id(self, can_id: str, header):
        """取消訂閱特定的 CAN ID"""
        if not self.monitor:
            raise RuntimeError("尚未連接到設備")
        #確保使用正確的格式訂閱
        if isinstance(can_id, str):
            can_id = can_id.lower()

        self.monitor.unsubscribe(can_id, header, self._message_handler)
        logger.info(f"已取消訂閱 CAN ID: {can_id}")

    @keyword
    def subscribe_to_can_id(self, can_id, header):
        """訂閱特定的 CAN ID"""
        if not self.monitor:
            raise RuntimeError("尚未連接到設備")

        # 確保使用正確的格式訂閱
        if isinstance(can_id, str):
            can_id = can_id.lower()


        self.monitor.subscribe(can_id, header, self._message_handler)
        logger.info(f"已訂閱 CAN ID: {can_id}")

    @keyword
    def send_can_message(self, can_id, payload, node=1, can_type=0):
        """發送單次 CAN 訊息

        Args:
            can_id: CAN ID (例如: "0x123" 或 291)
            payload: 十六進制格式的資料 (例如: "01 02 03 04")
            node: 節點編號 (預設: 1) ( 1:公, 0:私 )
            can_type: CAN 類型 (預設: 0)

        Returns:
            tuple: (bool, int) - (是否成功, systick值)
                   如果沒有收到確認封包，systick 將為 None
        """
        if not self.monitor:
            raise RuntimeError("尚未連接到設備")

        # 轉換 CAN ID
        if isinstance(can_id, str):
            can_id = int(can_id, 16)

        # 轉換 payload
        if isinstance(payload, str):
            payload = payload.replace(' ', '').replace('0x', '')
            if len(payload) % 2 != 0:
                payload = '0' + payload
            payload = bytes.fromhex(payload)

        # 用於追蹤是否收到正確的回應和systick值
        tx_received = False
        received_systick = None

        async def _tx_message_handler(packet):
            """處理接收到的訊息"""
            nonlocal tx_received, received_systick
            if packet:
                if packet.header == "0xAAAA":  # 檢查 header
                    tx_received = True
                    received_systick = int(packet.systick)  # 儲存 systick 值
                    # 確保 can_id 存在於緩存中
                    if packet.can_id not in self._message_buffers:
                        self._message_buffers[packet.can_id] = []
                    # 儲存訊息
                    self._message_buffers[packet.can_id].append(packet)
                    logger.debug(
                        f"收到發送確認 - Header: {packet.header}, ID: {packet.can_id}, Payload: {packet.payload}, SystemTick: {packet.systick}")
                    if self.debug == True:
                        print(f"收到發送確認 - Header: {packet.header}, ID: {packet.can_id}, Payload: {packet.payload}, SystemTick: {packet.systick}")

        async def send_with_minimal_delay():
            # subscribe 不是異步方法，所以不需要 await
            self.monitor.subscribe(hex(can_id), "0xAAAA", _tx_message_handler)
            result = await self.monitor.send_data(node, can_type, can_id, len(payload), payload)
            if result:
                logger.info(
                    f"發送訊息 - CAN ID: 0x{can_id:X}, Node: {node}, Type: {can_type}, Payload: {' '.join([f'{b:02X}' for b in payload])}")
            else:
                raise RuntimeError(f"發送失敗 - CAN ID: 0x{can_id:X}")

            # 等待接收確認或超時
            start_time = asyncio.get_event_loop().time()
            while not tx_received:
                await asyncio.sleep(0.001)
                if asyncio.get_event_loop().time() - start_time > 0.1:  # 100ms 超時
                    logger.info(f"未收到 0xAAAA header 的確認封包 - CAN ID: 0x{can_id:X}")
                    if self.debug:
                        print(f"未收到 0xAAAA header 的確認封包 - CAN ID: 0x{can_id:X}")
                    break

            return received_systick

        try:
            systick = self.loop.run_until_complete(send_with_minimal_delay())
            return systick
        except Exception as e:
            logger.error(f"發送錯誤: {e}")
            return False

    @keyword
    def clear_received_messages(self):
        """清除已接收的訊息緩存"""
        self._received_messages.clear()

    @keyword
    def Power_Supply_Connect(self):
        payload = "0A 00 00 00 00"
        self.send_can_message("0x301", payload, 0, 0)

    @keyword
    def Power_Supply_Disconnect(self):
        payload = "0B 00 00 00 00"
        self.send_can_message("0x301", payload, 0, 0)

    @keyword
    def Power_Supply_Output_On(self):
        """開啟電源輸出"""
        if not self.power_supply:
            self._init_power_supply()
        self.power_supply.output_on()
        logger.info("Power supply output turned ON")

    @keyword
    def Power_Supply_Output_Off(self):
        """關閉電源輸出"""
        if not self.power_supply:
            self._init_power_supply()
        self.power_supply.output_off()
        logger.info("Power supply output turned OFF")

    @keyword
    def Power_Supply_Get_Current_Voltage_Setting(self):
        """測量當前電流和電壓

        Returns:
            tuple: (voltage_mv, current_ma) - 電壓(mV)和電流(mA)的值
        """
        if not self.power_supply:
            self._init_power_supply()

        voltage = self.power_supply.get_voltage_setting()
        current = self.power_supply.get_current_setting()

        if voltage is not None and current is not None:
            voltage_mv = int(voltage * 1000)  # Convert V to mV
            current_ma = int(current * 1000)  # Convert A to mA

            if self.debug:
                print(f"Voltage: {voltage_mv} mV")
                print(f"Current: {current_ma} mA")

            return voltage_mv, current_ma
        return None, None

    @keyword
    def Power_Supply_Set_Voltage_Protection(self, voltage: str):
        """設置電壓保護值

        Args:
            voltage: 電壓值(mV)的字串
        """
        if not self.power_supply:
            self._init_power_supply()

        # 注意：UDP6730可能不直接支持此功能
        logger.warning("Voltage protection setting might not be supported by UDP6730")

    @keyword
    def Power_Supply_Set_Voltage(self, voltage: str):
        """設置輸出電壓

        Args:
            voltage: 電壓值(mV)的字串
        """
        if not self.power_supply:
            self._init_power_supply()

        voltage_v = float(voltage) / 1000  # Convert mV to V
        self.power_supply.set_voltage(voltage_v)
        logger.info(f"Voltage set to {voltage} mV")

    @keyword
    def Power_Supply_Set_Current_Protection(self, current: str):
        """設置電流保護值

        Args:
            current: 電流值(mA)的字串
        """
        if not self.power_supply:
            self._init_power_supply()

        # 注意：UDP6730可能不直接支持此功能
        logger.warning("Current protection setting might not be supported by UDP6730")

    @keyword
    def Power_Supply_Set_Current(self, current: str):
        """設置輸出電流

        Args:
            current: 電流值(mA)的字串
        """
        if not self.power_supply:
            self._init_power_supply()

        current_a = float(current) / 1000  # Convert mA to A
        self.power_supply.set_current(current_a)
        logger.info(f"Current set to {current} mA")

    @keyword
    def Loader_Connect(self):
        payload = "0F 00 00 00 00"
        self.send_can_message("0x301", payload, 0, 0)

    @keyword
    def Loader_Disconnect(self):
        payload = "10 00 00 00 00"
        self.send_can_message("0x301", payload, 0, 0)

    @keyword
    def Loader_Output_On(self):
        self.loader.load_on()

    @keyword
    def Loader_Output_Off(self):
        self.loader.load_off()

    @keyword
    def Loader_Set_Mode(self, mode):
        """Set the operation mode

        Args:
            mode (str): 'CC', 'CR', 'CV' or 'CP'
        """
        self.loader.set_mode(mode)

    @keyword
    def Loader_Set_Current(self, current_str, level="HIGH"):
        """Set current in CC mode

        Args:
            current_str (str): Current value in mA (e.g. '5000')
            level (str): "HIGH" or "LOW"
        """
        current = float(current_str) / 1000  # Convert mA to A
        self.loader.set_current(current, level)

    @keyword
    def Loader_Set_Resistance(self, resistance_str, level="HIGH"):
        """Set resistance in CR mode

        Args:
            resistance_str (str): Resistance value in Ω (e.g. '10')
            level (str): "HIGH" or "LOW"
        """
        resistance = float(resistance_str)  # Already in Ω
        self.loader.set_resistance(resistance, level)

    @keyword
    def Loader_Set_Voltage(self, voltage_str, level="HIGH"):
        """Set voltage in CV mode

        Args:
            voltage_str (str): Voltage value in mV (e.g. '5000')
            level (str): "HIGH" or "LOW"
        """
        voltage = float(voltage_str) / 1000  # Convert mV to V
        self.loader.set_voltage(voltage, level)

    @keyword
    def Loader_Set_Power(self, power_str, level="HIGH"):
        """Set power in CP mode

        Args:
            power_str (str): Power value in mW (e.g. '1000')
            level (str): "HIGH" or "LOW"
        """
        power = float(power_str) / 1000  # Convert mW to W
        self.loader.set_power(power, level)

    @keyword
    def Power_Supply_Measure_Voltage(self):
        """Measure current voltage

        Returns:
            str: Measured voltage in mV
        """
        voltage = self.power_supply.measure_voltage()
        logger.info(f"{int(voltage * 1000)} mV")
        return f"{int(voltage * 1000)} mV"

    @keyword
    def Power_Supply_Measure_Current(self):
        """Measure current current

        Returns:
            str: Measured current in mA
        """
        current = self.power_supply.measure_current()
        logger.info(f"{int(current * 1000 )} mA")
        return f"{int(current * 1000)} A"

    @keyword
    def Power_Supply_Measure_Power(self):
        """Measure current power

        Returns:
            str: Measured power in mW
        """
        power = self.power_supply.measure_power()
        logger.info(f"{int(power * 1000)} mW")
        return f"{int(power * 1000)} mW"

    @keyword
    def Loader_Measure_Voltage(self):
        """Measure current voltage

        Returns:
            str: Measured voltage in mV
        """
        voltage = self.loader.measure_voltage()
        logger.info(f"{int(voltage * 1000)} mV")
        return f"{int(voltage * 1000)} mV"

    @keyword
    def Loader_Measure_Current(self):
        """Measure current current

        Returns:
            str: Measured current in mA
        """
        current = self.loader.measure_current()
        logger.info(f"{int(current * 1000 )} mA")
        return f"{int(current * 1000)} A"

    @keyword
    def Loader_Measure_Power(self):
        """Measure current power

        Returns:
            str: Measured power in mW
        """
        power = self.loader.measure_power()
        logger.info(f"{int(power * 1000)} mW")
        return f"{int(power * 1000)} mW"

    @keyword
    def Wake_Up(self):

        payload = "0E 00 00 00 00"
        self.send_can_message("0x301", payload, 0, 0)

    @keyword
    def Charger_In(self):

        payload = "0C 00 00 00 00"
        self.send_can_message("0x301", payload, 0, 0)

    @keyword
    def Charger_Out(self):
        payload = "0D 00 00 00 00"
        self.send_can_message("0x301", payload, 0, 0)


    def _dec_to_hex_bytes(self, decimal_str: str, hex_bytes_len: int = 4):
        # Convert string to integer, then to hex and remove '0x' prefix
        hex_str = hex(int(decimal_str))[2:]

        # Ensure even length for proper byte splitting
        if len(hex_str) % 2 != 0:
            hex_str = '0' + hex_str

        # Split into bytes
        hex_bytes = [hex_str[i:i + 2] for i in range(0, len(hex_str), 2)]

        # Reverse the bytes for LSB order
        hex_bytes.reverse()

        # Pad to 4 bytes if necessary
        while len(hex_bytes) < hex_bytes_len:
            hex_bytes.append('00')

        return ' '.join(hex_bytes)

    @keyword
    def Stop_Motor_Test(self):

        payload = f"00 00 00 00 00 00 00 00"

        self.send_can_message("0x20010", payload, 1, 1)

    @keyword
    def Control_Motor_To_Speed(self, Speed: str, Time: str = "0"):

        payload = f"01 " + self._dec_to_hex_bytes (Speed, hex_bytes_len=4) + f" " + self._dec_to_hex_bytes (Time, hex_bytes_len=3)


        self.send_can_message(can_id="0x20010", payload=payload, node=1, can_type=1)

    @keyword
    def Control_Motor_To_Amplitude(self, Amplitude: str, Time: str = "0"):

        payload = f"01 " + self._dec_to_hex_bytes (Amplitude, hex_bytes_len=4) + f" " + self._dec_to_hex_bytes (Time, hex_bytes_len=3)

        self.send_can_message(can_id="0x20010", payload=payload, node=1, can_type=1)


    @keyword
    def Button_All_Off(self):

        payload = "00 00"
        self.send_can_message(can_id="0x1000", payload=payload, node=0, can_type=1)

    def button_short_press(self, button_num):
        temp = 2 ** button_num
        hex_str = hex(temp)[2:].upper()
        if len(hex_str) % 2 != 0:
            hex_str = '0' + hex_str
        hex_bytes = [hex_str[i:i + 2] for i in range(0, len(hex_str), 2)]
        hex_bytes.reverse()
        while len(hex_bytes) < 2:
            hex_bytes.append('00')

        hex_bytes = ' '.join(hex_bytes)

        self.send_can_message(can_id="0x1000", payload=hex_bytes, node=0, can_type=1)
        time.sleep(0.2)
        self.send_can_message(can_id="0x1000", payload="00 00", node=0, can_type=1)
        time.sleep(0.2)


    @keyword
    def Button_Right_Short_Press(self):
        self.button_short_press(0)

    @keyword
    def Button_Left_Short_Press(self):
        self.button_short_press(1)

    @keyword
    def Button_Up_Short_Press(self):
        self.button_short_press(2)

    @keyword
    def Button_Down_Short_Press(self):
        self.button_short_press(3)

    @keyword
    def Button_Power_Press(self):
        self.send_can_message(can_id="0x1000", payload="10 00", node=0, can_type=1)
        time.sleep(3)
        self.send_can_message(can_id="0x1000", payload="00 00", node=0, can_type=1)
        time.sleep(0.2)


    @keyword
    def BMS_MCU_Reset(self):

        payload = f"00 00 00 00 00 00 00 00"

        self.send_can_message("0x40010", payload, 1, 1)

    @keyword
    def Controller_MCU_Reset(self):
        """重置控制器 MCU

            發送命令重置主控制器的微控制器。

            Returns:
                None

            Examples:
                | Controller MCU Reset |
        """
        payload = f"08 00 00 00 00 00 00 00"

        self.send_can_message("0x20010", payload, 1, 1)

    @keyword
    def HMI_MCU_Reset(self):
        """重置 HMI MCU

            發送命令重置人機介面的微控制器。

            Returns:
                None

            Examples:
                | HMI MCU Reset |
        """

        payload = f"0F 00 00 00 00 00 00 00"

        self.send_can_message("0x30010", payload, 1, 1)

