from enum import Enum
from migen import Record, DIR_S_TO_M, DIR_M_TO_S, Module
from .axi import write_ack, read_attrs

__all__ = ["Type", "Interface", "InterconnectPointToPoint"]

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

    def write_da(self, type_):
        yield self.da.type.eq(type_)
        yield from write_ack(self.da)

    def read_da(self):
        return read_attrs(self.da)

    def write_dr(self, type_):
        yield self.dr.eq(type_)
        yield from write_ack(self.dr)

    def read_dr(self):
        return read_attrs(self.dr)


class InterconnectPointToPoint(Module):
    def __init__(self, master, slave):
        self.comb += master.connect(slave)
