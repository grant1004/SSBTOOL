from dataclasses import dataclass
from typing import Dict


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

    def to_dict(self) -> Dict[str, str]:
        """將 CAN 數據包轉換為字典格式"""
        return {
            'header': self.header,
            'systick': self.systick,
            'node': self.node,
            'can_type': self.can_type,
            'can_id': self.can_id,
            'data_length': self.data_length,
            'payload': self.payload,
            'crc32': self.crc32
        }
