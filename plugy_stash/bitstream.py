"""LSB-first bit reader/writer used by Diablo II save files.

Diablo II writes bit fields starting at the least significant bit of each byte.
All item structures are byte-aligned at their start and padded to the next byte
boundary before the following item.
"""
from __future__ import annotations


class BitReader:
    def __init__(self, data: bytes | bytearray, bitpos: int = 0) -> None:
        self.data = data
        self.bitpos = bitpos

    @property
    def bytepos(self) -> int:
        return (self.bitpos + 7) // 8

    def read(self, bits: int) -> int:
        if bits < 0:
            raise ValueError("negative bit count")
        end = self.bitpos + bits
        if end > len(self.data) * 8:
            raise ValueError("unexpected end of item data")
        value = 0
        shift = 0
        while self.bitpos < end:
            byte_index = self.bitpos >> 3
            bit_index = self.bitpos & 7
            take = min(8 - bit_index, end - self.bitpos)
            chunk = (self.data[byte_index] >> bit_index) & ((1 << take) - 1)
            value |= chunk << shift
            shift += take
            self.bitpos += take
        return value

    def skip(self, bits: int) -> None:
        self.read(bits)

    def align(self) -> None:
        self.bitpos = (self.bitpos + 7) & ~7


def read_bits_at(data: bytes | bytearray, bitpos: int, bits: int) -> int:
    return BitReader(data, bitpos).read(bits)


def write_bits_at(buf: bytearray, bitpos: int, bits: int, value: int) -> None:
    """Write ``bits`` bits at an arbitrary (possibly unaligned) position.

    Only the touched bits are changed; every other bit in the buffer is kept.
    """
    if bits < 0:
        raise ValueError("negative bit count")
    if value < 0 or value >= (1 << bits):
        raise ValueError(f"value {value} does not fit in {bits} bits")
    end = bitpos + bits
    if end > len(buf) * 8:
        raise ValueError("write past end of buffer")
    shift = 0
    while bitpos < end:
        byte_index = bitpos >> 3
        bit_index = bitpos & 7
        take = min(8 - bit_index, end - bitpos)
        mask = ((1 << take) - 1) << bit_index
        chunk = (value >> shift) & ((1 << take) - 1)
        buf[byte_index] = (buf[byte_index] & ~mask) | (chunk << bit_index)
        shift += take
        bitpos += take
