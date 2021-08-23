from operator import attrgetter
from migen import *  # noqa
from . import axi

__all__ = ["SRAM"]


class SRAM(Module):
    def __init__(self, mem_or_size, read_only=False, init=None, bus=None):

        # SRAM initialisation

        if bus is None:
            bus = axi.Interface()
        self.bus = bus
        bus_data_width = len(self.bus.r.data)
        if isinstance(mem_or_size, Memory):
            assert(mem_or_size.width <= bus_data_width)
            self.mem = mem_or_size
        else:
            self.mem = Memory(bus_data_width,
                              mem_or_size // (bus_data_width // 8),
                              init=init
                              )

        # memory
        port = self.mem.get_port(write_capable=not read_only, we_granularity=8)
        self.port = port
        self.specials += self.mem, port

        # # #

        ar, aw, w, r, b = attrgetter("ar", "aw", "w", "r", "b")(bus)

        id_ = Signal(len(ar.id), reset_less=True)

        writing = Signal()

        dout_index = Signal.like(ar.len)

        # todo: add support for bursts
        # self.r_addr_incr = axi.Incr(ar)
        # self.w_addr_incr = axi.Incr(aw)

        # # # Read

        self.comb += [
            r.data.eq(port.dat_r),
            r.id.eq(id_),
            r.resp.eq(axi.Response.okay),
        ]

        # read control
        self.submodules.read_fsm = read_fsm = FSM(reset_state="IDLE")
        read_fsm.act(
            "IDLE",
            r.valid.eq(0),
            If(
                ar.valid & ~writing,
                NextValue(port.adr, ar.addr[2:]),
                NextValue(dout_index, 0),
                NextValue(ar.ready, 1),
                NextValue(id_, ar.id),
                NextState("READ_WAIT"),
            )
        )

        read_fsm.act(
            "READ_WAIT",  # need this state to wait one cycle for data
            NextValue(ar.ready, 0),
            NextState("READ")
        )

        read_fsm.act(
            "READ",
            r.valid.eq(1),
            r.last.eq(r.valid & dout_index == ar.len),
            If(
                r.last & r.ready,
                If(  # ar valid? go straight to the next read
                    ar.valid & ~writing,
                    NextValue(port.adr, ar.addr[2:]),
                    NextValue(dout_index, 0),
                    NextValue(ar.ready, 1),
                    NextValue(id_, ar.id),
                    NextState("READ_WAIT"),
                ).Else(
                    NextState("IDLE")
                )
            )
        )

        self.sync += [
            If(
                r.ready & r.valid,
                dout_index.eq(dout_index + 1),
            )
        ]

        # # # Write

        if not read_only:
            self.comb += [
                port.dat_w.eq(w.data),
                b.id.eq(id_),
                b.resp.eq(axi.Response.okay),
            ]

            self.submodules.write_fsm = write_fsm = FSM(reset_state="IDLE")
            write_fsm.act(
                "IDLE",
                w.ready.eq(0),
                If(
                    aw.valid,
                    NextValue(aw.ready, 1),
                    NextValue(id_, aw.id),
                    NextValue(writing, 1),
                    If(
                        w.valid,  # skip a state if data is ready already
                        NextValue(port.adr, aw.addr[2:]),
                        NextState("WRITE"),
                    ).Else(
                        NextState("AW_VALID_WAIT")
                    )
                )
            )

            write_fsm.act(
                "AW_VALID_WAIT",  # wait for data, if not available yet
                If(
                    w.valid,
                    NextValue(port.adr, aw.addr[2:]),
                    NextState("WRITE"),
                )
            )

            write_fsm.act(
                "WRITE",
                NextValue(aw.ready, 0),
                w.ready.eq(1),
                port.we.eq(w.strb),
                If(
                    w.ready & w.last,
                    NextValue(writing, 0),
                    NextState("WRITE_RESP")
                )
            )

            write_fsm.act(
                "WRITE_RESP",
                b.valid.eq(1),
                If(
                    b.ready,
                    If(  # aw valid? go straight for the next write
                        aw.valid,
                        NextValue(aw.ready, 1),
                        NextValue(id_, aw.id),
                        NextValue(writing, 1),
                        If(
                            w.valid,
                            NextValue(port.adr, aw.addr[2:]),
                            NextState("WRITE"),
                        ).Else(
                            NextState("AW_VALID_WAIT")
                        )
                    ).Else(
                        NextState("IDLE")
                    )
                )
            )
