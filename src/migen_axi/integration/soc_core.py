from types import SimpleNamespace
from migen import *  # noqa
from misoc.cores import identifier
from misoc.integration.wb_slaves import WishboneSlaveManager as SlaveManager
from misoc.interconnect import csr_bus
from ..interconnect import axi, axi2csr
from ..cores import ps7


def interrupt2irq_id(idx):
    if irqf2p_idx < 8:
        return 68 - idx
    else:
        return 91 - idx


class SoCCore(Module):
    mem_map = dict(
        axi=0x40000000,  # m_axi_gp0
        csr=0x80000000,  # m_axi_gp1
    )

    def __init__(self, platform,
                 csr_data_width=8,
                 csr_address_width=14,
                 max_addr=0xc0000000,
                 ident="SoCCore"):
        self.platform = platform
        # self.clk_freq = clk_freq

        self.csr_data_width = csr_data_width
        self.csr_address_width = csr_address_width

        self._memory_regions = []  # seq of (name, origin, length)
        self._csr_regions = []  # seq of (name, origin, busword, csr_list|Memory)  # noqa
        self._constants = []  # seq of (name, value)

        self._axi_slaves = SlaveManager(max_addr)

        self.csr_devices = [
            "identifier_mem",
        ]
        self.interrupt_devices = []

        self.submodules.ps7 = ps7.PS7(SimpleNamespace(
            ps=platform.request("ps"),
            ddr=platform.request("ddr"),
        ))

        self.submodules.axi2csr = axi2csr.AXI2CSR(
            bus_csr=csr_bus.Interface(csr_data_width, csr_address_width),
            bus_axi=axi.Interface.like(self.ps7.m_axi_gp1))

        self.register_mem("csr", self.mem_map["csr"], 4 * 2**csr_address_width,
                          self.axi2csr.bus)

        self.submodules.identifier = identifier.Identifier(ident)

    def add_axi_slave(self, origin, length, interface):
        if self.finalized:
            raise RuntimeError("{} already finalised")
        self._axi_slaves.add(origin, length, interface)

    # This function simply registers the memory region for firmware purposes
    # (linker script, generated headers)
    def add_memory_region(self, name, origin, length):
        self._memory_regions.append((name, origin, length))

    def check_csr_region(self, name, origin):
        for n, o, l, obj in self._csr_regions:
            if n == name or o == origin:
                raise ValueError(
                    "CSR region conflict between {} and {}".format(n, name))

    def add_csr_region(self, name, origin, busword, obj):
        self.check_csr_region(name, origin)
        self._csr_regions.append((name, origin, busword, obj))

    def register_mem(self, name, origin, length, interface):
        self.add_axi_slave(origin, length, interface)
        self.add_memory_region(name, origin, length)

    @property
    def memory_regions(self):
        return self._memory_regions

    @property
    def csr_regions(self):
        return self._csr_regions

    @property
    def constants(self):
        return self._constants

    def get_csr_dev_address(self, name, memory):
        if memory is not None:
            name = "_".join([name, memory.name_override])
        try:
            return self.csr_devices.index(name)
        except ValueError:
            return None

    def do_finalize(self):
        # CSR
        self.submodules.csrbankarray = csr_bus.CSRBankArray(
            self, self.get_csr_dev_address,
            data_width=self.csr_data_width,
            address_width=self.csr_address_width)

        self.submodules.csrcon = csr_bus.Interconnect(
            self.axi2csr.csr, self.csrbankarray.get_buses())

        for name, csrs, mapaddr, rmap in self.csrbankarray.banks:
            self.add_csr_region(
                name, (self.mem_map["csr"] + 0x800 * mapaddr),
                self.csr_data_width, csrs)
        for name, memory, mapaddr, mmap in self.csrbankarray.srams:
            self.add_csr_region(
                "{}_{}".format(name, memory.name_override),
                (self.mem_map["csr"] + 0x800 * mapaddr),
                self.csr_data_width, memory)
        for name, constant in self.csrbankarray.constants:
            self._constants.append(
                (("_".join([name, constant.name]).upper(),
                  constant.value.value)))

        # Interrupts
        for n, name in enumerate(self.interrupt_devices):
            self.comb += self.ps7.interrupt[n].eq(getattr(self, name).ev.irq)

        # AXI: FIXME: add InterconnectShared support
        slaves = self._axi_slaves.get_interconnect_slaves()
        if len(slaves) > 2:
            raise NotImplementedError("only P2P is supported")
        self.submodules += axi.InterconnectPointToPoint(
            self.ps7.m_axi_gp1, slaves[0][1])
        if len(slaves) == 2:
            self.submodules += axi.InterconnectPointToPoint(
                self.ps7.m_axi_gp0, slaves[1][1])

    def build(self, *args, **kwargs):
        self.platform.build(self, *args, **kwargs)
