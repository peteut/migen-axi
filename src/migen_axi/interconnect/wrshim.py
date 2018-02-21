from operator import and_
from toolz.curried import *  # noqa
from migen import *  # noqa
from ..interconnect import Interface


__all__ = ["AxiWrshim"]


class AxiWrshim(Module):
    def __init__(self, id_width=6):
        self.m_axi_i = i = Interface(id_width=id_width)
        self.m_axi_o = o = Interface(id_width=id_width)

        ###

        # write command
        wlast_consumed = Signal()
        wlast_detect = Signal(reset=1)
        self.sync += \
            If(
                wlast_consumed, wlast_detect.eq(1)
            ).Elif(
                reduce(and_, [i.w.valid, o.w.ready]), wlast_detect.eq(0)
            )
        first_beat_detect = Signal()
        self.comb += first_beat_detect.eq(wlast_detect & i.w.valid)
        stall_awvalid = Signal()
        self.sync += \
            If(
                reduce(and_, [i.aw.valid, o.aw.ready, ~o.w.ready]),
                stall_awvalid.eq(1)
            ).Elif(
                o.w.ready,
                stall_awvalid.eq(0)
            )
        store_first_beat = Signal()
        self.sync += \
            If(
                first_beat_detect & ~o.aw.ready,
                store_first_beat.eq(1)
            ).Elif(
                o.aw.ready,
                store_first_beat.eq(0)
            )
        awcmd_en = Signal()
        self.comb += awcmd_en.eq((first_beat_detect & ~stall_awvalid) |
                                 store_first_beat)
        self.comb += [
            o.aw.valid.eq(i.aw.valid & awcmd_en),
            i.aw.ready.eq(o.aw.ready & awcmd_en),
        ]

        # write data
        addr_ofs = Signal(2)
        awsize = Signal(3)
        self.comb += Case(
            i.w.strb,
            thread_first(
                dict(((1 << i,
                       [awsize.eq(0), addr_ofs.eq(i)]) for i in range(4))),
                (assoc, 0b1100, [awsize.eq(1), addr_ofs.eq(2)]),
                (assoc, 0b0011, [awsize.eq(1), addr_ofs.eq(0)]),
                (assoc, "default", [awsize.eq(i.aw.size), addr_ofs.eq(0)])))
        start_wr = Signal()
        previous_cmd_done = Signal(reset=1)
        self.comb += start_wr.eq(
            reduce(and_, [wlast_detect, i.w.valid, previous_cmd_done]))
        self.comb += wlast_consumed.eq(
            reduce(and_, [i.w.valid, o.w.ready, i.w.last]))
        burst_still_active = Signal()
        self.sync += \
            If(
                start_wr & ~wlast_consumed, burst_still_active.eq(1)
            ).Elif(
                wlast_consumed, burst_still_active.eq(0)
            )
        wdata_en = Signal()
        self.comb += wdata_en.eq(burst_still_active | start_wr)
        self.sync += \
            If(
                i.aw.valid & o.aw.ready, previous_cmd_done.eq(1)
            ).Elif(
                i.aw.valid, previous_cmd_done.eq(0)
            )
        self.comb += [
            o.w.valid.eq(i.w.valid & wdata_en),
            i.w.ready.eq(o.w.ready & wdata_en),
        ]
        self.comb += [
            i.aw.connect(
                o.aw, omit=set(["valid", "ready", "addr", "size"])),
            i.w.connect(
                o.w, omit=set(["valid", "ready", "size"])),
            i.connect(o, omit=set(["aw", "w"])),
            o.aw.addr.eq(Cat(addr_ofs, i.aw.addr[2:])),
            o.aw.size.eq(awsize),
        ]
