import usb.core
import usb.util
from typing import Optional, Union, Callable, Dict, Tuple
from dataclasses import dataclass
import struct
from datetime import datetime
from collections import defaultdict
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CanPacket:
    """CAN 封包數據結構"""
    header: str
    systick: str
    node: str
    can_type: str
    can_id: str
    data_length: str
    payload: str
    crc32: str

    def __str__(self):
        return (
            f"CAN Packet:\n"
            f"  Header: {self.header}\n"
            f"  Systick: {self.systick}\n"
            f"  Node: {self.node}\n"
            f"  CAN Type: {self.can_type}\n"
            f"  CAN ID: {self.can_id}\n"
            f"  Data Length: {self.data_length}\n"
            f"  Payload: {self.payload}\n"
            f"  CRC32: {self.crc32}"
        )

class AsyncCDC:
    """非同步 CDC 通訊類"""

    def __init__(self, vendor_id=0x5458, product_id=0x1222):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device = None
        self.ep_out = None
        self.ep_in = None
        self.interface = None
        self.usb_dlc = 25

        self._subscribers = defaultdict(list)
        self._running = False
        self._tasks = []

        self._received_packets = 0
        self._processed_packets = 0
        self._last_stats_time = datetime.now()

        self.read_timeout = 10
        self.process_batch_size = 20

    async def connect(self) -> bool:
        """建立 USB CDC 連接"""
        try:
            if self.device:
                usb.util.dispose_resources(self.device)

            self.device = usb.core.find(
                idVendor=self.vendor_id,
                idProduct=self.product_id
            )

            if self.device is None:
                print(f'找不到設備 (VID=0x{self.vendor_id:04X}, PID=0x{self.product_id:04X})')
                return False

            self.device.set_configuration()
            cfg = self.device.get_active_configuration()
            self.interface = cfg[(1, 0)]

            self.ep_out = usb.util.find_descriptor(
                self.interface,
                custom_match=lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            self.ep_in = usb.util.find_descriptor(
                self.interface,
                custom_match=lambda e:
                usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )

            if self.ep_out is None or self.ep_in is None:
                print('無法找到端點')
                return False

            print("設備連接成功")
            return True

        except Exception as e:
            print(f"連接失敗: {str(e)}")
            return False

    async def is_connected(self) -> bool:
        """檢查設備是否連接"""
        try:
            if not self.device or not self.ep_in or not self.ep_out:
                return False
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.device.get_active_configuration()
            )
            return True
        except:
            return False

    def disconnect(self):
        """關閉連接"""
        if self.device:
            usb.util.dispose_resources(self.device)
            self.device = None
            self.ep_in = None
            self.ep_out = None

    async def receive_packets(self):
        """封包接收協程"""
        while self._running:
            try:
                if self.ep_in and await self.is_connected():
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(
                        None,
                        lambda: self.ep_in.read(
                            self.usb_dlc * self.process_batch_size,
                            timeout=self.read_timeout
                        )
                    )

                    if data:
                        packets = []
                        for i in range(0, len(data), self.usb_dlc):
                            packet_data = data[i:i + self.usb_dlc]
                            if len(packet_data) == self.usb_dlc:
                                packet = self.parse_packet(bytes(packet_data))
                                if packet:
                                    packets.append(packet)
                                    self._received_packets += 1

                        if packets:
                            await self._process_packets(packets)

            except usb.core.USBTimeoutError:
                await asyncio.sleep(0.001)
            except Exception as e:
                logger.error(f"接收錯誤: {e}")

            self._update_stats()

    async def _process_packets(self, packets):
        """批量處理封包"""
        for packet in packets:
            try:
                subscription_key = (packet.header, packet.can_id)
                subscribers = self._subscribers.get(subscription_key, [])

                if subscribers:
                    notification_tasks = []
                    for callback in subscribers:
                        if asyncio.iscoroutinefunction(callback):
                            notification_tasks.append(
                                asyncio.create_task(callback(packet))
                            )
                        else:
                            callback(packet)

                    if notification_tasks:
                        await asyncio.gather(*notification_tasks)

                self._processed_packets += 1

            except Exception as e:
                logger.error(f"處理封包錯誤: {e}")

    def _update_stats(self):
        """更新性能統計"""
        # now = datetime.now()
        # if (now - self._last_stats_time).seconds >= 5:
        #     duration = (now - self._last_stats_time).total_seconds()
        #     receive_rate = self._received_packets / duration
        #     process_rate = self._processed_packets / duration
        #
        #     # logger.info(
        #     #     f"Performance Stats:\n"
        #     #     f"  Received Rate: {receive_rate:.2f} packets/s\n"
        #     #     f"  Processed Rate: {process_rate:.2f} packets/s"
        #     # )
        #
        #     self._received_packets = 0
        #     self._processed_packets = 0
        #     self._last_stats_time = now

    def subscribe(self, can_id: str, header: str, callback: Callable):
        """訂閱特定 CAN ID 和 header"""
        subscription_key = (header, can_id)
        if callback not in self._subscribers[subscription_key]:
            self._subscribers[subscription_key].append(callback)
            logger.info(f"Added subscription for CAN ID: {can_id}, Header: {header}")

    def unsubscribe(self, can_id: str, header: str, callback: Callable):
        """取消訂閱"""
        subscription_key = (header, can_id)
        if subscription_key in self._subscribers and callback in self._subscribers[subscription_key]:
            self._subscribers[subscription_key].remove(callback)
            print(f"已取消訂閱 CAN ID: {can_id}, Header: {header}")

    async def send_data(self, node: int, can_type: int, can_id: int, dlc: int,
                       payload: Union[str, bytes]) -> bool:
        """發送數據包"""
        try:
            if not await self.is_connected():
                print("設備未連接")
                return False

            if isinstance(payload, str):
                payload = payload.encode('utf-8')
            packet = self.pack_data(node, can_type, can_id, dlc, payload)

            loop = asyncio.get_event_loop()
            bytes_written = await loop.run_in_executor(
                None,
                lambda: self.ep_out.write(packet)
            )

            return bytes_written == len(packet)

        except Exception as e:
            print(f"發送錯誤: {e}")
            return False

    def pack_data(self, node: int, can_type: int, can_id: int, dlc: int, payload: bytes) -> bytes:
        """打包數據"""
        if len(payload) > 8:
            raise ValueError("Payload超過8 bytes")

        payload = payload.ljust(8, b'\x00')

        packet = struct.pack('<HIBBIBQ',
                           0xFFFF,
                           int(datetime.now().timestamp() * 1000) & 0xFFFFFFFF,
                           node,
                           can_type,
                           can_id,
                           dlc,
                           int.from_bytes(payload, 'little')
                           )

        crc_str = self.calculate_crc(packet)
        crc_bytes = bytes.fromhex(crc_str)
        return packet + crc_bytes

    def parse_packet(self, data: bytes) -> Optional[CanPacket]:
        """解析數據包"""
        try:
            if len(data) != self.usb_dlc:
                return None

            header = struct.unpack('<H', data[0:2])[0]
            systick = struct.unpack('<I', data[2:6])[0]
            node = struct.unpack('<B', data[6:7])[0]
            can_type = struct.unpack('<B', data[7:8])[0]
            can_id = struct.unpack('<I', data[8:12])[0]
            data_length = struct.unpack('<B', data[12:13])[0]

            if (header != 0xFFFF and header != 0xAAAA):
                return None

            received_crc = ''.join([f"{x:02X}" for x in data[21:self.usb_dlc]])
            calculated_crc = self.calculate_crc(data[0:21])

            packet = CanPacket(
                header=f"0x{header:0X}",
                systick=f"{systick}",
                node=f"{node}",
                can_type=f"{can_type}",
                can_id=f"0x{can_id:0X}",
                data_length=f"{data_length}",
                payload=' '.join([f"{x:02X}" for x in data[13:13+data_length]]),
                crc32=''.join([f"{x:02X}" for x in data[21:self.usb_dlc]])
            )

            if received_crc != calculated_crc:
                return None

            return packet

        except Exception as e:
            print(f"解析錯誤: {e}")
            return None

    async def start(self):
        """啟動通訊系統"""
        if self._running:
            return

        self._running = True
        self._tasks = [
            asyncio.create_task(self.receive_packets())
        ]
        print("CDC 通訊系統啟動")

    async def stop(self):
        """停止通訊系統"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self.disconnect()
        print("CDC 通訊系統停止")

    def calculate_crc(self, data, init=0):
        crc32_table = [
            0x00000000, 0x04c11db7, 0x09823b6e, 0x0d4326d9,
            0x130476dc, 0x17c56b6b, 0x1a864db2, 0x1e475005,
            0x2608edb8, 0x22c9f00f, 0x2f8ad6d6, 0x2b4bcb61,
            0x350c9b64, 0x31cd86d3, 0x3c8ea00a, 0x384fbdbd,
            0x4c11db70, 0x48d0c6c7, 0x4593e01e, 0x4152fda9,
            0x5f15adac, 0x5bd4b01b, 0x569796c2, 0x52568b75,
            0x6a1936c8, 0x6ed82b7f, 0x639b0da6, 0x675a1011,
            0x791d4014, 0x7ddc5da3, 0x709f7b7a, 0x745e66cd,
            0x9823b6e0, 0x9ce2ab57, 0x91a18d8e, 0x95609039,
            0x8b27c03c, 0x8fe6dd8b, 0x82a5fb52, 0x8664e6e5,
            0xbe2b5b58, 0xbaea46ef, 0xb7a96036, 0xb3687d81,
            0xad2f2d84, 0xa9ee3033, 0xa4ad16ea, 0xa06c0b5d,
            0xd4326d90, 0xd0f37027, 0xddb056fe, 0xd9714b49,
            0xc7361b4c, 0xc3f706fb, 0xceb42022, 0xca753d95,
            0xf23a8028, 0xf6fb9d9f, 0xfbb8bb46, 0xff79a6f1,
            0xe13ef6f4, 0xe5ffeb43, 0xe8bccd9a, 0xec7dd02d,
            0x34867077, 0x30476dc0, 0x3d044b19, 0x39c556ae,
            0x278206ab, 0x23431b1c, 0x2e003dc5, 0x2ac12072,
            0x128e9dcf, 0x164f8078, 0x1b0ca6a1, 0x1fcdbb16,
            0x018aeb13, 0x054bf6a4, 0x0808d07d, 0x0cc9cdca,
            0x7897ab07, 0x7c56b6b0, 0x71159069, 0x75d48dde,
            0x6b93dddb, 0x6f52c06c, 0x6211e6b5, 0x66d0fb02,
            0x5e9f46bf, 0x5a5e5b08, 0x571d7dd1, 0x53dc6066,
            0x4d9b3063, 0x495a2dd4, 0x44190b0d, 0x40d816ba,
            0xaca5c697, 0xa864db20, 0xa527fdf9, 0xa1e6e04e,
            0xbfa1b04b, 0xbb60adfc, 0xb6238b25, 0xb2e29692,
            0x8aad2b2f, 0x8e6c3698, 0x832f1041, 0x87ee0df6,
            0x99a95df3, 0x9d684044, 0x902b669d, 0x94ea7b2a,
            0xe0b41de7, 0xe4750050, 0xe9362689, 0xedf73b3e,
            0xf3b06b3b, 0xf771768c, 0xfa325055, 0xfef34de2,
            0xc6bcf05f, 0xc27dede8, 0xcf3ecb31, 0xcbffd686,
            0xd5b88683, 0xd1799b34, 0xdc3abded, 0xd8fba05a,
            0x690ce0ee, 0x6dcdfd59, 0x608edb80, 0x644fc637,
            0x7a089632, 0x7ec98b85, 0x738aad5c, 0x774bb0eb,
            0x4f040d56, 0x4bc510e1, 0x46863638, 0x42472b8f,
            0x5c007b8a, 0x58c1663d, 0x558240e4, 0x51435d53,
            0x251d3b9e, 0x21dc2629, 0x2c9f00f0, 0x285e1d47,
            0x36194d42, 0x32d850f5, 0x3f9b762c, 0x3b5a6b9b,
            0x0315d626, 0x07d4cb91, 0x0a97ed48, 0x0e56f0ff,
            0x1011a0fa, 0x14d0bd4d, 0x19939b94, 0x1d528623,
            0xf12f560e, 0xf5ee4bb9, 0xf8ad6d60, 0xfc6c70d7,
            0xe22b20d2, 0xe6ea3d65, 0xeba91bbc, 0xef68060b,
            0xd727bbb6, 0xd3e6a601, 0xdea580d8, 0xda649d6f,
            0xc423cd6a, 0xc0e2d0dd, 0xcda1f604, 0xc960ebb3,
            0xbd3e8d7e, 0xb9ff90c9, 0xb4bcb610, 0xb07daba7,
            0xae3afba2, 0xaafbe615, 0xa7b8c0cc, 0xa379dd7b,
            0x9b3660c6, 0x9ff77d71, 0x92b45ba8, 0x9675461f,
            0x8832161a, 0x8cf30bad, 0x81b02d74, 0x857130c3,
            0x5d8a9099, 0x594b8d2e, 0x5408abf7, 0x50c9b640,
            0x4e8ee645, 0x4a4ffbf2, 0x470cdd2b, 0x43cdc09c,
            0x7b827d21, 0x7f436096, 0x7200464f, 0x76c15bf8,
            0x68860bfd, 0x6c47164a, 0x61043093, 0x65c52d24,
            0x119b4be9, 0x155a565e, 0x18197087, 0x1cd86d30,
            0x029f3d35, 0x065e2082, 0x0b1d065b, 0x0fdc1bec,
            0x3793a651, 0x3352bbe6, 0x3e119d3f, 0x3ad08088,
            0x2497d08d, 0x2056cd3a, 0x2d15ebe3, 0x29d4f654,
            0xc5a92679, 0xc1683bce, 0xcc2b1d17, 0xc8ea00a0,
            0xd6ad50a5, 0xd26c4d12, 0xdf2f6bcb, 0xdbee767c,
            0xe3a1cbc1, 0xe760d676, 0xea23f0af, 0xeee2ed18,
            0xf0a5bd1d, 0xf464a0aa, 0xf9278673, 0xfde69bc4,
            0x89b8fd09, 0x8d79e0be, 0x803ac667, 0x84fbdbd0,
            0x9abc8bd5, 0x9e7d9662, 0x933eb0bb, 0x97ffad0c,
            0xafb010b1, 0xab710d06, 0xa6322bdf, 0xa2f33668,
            0xbcb4666d, 0xb8757bda, 0xb5365d03, 0xb1f740b4
        ]
        crc = init

        for byte in data:
            # 模擬 C 程式的運算邏輯
            crc = ((crc << 8) ^ crc32_table[((crc >> 24) ^ byte) & 0xFF]) & 0xFFFFFFFF
            result = [
                (crc >> 0) & 0xFF,
                (crc >> 8) & 0xFF,
                (crc >> 16) & 0xFF,
                (crc >> 24) & 0xFF
            ]

        return ''.join(f"{b:02X}" for b in result)


    async def handle_response(packet):
        """處理回應封包"""
        if packet.header == "0xAAAA":
            print(f"Got response packet:")
            print(packet)



