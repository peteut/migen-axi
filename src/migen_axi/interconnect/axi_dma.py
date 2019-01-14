import operator
from toolz.curried import *  # noqa
from migen import *  # noqa
from misoc.interconnect import stream
import ramda as R
from .axi import rec_layout, Burst, connect_source_hdshk, burst_size


__all__ = ["Reader", "Writer"]


BURST_LENGTH = 16


class Counter(Module):
    def __init__(self, t):
        self.ce = Signal()
        self.done = Signal()
        self.running = Signal()

        ###

        count = Signal(bits_for(t), reset=t)
        self.comb += self.done.eq(count == 0)
        self.sync += [
            If(
                self.ce,
                If(
                    ~self.done,
                    count.eq(count - 1),
                    self.running.eq(1)
                ).Else(
                    count.eq(count.reset),
                    self.running.eq(0)
                )
            )
        ]


class Countdown(Module):
    def __init__(self, t):
        self.ce = Signal()
        self.done = Signal()
        self.we = Signal()
        self.count_w = Signal(bits_for(t))

        ###

        count = Signal(bits_for(t))
        self.comb += self.done.eq(count == 0)
        self.sync += [
            If(
                self.we,
                count.eq(self.count_w)
            ).Elif(
                self.ce & ~self.done,
                count.eq(count - 1),
            )
        ]


# FIXME: Reader shall allow for a configurable source data width,
# and the sink shall provide an length filed to specify how many
# words shall be pushed to the source. Stick to burst access only, discard
# excess data if needed.
# Unaligned access is not needed (yet).
#
# Stall ar request until rfifo is empty, to prevent stalling during
# bus acceess.


