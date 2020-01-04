import serial
import time
#import binascii


def save_state():
    res = ''

    ser = serial.Serial('/dev/gps0', 115200, timeout=0.1)

    # Stop GNSS receiver, to keep battery backed memory consistent

    print("Stopping GNSS")
    res += '<br>Stopping GNSS: '
    ubx_stop = bytearray.fromhex("b5 62 06 04 04 00 00 00 08 00 16 74")
    ser.reset_input_buffer()
    ser.write(ubx_stop)

    if _expect_text(ser, 'Stopping'):
        res += 'Ok'
    else:
        res += 'Failed'

    print("Saving state to Flash")
    res += '<br>Saving state to Flash: '
    ubx_flash_backup = bytearray.fromhex("b5 62 09 14 04 00 00 00 00 00 21 ec")
    ser.reset_input_buffer()
    ser.write(ubx_flash_backup)

    # Ideally we would check for response and ACK here, but since this is only
    # a simple developer application we ommit it here
    # b5 62 09 14 08 00 02 00 00 00 01 00 00 00 28 ac
    if _expect_hex(ser, bytearray.fromhex('62 09 14 08 00 02 00 00 00 01 00 00')):
        res += 'Ok'
    else:
        res += 'Failed'

    # Restart receiver operation

    print("Restarting GNSS")
    res += '<br>Restarting GNSS: '
    ubx_start = bytearray.fromhex("b5 62 06 04 04 00 00 00 09 00 17 76")
    ser.reset_input_buffer()
    ser.write(ubx_start)

    if _expect_text(ser, 'Starting'):
        res += 'Ok'
    else:
        res += 'Failed'

    return res


def _expect_text(ser, text):
    t_end = time.time() + 2.0
    while time.time() < t_end:
        line = ser.readline()
        # print(binascii.hexlify(line))
        if line == b'':
            return False

        try:
            line = line.decode('ascii')
            # print(line)
            if text in line:
                return True

        except UnicodeDecodeError:
            pass


def _expect_hex(ser, hex):
    data = bytearray()
    t_end = time.time() + 1.0
    while time.time() < t_end:
        line = ser.read(8)
        # print(binascii.hexlify(line))
        data += line
        pos = data.find(hex)
        # print(pos)
        if pos != -1:
            return True
