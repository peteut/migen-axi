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


@ResetInserter()
class _ReadRequester(Module, AutoCSR):
    """
    Peripheral Request Interface read requester.

    Attributes
    ----------
    burst_request : migen.Signal
        Request burst read.
    _status : misoc.interconnect.csr.CSRStatus
        - [0] burst_request
        - [4] IDLE onging
        - [5] READ onging
        - [8:11] last valid da.type
    """
    def __init__(self, bus):
        self.burst_request = Signal()
        self._status = CSRStatus(10)

        ###

        dr, da = attrgetter("dr", "da")(bus)
        burst_type = dmac_bus.Type.burst
        flush_type = dmac_bus.Type.flush

        # control
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act(
            "IDLE",
            If(
                da.valid & (da.type == flush_type),
                NextState("ACK_FLUSH"),
            ).Elif(
                self.burst_request,
                dr.valid.eq(1),
                dr.type.eq(burst_type),
                If(
                    dr.ready, NextState("READ"),
                ),
            ),
        )
        fsm.act(
            "ACK_FLUSH",
            dr.valid.eq(1),
            dr.type.eq(flush_type),
            If(
                dr.ready, NextState("IDLE"),
            )
        )
        fsm.act(
            "READ",
            If(
                da.valid,
                If(
                    da.type == flush_type, NextState("ACK_FLUSH"),
                ).Elif(
                    da.type == burst_type, NextState("IDLE"),
                )
            )
        )
        da_type = Signal(len(da.type), reset=0x3)
        self.sync += If(da.valid, da_type.eq(da.type))
        self.comb += [
            da.ready.eq(1),
            self._status.status.eq(Cat(
                self.burst_request, C(0, (3, False)),
                fsm.ongoing("IDLE"), fsm.ongoing("READ"), C(0, (2, False)),
                da_type)),
        ]


class Writer(Module, AutoCSR):
    """
    Stream to AXI interface via ARM CoreLink DMA-330 DMA Controller.

    Parameters
    ----------
    bus : migen_axi.interconnect.axi.Interface
    bus_dmac : migen_axi.interconnect.dmac_bus.Interface
    fifo_depth: int, optional

    Attributes
    ----------
    sink : misoc.interconnect.stream.Endpoint
    busy : migen.Signal
        Data to write pending.
    dma_reset : migen.Signal
        Reset Peripheral Request Interface.
    """
    def __init__(self, bus, bus_dmac, fifo_depth=None):
        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(bus)
        dw = bus.data_width
        self.sink = stream.Endpoint(rec_layout(r, {"data"}))
        self.busy = Signal()
        self.dma_reset = Signal()

        ###

        self.submodules.requester = requester = _ReadRequester(bus_dmac)
        self.comb += requester.reset.eq(self.dma_reset)

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
        id_ = Signal(bus.id_width, reset_less=True)
        id_next = Signal(len(id_))
        cnt = Signal(max=15, reset_less=True)
        cnt_next = Signal(len(cnt))
        self.comb += [
            id_next.eq(id_),
            cnt_next.eq(cnt),
        ]
        self.sync += [
            id_.eq(id_next),
            cnt.eq(cnt_next),
        ]
        # control
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act(
            "IDLE",
            aw.ready.eq(1),
            ar.ready.eq(1),
            If(
                aw.valid,
                ar.ready.eq(0),
                id_next.eq(aw.id),
                NextState("WRITE"),
            ).Elif(
                ar.valid,
                id_next.eq(ar.id),
                cnt_next.eq(ar.len),
                NextState("READ"),
            )
        )
        fsm.act(
            "WRITE",
            w.ready.eq(1),
            # ignored
            If(
                w.valid & w.last, NextState("WRITE_DONE"),
            )
        )
        fsm.act(
            "WRITE_DONE",
            b.valid.eq(1),
            If(
                b.ready, NextState("IDLE"),
            )
        )
        fsm.act(
            "READ",
            r.valid.eq(1),
            If(
                cnt == 0,
                r.last.eq(1),
                If(
                    r.ready, NextState("IDLE"),
                ).Else(
                    NextState("READ_DONE"),
                )
            ).Elif(
                r.ready, cnt_next.eq(cnt - 1),
            )
        )
        fsm.act(
            "READ_DONE",
            r.valid.eq(1),
            r.last.eq(1),
            If(
                r.ready, NextState("IDLE"),
            )
        )
        # data path
        self.comb += [
            r.last.eq(cnt == 0),
            r.id.eq(id_),
            b.id.eq(id_),
            r.resp.eq(axi.Response.okay),
            b.resp.eq(axi.Response.okay),
            r.data.eq(fifo.dout),
            fifo.re.eq(r.valid & r.ready),
        ]
