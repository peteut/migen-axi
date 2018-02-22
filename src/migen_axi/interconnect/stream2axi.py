from operator import attrgetter, or_
from migen import *  # noqa
from migen.genlib.fifo import SyncFIFO
from misoc.interconnect import stream
from misoc.interconnect.csr import AutoCSR, CSRStatus
from . import dmac_bus
from . import axi
from .axi import rec_layout

BURST_LENGTH = 16
DMAC_LATENCY = 2


class _ReadRequester(Module, AutoCSR):
    def __init__(self, bus):
        self.burst_request = Signal()
        self._status = CSRStatus(3)

        ###

        dr, da = attrgetter("dr", "da")(bus)
        burst_type = dmac_bus.Type.burst.value
        flush_type = dmac_bus.Type.flush.value

        self.comb += [
            self._status.status[0].eq(self.burst_request),
        ]

        # control
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act(
            "IDLE",
            self._status.status[1].eq(1),
            If(
                da.valid & (da.type == flush_type),
                NextState("ACK_FLUSH"),
            ).Elif(
                self.burst_request,
                dr.valid.eq(1),
                dr.type.eq(burst_type),
                If(
                    dr.ready,
                    NextState("READ"),
                ),
            ),
        )
        fsm.act(
            "ACK_FLUSH",
            dr.valid.eq(1),
            dr.type.eq(flush_type),
            If(
                dr.ready,
                NextState("IDLE"),
            )
        )
        fsm.act(
            "READ",
            self._status.status[2].eq(1),
            If(
                da.valid & (da.type == burst_type),
                NextState("IDLE"),
            ).Elif(
                da.valid & (da.type == flush_type),
                NextState("ACK_FLUSH"),
            )
        )
        self.comb += [
            da.ready.eq(1),
        ]


class Writer(Module, AutoCSR):
    def __init__(self, bus, bus_dmac, fifo_depth=None):
        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(bus)
        dw = bus.data_width
        self.sink = stream.Endpoint(rec_layout(r, {"data"}))
        self.busy = Signal()

        ###

        self.submodules.requester = requester = _ReadRequester(bus_dmac)

        fifo_depth = fifo_depth or BURST_LENGTH + DMAC_LATENCY
        if fifo_depth < BURST_LENGTH:
            raise ValueError("fifo_depth shall be ge BURST_LENGTH")
        try:
            log2_int(BURST_LENGTH)
        except ValueError:
            raise ValueError("BURST_LENGTH shall be a power of 2")

        fifo = SyncFIFO(dw, fifo_depth)
        self.submodules += fifo

        self.comb += [
            requester.burst_request.eq(
                reduce(or_, fifo.level[len(wrap(BURST_LENGTH - 1)):])),
            self.sink.ack.eq(fifo.writable),
            fifo.we.eq(self.sink.stb),
            fifo.din.eq(self.sink.data),
        ]

        self.comb += [
            r.data.eq(fifo.dout),
            self.busy.eq(fifo.readable),
        ]

        # AXI Slave, ignore write access
        id_ = Signal(len(ar), reset_less=True)
        cnt = Signal(max=15, reset_less=True)
        cnt_dec = Signal(len(cnt))

        # control
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act(
            "IDLE",
            aw.ready.eq(1),
            ar.ready.eq(1),
            If(
                aw.valid,
                ar.ready.eq(0),
                NextValue(id_, aw.id),
                NextState("WRITE"),
            ).Elif(
                ar.valid,
                NextValue(id_, ar.id),
                NextValue(cnt, ar.len),
                NextState("READ"),
            )
        )
        fsm.act(
            "WRITE",
            w.ready.eq(1),
            # ignored
            If(
                w.valid & w.last,
                NextState("WRITE_DONE"),
            )
        )
        fsm.act(
            "WRITE_DONE",
            b.valid.eq(1),
            If(
                b.ready,
                NextState("IDLE"),
            )
        )
        fsm.act(
            "READ",
            r.valid.eq(1),
            If(
                cnt == 0,
                r.last.eq(1),
                If(
                    r.ready,
                    NextState("IDLE"),
                ).Else(
                    NextState("READ_DONE"),
                )
            ).Elif(
                r.ready,
                NextValue(cnt, cnt_dec),
            )
        )
        fsm.act(
            "READ_DONE",
            r.valid.eq(1),
            r.last.eq(1),
            If(
                r.ready,
                NextState("IDLE"),
            )
        )
        self.comb += [
            cnt_dec.eq(cnt - 1),
        ]

        # data path
        self.comb += [
            r.last.eq(cnt == 0),
            r.id.eq(id_),
            b.id.eq(id_),
            r.resp.eq(axi.Response.okay.value),
            b.resp.eq(axi.Response.okay.value),
            r.data.eq(fifo.dout),
            fifo.re.eq(r.valid & r.ready),
        ]