class Reader(Module):
    def __init__(self, bus, nbits_source=None, fifo_depth=None):
        ar, r = operator.attrgetter("ar", "r")(bus)
        dw = bus.data_width
        alignment_bits = bits_for(dw // 8) - 1
        if nbits_source:
            if nbits_source % 8:
                raise ValueError("nbits_source must be a multiple of 8")
            if nbits_source > dw:
                raise ValueError("nbits_source must be <= bus.data_width")
        nbits_source = nbits_source or dw
        counter_bits = bits_for(
            (2**len(bus.ar.addr) - 1) // (nbits_source // 8))
        self.sink = stream.Endpoint(
            pipe(
                rec_layout(ar, {"addr"}),
                juxt([
                    identity,
                    R.always([("n", counter_bits)]),
                ]),
                concat, list))
        self.source = stream.Endpoint([("data", nbits_source)])

        ###

        sink_consume = Signal()
        self.comb += sink_consume.eq(self.sink.stb & self.sink.ack)
        remaining = Countdown(counter_bits)
        self.submodules += remaining
        self.comb += [
            remaining.count_w.eq(self.sink.n),
            remaining.we.eq(sink_consume),
            remaining.ce.eq(self.source.stb & self.source.ack),
        ]
        eop_consumed = Signal()
        self.sync += [
            If(
                sink_consume,
                eop_consumed.eq(0),
            ).Elif(
                self.source.stb & self.source.ack & self.source.eop,
                eop_consumed.eq(1)
            )
        ]
        converter = stream.Converter(dw, nbits_source)
        self.submodules += converter
        self.comb += [
            converter.source.ack.eq(self.source.ack | eop_consumed),
            self.source.stb.eq(converter.source.stb & ~eop_consumed),
            self.source.eop.eq(remaining.done),
            self.source.data.eq(converter.source.data),
        ]
        fifo_depth = min(fifo_depth or BURST_LENGTH, BURST_LENGTH)
        if fifo_depth % (dw // 8):
            raise ValueError("fifo_depth shall be a multiple of wordsize")
        rfifo = stream.SyncFIFO(rec_layout(r, {"data"}), depth=fifo_depth)
        self.submodules += rfifo
        self.comb += rfifo.source.connect(converter.sink)

        burst_done = Signal()
        self.sync += burst_done.eq(r.valid & r.ready & r.last)
        # ar channel
        ar_acked = Signal(reset=1)
        sink_acked = Signal()
        self.sync += [
            If(
                sink_consume,
                sink_acked.eq(1)
            ).Elif(
                remaining.done,
                sink_acked.eq(0)
            )
        ]

        self.sync += [
            If(
                sink_consume,
                ar_acked.eq(0),
                ar.addr[alignment_bits:].eq(self.sink.addr[alignment_bits:]),
            ).Else(
                If(
                    burst_done & ~remaining.done,
                    ar_acked.eq(0),
                    ar.addr.eq(ar.addr + fifo_depth * dw // 8)
                ),
                If(
                    ar.valid & ar.ready,
                    ar_acked.eq(1)
                )
            ),
        ]
        self.comb += [
            self.sink.ack.eq(~sink_acked & remaining.done),
            ar.len.eq(fifo_depth - 1),
            ar.size.eq(burst_size(dw // 8)),
            ar.burst.eq(Burst.incr.value),
            # ensure FIFO is clear to not stall the bus
            ar.valid.eq(~ar_acked & ~rfifo.source.stb)
        ]
        # r channel
        self.comb += [
            remaining.ce.eq(rfifo.sink.stb & rfifo.sink.ack),
            rfifo.sink.data.eq(r.data),
            rfifo.sink.stb.eq(r.valid),
            r.ready.eq(rfifo.sink.ack),
        ]


class Writer(Module):
    def __init__(self, bus, fifo_depth=None):
        aw, w, b = operator.attrgetter("aw", "w", "b")(bus)
        self.sink = stream.Endpoint(
            rec_layout(aw, {"addr"}) + rec_layout(w, {"data"}))

        ###

        dw = bus.data_width
        alignment_bits = bits_for(dw // 8) - 1
        fifo_depth = min(fifo_depth or BURST_LENGTH, BURST_LENGTH)
        self.submodules.burst_cnt = Counter(fifo_depth - 1)
        sink_consume = Signal()
        self.comb += sink_consume.eq(self.sink.stb & self.sink.ack)
        sof = Signal(reset=1)
        # aw channel
        aw_acked = Signal()
        self.sync += [
            If(
                sink_consume,
                sof.eq(self.sink.eop),
                If(
                    sof,
                    aw.addr[alignment_bits:].eq(
                        self.sink.addr[alignment_bits:])
                ).Elif(
                    self.burst_cnt.done & aw_acked,
                    aw.addr.eq(aw.addr + fifo_depth * dw // 8)
                )
            )
        ]
        self.comb += [
            aw.len.eq(fifo_depth - 1),
            aw.size.eq(burst_size(dw // 8)),
            aw.burst.eq(Burst.incr.value),
        ]
        self.sync += [
            If(
                aw.valid & aw.ready,
                aw.valid.eq(0), aw_acked.eq(1)
            ).Elif(
                sink_consume & ~aw_acked,
                aw.valid.eq(1)
            )
        ]
        # w channel
        wfifo = stream.SyncFIFO(rec_layout(w, {"data"}), depth=fifo_depth)
        self.submodules += wfifo
        self.comb += [
            If(
                self.sink.eop,
                If(
                    b.valid & b.ready,
                    self.sink.ack.eq(1)
                )
            ).Else(
                self.sink.ack.eq(wfifo.sink.ack)
            )
        ]
        self.comb += [
            wfifo.sink.stb.eq(
                self.sink.stb &
                (~self.sink.eop |
                 (self.sink.eop & self.burst_cnt.running))),
            self.burst_cnt.ce.eq(wfifo.sink.stb & wfifo.sink.ack),
            wfifo.sink.eop.eq(self.burst_cnt.done),
            wfifo.sink.data.eq(self.sink.data),
        ]
        self.comb += [
            w.data.eq(wfifo.source.data),
            w.strb.eq(2 ** (dw // 8) - 1),
            w.last.eq(wfifo.source.eop),
        ]
        self.comb += connect_source_hdshk(w, wfifo.source)
        # b channel
        self.sync += [
            If(
                b.ready & b.valid,
                b.ready.eq(0), aw_acked.eq(0),
            ).Elif(
                reduce(operator.and_, [w.last, w.valid, w.ready]),
                b.ready.eq(1)
            )
        ]
