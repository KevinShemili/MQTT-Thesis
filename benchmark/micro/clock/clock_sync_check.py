import socket
import statistics
import sys
import time

import ntplib

PORT = 12345
BURSTS = 30
EXCHANGES_PER_BURST = 8
INTERVAL_SECONDS = 5


def serve():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", PORT))

        while True:
            data, address = sock.recvfrom(256)
            received = ntplib.system_to_ntp_time(time.time())

            request = ntplib.NTPPacket()
            request.from_data(data)

            reply = ntplib.NTPPacket(version=request.version, mode=4)
            # Measurement responder only; not a synchronization source.
            reply.leap = 3
            reply.orig_timestamp = request.tx_timestamp
            reply.recv_timestamp = received
            reply.tx_timestamp = ntplib.system_to_ntp_time(time.time())

            sock.sendto(reply.to_data(), address)


def measure(host):
    client = ntplib.NTPClient()
    selected = []

    for burst in range(BURSTS):
        exchanges = []

        for _ in range(EXCHANGES_PER_BURST):
            result = client.request(
                host,
                version=4,
                port=PORT,
                timeout=5,
            )

            if result.delay < 0:
                raise RuntimeError("Negative RTT: invalid measurement; rerun.")

            exchanges.append(result)

        # Keep the lowest-RTT exchange from each burst.
        selected.append(min(exchanges, key=lambda result: result.delay))

        if burst < BURSTS - 1:
            time.sleep(INTERVAL_SECONDS)

    offsets = [result.offset for result in selected]
    rtts = [result.delay for result in selected]

    mean_offset = statistics.mean(offsets)
    mean_rtt = statistics.mean(rtts)
    offset_variation = statistics.stdev(offsets)

    print(f"Selected measurements: {len(selected)}")
    print(f"Mean estimated clock offset (Pi4 - Pi3): {mean_offset * 1000:+.3f} ms")
    print(f"Mean selected RTT: {mean_rtt * 1000:.3f} ms")
    print(f"Offset variation (standard deviation): {offset_variation * 1000:.3f} ms")


if __name__ == "__main__":
    if sys.argv[1] == "server":
        try:
            serve()
        except KeyboardInterrupt:
            pass
    else:
        measure(sys.argv[1])
