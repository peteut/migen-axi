from operator import attrgetter
from toolz.curried import *  # noqa
from migen import *  # noqa
from . import axi
from misoc.interconnect import csr_bus

__all__ = ["AXI2CSR"]


class AXI2CSR(Module):
    def __init__(self, bus_axi=None, bus_csr=None):
        self.bus = bus_axi or axi.Interface()
        self.csr = bus_csr or csr_bus.Interface()

        ###

        if len(self.csr.dat_w) != 8:
            raise NotImplementedError(
                "AXI2CSR is currently only implemented for data_width = 8")

        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(self.bus)

        id_ = Signal(len(ar.id), reset_less=True)

        # control
        adr_next = Signal(2, reset_less=True)
        adr_incr = Signal(2, reset_less=True)
        pending = Signal(reset_less=True)
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act(
            "IDLE",
            aw.ready.eq(1),
            ar.ready.eq(1),
            If(
                aw.valid,
                ar.ready.eq(0),
                NextValue(self.csr.adr, aw.addr),
                NextValue(id_, aw.id),
                NextValue(pending, 1),
                NextState("WRITE"),
            ).Elif(
                ar.valid,
                NextValue(self.csr.adr, ar.addr),
                NextValue(id_, ar.id),
                NextValue(pending, 1),
                NextState("READ"),
            ),
        )
        fsm.act(
            "WRITE",
            If(
                w.valid,
                If(
                    ~pending,
                    adr_next.eq(adr_incr),
                ),
                If(
                    adr_next == 3,
                    w.ready.eq(1),
                    NextState("WRITE_DONE"),
                ),
            )
            .Else(
                NextValue(pending, 1),
            )
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
                If(
                    self.csr.adr[:2] == 3,
                    NextState("READ_DONE"),
                )
                .Else(
                    NextValue(pending, 1),
                    adr_next.eq(adr_incr),
                )
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
        write_state = fsm.ongoing("WRITE")
        read_state = fsm.ongoing("READ")
        self.comb += [
            adr_incr.eq(self.csr.adr[:2] + 1),
            adr_next.eq(self.csr.adr[:2]),
            r.id.eq(id_),
            b.id.eq(id_),
            r.resp.eq(axi.Response.okay.value),
            b.resp.eq(axi.Response.okay.value),
            r.last.eq(1),
        ]
        self.sync += [
            pending.eq(0),
            self.csr.we.eq(0),
            self.csr.adr[:2].eq(adr_next),
            If(
                write_state,
                Case(
                    adr_next,
                    dict([(i, self.csr.dat_w.eq(
                        w.data[i * 8: i * 8 + 8])) for i in range(4)])
                ),
                Case(
                    adr_next,
                    dict([(i, self.csr.we.eq(w.strb[i])) for i in range(4)])
                ),
            ),
            If(
                read_state,
                Case(
                    self.csr.adr[:2],
                    dict([(i, r.data[i * 8: i * 8 + 8].eq(
                        self.csr.dat_r)) for i in range(4)])
                )
            ),
        ]
