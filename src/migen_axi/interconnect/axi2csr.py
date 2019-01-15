from operator import attrgetter
from migen import *  # noqa
from . import axi
from misoc.interconnect import csr_bus

__all__ = ["AXI2CSR"]


class AXI2CSR(Module):
    def __init__(self, bus_axi=None, bus_csr=None):
        self.bus = bus_axi or axi.Interface()
        self.csr = bus_csr or csr_bus.Interface()

        ###

        dw = len(self.csr.dat_w)

        if dw not in (8, 16, 32):
            raise NotImplementedError(
                "AXI2CSR data_width shall be in (8, 16, 32)")

        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(self.bus)

        id_ = Signal(len(ar.id), reset_less=True)

        # control
        pending = Signal(reset_less=True)
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act(
            "IDLE",
            aw.ready.eq(1),
            ar.ready.eq(1),
            If(
                aw.valid,
                ar.ready.eq(0),
                NextValue(self.csr.adr, aw.addr[2:]),
                NextValue(id_, aw.id),
                NextState("WRITE"),
            ).Elif(
                ar.valid,
                NextValue(self.csr.adr, ar.addr[2:]),
                NextValue(id_, ar.id),
                NextValue(pending, 1),
                NextState("READ"),
            ),
        )
        fsm.act(
            "WRITE",
            If(
                w.valid,
                w.ready.eq(1),
                NextValue(self.csr.we, 1),
                NextState("WRITE_DONE"),
            ),
        )
        fsm.act(
            "WRITE_DONE",
            b.valid.eq(1),
            If(
                b.ready,
                NextState("IDLE")
            )
        )
        fsm.act(
            "READ",
            If(
                ~pending,
                NextState("READ_DONE"),
            )
        )
        fsm.act(
            "READ_DONE",
            r.valid.eq(1),
            If(
                r.ready,
                NextState("IDLE"),
            )
        )

        # data path
        self.comb += [
            r.id.eq(id_),
            b.id.eq(id_),
            r.resp.eq(axi.Response.okay),
            b.resp.eq(axi.Response.okay),
            r.last.eq(1),
        ]
        self.sync += [
            pending.eq(0),
            r.data.eq(self.csr.dat_r),
            self.csr.we.eq(0),
            self.csr.dat_w.eq(w.data),
        ]
