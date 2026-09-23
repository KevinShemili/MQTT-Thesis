# One measured repetition of the complete MQTT workload
class MacroCase:

    def __init__(self, repetition: int):
        self.repetition = repetition
        self.publisher_cycles: int = 0
        self.subscriber_cycles: int = 0
        self.publisher_timestamps: dict[str, int] = {}
        self.subscriber_timestamps: dict[str, int] = {}
