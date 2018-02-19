from operator import attrgetter
from migen import *  # noqa
from . import dmac_bus

BURST_LENGTH = 16
DMAC_LATENCY = 2


class _ReadRequester(Module):
    def __init__(self, bus):
        self.burst_request = Signal()

        ###

        dr, da = attrgetter("dr", "da")(bus)
        burst_type = dmac_bus.Type.burst.value
        flush_type = dmac_bus.Type.flush.value

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
