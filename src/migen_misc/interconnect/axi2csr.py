from operator import attrgetter, and_
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

        dw = len(self.csr.dat_w)

        if dw not in (8, 16):
            raise NotImplementedError(
                "AXI2CSR is currently only implemented for dw of 8 or 16")

        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(self.bus)

        id_ = Signal(len(ar.id), reset_less=True)

        # control
        adr_next = Signal(2, reset_less=True)
        adr_incr = Signal(2, reset_less=True)
        pending = Signal(reset_less=True)
        pending_next = Signal()
        self.comb += pending_next.eq(0)
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
                pending_next.eq(1),
                NextState("WRITE"),
            ).Elif(
                ar.valid,
                NextValue(self.csr.adr, ar.addr),
                NextValue(id_, ar.id),
                pending_next.eq(1),
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
                    reduce(and_, adr_next[dw // 8 - 1:]),
                    w.ready.eq(1),
                    NextState("WRITE_DONE"),
                ),
            )
            .Else(
                pending_next.eq(1),
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
                    reduce(and_, self.csr.adr[dw // 8 - 1:2]),
                    NextState("READ_DONE"),
                )
                .Else(
                    pending_next.eq(1),
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
            adr_incr.eq(
                (self.csr.adr[dw // 8 - 1:2] + 1) << (dw // 8 - 1)),
            adr_next.eq(self.csr.adr[:2]),
            r.id.eq(id_),
            b.id.eq(id_),
            r.resp.eq(axi.Response.okay.value),
            b.resp.eq(axi.Response.okay.value),
            r.last.eq(1),
        ]
        self.sync += [
            pending.eq(pending_next),
            self.csr.we.eq(0),
            self.csr.adr[:2].eq(adr_next),
            If(
                write_state,
                Case(
                    adr_next[dw // 8 - 1:],
                    dict([(i, self.csr.dat_w.eq(
                        w.data[i * dw:i * dw + dw]))
                        for i in range(32 // dw)])
                ),
                Case(
                    adr_next[dw // 8 - 1:],
                    dict([(i, self.csr.we.eq(w.strb[i]))
                          for i in range(32 // dw)])
                ),
            ),
            If(
                ~pending & read_state,
                Case(
                    self.csr.adr[dw // 8 - 1:2],
                    dict([(i, r.data[i * dw:i * dw + dw].eq(
                        self.csr.dat_r)) for i in range(32 // dw)])
                )
            ),
        ]
