import serial


class UM24C:

    REQUEST = b"\xF0"
    RESPONSE_SIZE = 130

    def __init__(self, port: str):
        self.connection = serial.Serial(
            port=port,
            baudrate=9600,
            timeout=2,
            write_timeout=2,
        )

    def read(self):
        self.connection.reset_input_buffer()

        self.connection.write(self.REQUEST)
        self.connection.flush()

        data = self.connection.read(self.RESPONSE_SIZE)

        if len(data) != self.RESPONSE_SIZE:
            raise RuntimeError(
                f"Invalid UM24C response size: {len(data)}"
            )

        voltage = int.from_bytes(
            data[2:4],
            byteorder="big",
        ) / 100.0

        current = int.from_bytes(
            data[4:6],
            byteorder="big",
        ) / 1000.0

        power = int.from_bytes(
            data[6:10],
            byteorder="big",
        ) / 1000.0

        return voltage, current, power

    def close(self):
        self.connection.close()