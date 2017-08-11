from operator import attrgetter
from toolz.curried import *  # noqa
from migen import *  # noqa
from . import axi
from misoc.interconnect import csr_bus, stream

__all__ = ["AXI2CSR"]


expand_strb = comp(Cat, map(flip(Replicate, 8)), concat)


class AXI2CSR(Module):
    def __init__(self, bus_axi=None, bus_csr=None, depth=4):
        self.bus = bus_axi or axi.Interface()
        self.csr = bus_csr or csr_bus.Interface()

        need_wstrb = (len(self.csr.dat_r) // 8) > 1

        ###

        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(self.bus)
        FIFO = partial(stream.SyncFIFO, depth=depth)

        self.submodules.arfifo = FIFO(axi.rec_layout(ar, {"addr", "id"}))
        self.comb += axi.connect_sink_hdshk(ar, self.arfifo.sink)
        self.comb += [
            self.arfifo.sink.addr.eq(ar.addr), self.arfifo.sink.id.eq(ar.id),
        ]
        self.submodules.awfifo = FIFO(axi.rec_layout(aw, {"addr", "id"}))
        self.comb += axi.connect_sink_hdshk(aw, self.awfifo.sink)
        self.comb += [
            self.awfifo.sink.addr.eq(aw.addr), self.awfifo.sink.id.eq(aw.id),
        ]
        self.submodules.wfifo = FIFO(axi.rec_layout(w, {"data", "strb"}))
        self.comb += axi.connect_sink_hdshk(w, self.wfifo.sink)
        self.comb += [
            # mask strobe
            self.wfifo.sink.data.eq(w.data & expand_strb(w.strb)),
            self.wfifo.sink.strb.eq(w.strb),
        ]
        self.submodules.rfifo = FIFO(axi.rec_layout(r, {"data", "id"}))
        self.comb += axi.connect_source_hdshk(r, self.rfifo.source)
        self.comb += [
            self.rfifo.sink.id.eq(self.arfifo.source.id),
            self.rfifo.sink.data.eq(self.csr.dat_r),
            r.id.eq(self.rfifo.source.id),
            r.data.eq(self.rfifo.source.data),
        ]
        self.submodules.bfifo = FIFO(axi.rec_layout(b, {"id"}))
        self.comb += axi.connect_source_hdshk(b, self.bfifo.source)
        self.comb += [
            self.bfifo.sink.id.eq(self.awfifo.source.id),
            b.id.eq(self.bfifo.source.id),
        ]
        self.sync += [
            self.csr.we.eq(0),
            self.rfifo.sink.stb.eq(0),
            If(
                self.arfifo.source.stb,
                self.csr.adr.eq(self.arfifo.source.addr),
            ).Elif(
                self.awfifo.source.stb,
                self.csr.adr.eq(self.awfifo.source.addr),
            ),
        ]
        if need_wstrb:
            self.sync += self.csr.dat_w.eq(
                self.wfifo.source.data |
                (expand_strb(~ self.wfifo.source.strb) & self.csr.dat_r))
        else:
            self.sync += self.csr.dat_w.eq(self.wfifo.source.data)

        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act(
            "IDLE",
            If(
                self.arfifo.source.stb & self.rfifo.sink.ack,
                NextState("READ")
            ).Elif(
                self.awfifo.source.stb & self.bfifo.sink.ack &
                self.bfifo.sink.ack,
                [NextValue(self.csr.we, 1), NextState("WRITE")]
                if not need_wstrb else
                [NextState("READ_MODIFY_WRITE")]
            )
        )
        fsm.act(
            "READ",
            If(
                self.rfifo.sink.stb,
                NextState("IDLE")
            )
            .Else(
                NextValue(self.rfifo.sink.stb, 1)
            )
        )
        if need_wstrb:
            fsm.act(
                "READ_MODIFY_WRITE",
                NextState("WRITE"),
                NextValue(self.csr.we, 1)
            )
        fsm.act(
            "WRITE",
            If(
                self.wfifo.source.stb,
                NextState("IDLE"),
            ),
            self.awfifo.source.ack.eq(1),
            self.wfifo.source.ack.eq(1),
            self.bfifo.sink.stb.eq(1)
        )
        self.comb += [
            r.last.eq(1), w.last.eq(1),
            r.resp.eq(axi.Response.okay.value),
            b.resp.eq(axi.Response.okay.value),

            self.arfifo.source.ack.eq(self.rfifo.sink.stb),
        ]
