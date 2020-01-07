# import pytest

from vcuui.gnss import _calc_checksum, _create_ubx_message


class TestChecksum:
    def test_one(self):
        # b5 62 - 06 04 04 00 00 00 09 00 - 17 76
        a, b = _calc_checksum(bytearray.fromhex("06 04 04 00 00 00 09 00"))
        assert(a == 0x17)
        assert(b == 0x76)

    def test_two(self):
        # b5 62 - 09 14 04 00 00 00 00 00 - 21 ec
        a, b = _calc_checksum(bytearray.fromhex("09 14 04 00 00 00 00 00"))
        assert(a == 0x21)
        assert(b == 0xec)

    def test_three(self):
        # b5 62 - 06 04 04 00 FF 87 00 00 - 94 f5
        a, b = _calc_checksum(bytearray.fromhex("06 04 04 00 FF 87 00 00"))
        assert(a == 0x94)
        assert(b == 0xf5)


class TestMessageCreator():
    def test_one(self):
        msg = _create_ubx_message(bytearray.fromhex("06 04 04 00 FF 87 00 00"))
        print(msg)
        assert(msg == bytearray.fromhex('b5 62 06 04 04 00 FF 87 00 00 94 f5'))
