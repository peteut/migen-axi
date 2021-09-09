from operator import attrgetter
from migen import *  # noqa
from . import axi
from misoc.interconnect import csr_bus

__all__ = ["AXI2CSR"]


class AXI2CSR(Module):
    def __init__(self, bus_axi=None, bus_csr=None, addr_extension=4):
        self.bus = bus_axi or axi.Interface()
        self.csr = bus_csr or csr_bus.Interface()


        # internal bus that will connect to address decoder
        # needs to be wider than CSR bus to accommodate both bus and any SRAM
        self.internal_csr = csr_bus.Interface(
            data_width=len(self.csr.dat_w), address_width=len(self.csr.adr)+addr_extension)

        # slave list to add to address decoder at the end 
        # csr bus is the first slave
        self.slaves = [(lambda a: a[len(self.csr.adr):] == 0, self.csr)]
        
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
                NextValue(self.internal_csr.adr, aw.addr[2:]),
                NextValue(id_, aw.id),
                NextState("WRITE"),
            ).Elif(
                ar.valid,
                NextValue(self.internal_csr.adr, ar.addr[2:]),
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
                NextValue(self.internal_csr.we, 1),
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
            r.data.eq(self.internal_csr.dat_r),
            self.internal_csr.we.eq(0),
            self.internal_csr.dat_w.eq(w.data),
        ]

    def add_slave(self, fun, slave):
        # fun - function that takes the address signal and returns a FHDL expression
        #       that evaluates to 1 when the slave is selected and 0 otherwise.
        # slave - Memory.port or csr bus reference.
        self.slaves += [(fun, slave)]

    def do_finalize(self):
        decoder = AddressDecoder(self.internal_csr, self.slaves, register=True)
        self.submodules += [decoder]


class AddressDecoder(Module):
    # slaves is a list of pairs:
    # 0) function that takes the address signal and returns a FHDL expression
    #    that evaluates to 1 when the slave is selected and 0 otherwise.
    # 1) Memory.port or csr bus reference.
    # register adds flip-flops after the address comparators. Improves timing,
    # but breaks Wishbone combinatorial feedback.
    def __init__(self, master, slaves, register=True):
        ns = len(slaves)
        slave_sel = Signal(ns)
        self.slave_sel_r = Signal(ns)

        ###

        # decode slave addresses
        self.comb += [slave_sel[i].eq(fn(master.adr))
                      for i, (fn, _) in enumerate(slaves)]
        if register:
            self.sync += self.slave_sel_r.eq(slave_sel)
        else:
            self.comb += self.slave_sel_r.eq(slave_sel)

        # connect master->slaves signals except we
        for _, slave in slaves:
            for dest, source in [(getattr(slave, name),
                                  getattr(master, name)) for
                                 name, _, direction in master.layout
                                 if direction == DIR_M_TO_S and name != "we"]:
                self.comb += dest.eq(source)

        # combine we with slave selection signals
        self.comb += [slave[1].we.eq(master.we & slave_sel) 
            for _, slave in enumerate(slaves)]

        # mux (1-hot) slave data return
        masked = [Replicate(self.slave_sel_r[i], len(master.dat_r)) & slaves[i][1].dat_r for i in range(ns)]
        self.comb += master.dat_r.eq(reduce(or_, masked))