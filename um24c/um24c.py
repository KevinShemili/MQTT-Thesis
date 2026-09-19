import socket


class UM24C:

    MAC_ADDRESS = "98:DA:F0:01:0C:10"

    REQUEST = b"\xf0"
    RESPONSE_SIZE = 130
    CHANNEL = 1

    def __init__(self):
        self.connection = socket.socket(
            socket.AF_BLUETOOTH,
            socket.SOCK_STREAM,
            socket.BTPROTO_RFCOMM,
        )

        self.connection.settimeout(5)
        self.connection.connect((self.MAC_ADDRESS, self.CHANNEL))

    def read(self):
        self.connection.sendall(self.REQUEST)

        data = bytearray()

        while len(data) < self.RESPONSE_SIZE:
            chunk = self.connection.recv(self.RESPONSE_SIZE - len(data))

            if not chunk:
                raise RuntimeError(f"UM24C connection closed after {len(data)} bytes")

            data.extend(chunk)

        voltage = int.from_bytes(data[2:4], byteorder="big") / 100.0
        current = int.from_bytes(data[4:6], byteorder="big") / 1000.0
        power = int.from_bytes(data[6:10], byteorder="big") / 1000.0

        return voltage, current, power

    def close(self):
        self.connection.close()
