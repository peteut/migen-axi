from enum import Enum
from migen import Record, DIR_S_TO_M, DIR_M_TO_S, Module

Type = Enum("Type", "single burst flush reserved")

# DMAC master, as per ARM DDI 0424D.
_layout = [
    # DMAC acknowledge bus
    ("da", [
        ("ready", 1, DIR_S_TO_M),  # Peripheral ready
        ("type", 2, DIR_M_TO_S),  # DMA request/ack type
        ("valid", 1, DIR_M_TO_S),  # DMA data valid
    ]),
    # Peripheral request bus
    ("dr", [
        ("last", 1, DIR_S_TO_M),  # Last data of DMA transfer
        ("ready", 1, DIR_M_TO_S),  # DMA ready
        ("type", 2, DIR_S_TO_M),  # Peripheral request/ack type
        ("valid", 1, DIR_S_TO_M),  # Peripheral data valid
    ]),
]


class Interface(Record):
    def __init__(self, name=None):
        super().__init__(_layout, name=name)


class InterconnectPointToPoint(Module):
    def __init__(self, master, slave):
        self.comb += master.connect(slave)
