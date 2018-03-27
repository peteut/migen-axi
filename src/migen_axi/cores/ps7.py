import operator
from types import SimpleNamespace
from toolz.curried import *  # noqa
import pyramda as R
from migen import *  # noqa
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.record import DIR_S_TO_M, DIR_M_TO_S, DIR_NONE
from ..interconnect import (Interface, InterconnectPointToPoint, dmac_bus,
                            wrshim)


__all__ = ["PS7", "ddr_rec", "enet_rec"]


@R.curry
def apply_map(fn, kwargs):
    return fn(**kwargs)


@R.curry
def str_replace(old, new, string):
    return string.replace(old, new)


sig_name = comp(
    "".join, operator.methodcaller("split", "_"),
    get_in([-1, 0]), operator.attrgetter("backtrace"))


def connect_interface(interface, ps_m=True):
    return pipe(
        interface.iter_flat(),
        map(
            juxt([
                comp(
                    R.apply(operator.concat),
                    juxt([
                        comp(
                            comp(
                                flip(get)(
                                    dict([(DIR_M_TO_S, "o_" if ps_m else "i_"),
                                          (DIR_S_TO_M, "i_" if ps_m else "o_"),
                                          (DIR_NONE, "io_")])),
                                get(-1))),
                        comp(operator.methodcaller("upper"), sig_name, first),
                    ])
                ),
                first])),
        dict)


fix_arsize = comp(
    R.apply(update_in),
    juxt([
        identity,
        comp(list, filter(flip(str.endswith, "ARSIZE"))),
        R.always(get(slice(-1))),
    ]))


fix_awsize = comp(
    R.apply(update_in),
    juxt([
        identity,
        comp(list, filter(flip(str.endswith, "AWSIZE"))),
        R.always(get(slice(-1))),
    ]))


def connect_s_axi(interface):
    return thread_first(
        interface,
        (connect_interface, False),
        fix_arsize, fix_awsize)


def connect_m_axi(interface):
    return thread_first(
        interface,
        (connect_interface, True),
        fix_arsize, fix_awsize)


axi_global_rec = partial(Record, [
    ("aclk", 1, DIR_M_TO_S),
    ("areset_n", 1, DIR_M_TO_S),
])

acp_user_rec = partial(Record, [
    ("awuser", 5, DIR_S_TO_M),
    ("aruser", 5, DIR_S_TO_M),
])

hp_fifo_rec = partial(Record, [
    ("wcount", 8, DIR_M_TO_S),
    ("wrissuecap1_en", 1, DIR_S_TO_M),
    ("wacount", 6, DIR_M_TO_S),
    ("rcount", 8, DIR_M_TO_S),
    ("racount", 3, DIR_M_TO_S),
    ("rdissuecap1_en", 1, DIR_S_TO_M),
])

ps_rec = partial(Record, [
    ("clk", 1),
    ("por_b", 1),
    ("srst_b", 1),
])

ddr_rec = partial(Record, [
    ("a", 15),
    ("ba", 3),
    ("cas_n", 1),
    ("cke", 1),
    ("ck_n", 1),
    ("ck_p", 1),
    ("cs_n", 1),
    ("dm", 4),
    ("dq", 32),
    ("dqs_n", 4),
    ("dqs_p", 4),
    ("drst_n", 1),
    ("odt", 1),
    ("ras_n", 1),
    ("vrn", 1),
    ("vrp", 1),
    ("we_n", 1),
])

enet_rec = partial(Record, [
    ("gmii", [
        ("rx_clk", 1, DIR_S_TO_M),
        ("crs", 1, DIR_S_TO_M),
        ("col", 1, DIR_S_TO_M),
        ("rxd", 8, DIR_S_TO_M),
        ("rx_dv", 1, DIR_S_TO_M),
        ("rx_er", 1, DIR_S_TO_M),
        ("tx_clk", 1, DIR_S_TO_M),
        ("txd", 8, DIR_M_TO_S),
        ("tx_en", 1, DIR_M_TO_S),
        ("tx_er", 1, DIR_M_TO_S),
    ]),
    ("mdio", [
        ("mdc", 1, DIR_M_TO_S),
        ("i", 1, DIR_S_TO_M),
        ("o", 1, DIR_M_TO_S),
        ("t_n", 1, DIR_M_TO_S),
    ]),
    ("ptp", [
        ("sync_frame_tx", 1, DIR_M_TO_S),
        ("delay_req_tx", 1, DIR_M_TO_S),
        ("pdelay_req_tx", 1, DIR_M_TO_S),
        ("pdelay_resp_tx", 1, DIR_M_TO_S),
        ("sync_frame_rx", 1, DIR_M_TO_S),
        ("delay_req_rx", 1, DIR_M_TO_S),
        ("pdelay_req_rx", 1, DIR_M_TO_S),
        ("pdelay_resp_rx", 1, DIR_M_TO_S),
    ]),
    ("sof_rx", 1, DIR_M_TO_S),
    ("sof_tx", 1, DIR_M_TO_S),
    ("ext_intin", 1, DIR_S_TO_M),
])

ttc_rec = partial(Record, [
    ("wave_o", 3, DIR_M_TO_S),
    ("clk_i", 3, DIR_S_TO_M),
])

wdt_rec = partial(Record, [
    ("clk_i", 1, DIR_S_TO_M),
    ("rst_o", 1, DIR_M_TO_S),
])


def tristate(name, n=1):
    return name, [("i", n, DIR_S_TO_M),
                  ("o", n, DIR_M_TO_S),
                  ("t_n", n, DIR_M_TO_S)]


spio_rec = partial(Record, [
    tristate("sclk"),
    tristate("m"),
    tristate("s"),
    ("ss_i_n", 1, DIR_S_TO_M),
    ("ss_t_n", 1, DIR_M_TO_S),
    ("ss_o_n", 3, DIR_M_TO_S),
])

i2c_rec = partial(Record, [
    tristate("scl"),
    tristate("sda"),
])

can_rec = partial(Record, [
    ("phy_tx", 1, DIR_M_TO_S),
    ("phy_rx", 1, DIR_S_TO_M),
])

uart_rec = partial(Record, [
    ("tx", 1, DIR_M_TO_S),
    ("rx", 1, DIR_S_TO_M),
    ("cts_n", 1, DIR_S_TO_M),
    ("rts_n", 1, DIR_M_TO_S),
    ("dsr_n", 1, DIR_S_TO_M),
    ("dcd_n", 1, DIR_S_TO_M),
    ("ri_n", 1, DIR_S_TO_M),
    ("dtr_n", 1, DIR_M_TO_S),
])

sdio_rec = partial(Record, [
    ("clk", 1, DIR_M_TO_S),
    ("clk_fb", 1, DIR_S_TO_M),
    tristate("cmd"),
    tristate("data", 4),
    ("cd_n", 1, DIR_S_TO_M),
    ("wp", 1, DIR_S_TO_M),
    ("led", 1, DIR_M_TO_S),
    ("buspow", 1, DIR_M_TO_S),
    ("busvolt", 3, DIR_M_TO_S),
])

gpio_rec = partial(Record, [
    ("i", 64, DIR_S_TO_M),
    ("o", 64, DIR_M_TO_S),
    ("t_n", 64, DIR_M_TO_S)])

trace_rec = partial(Record, [
    ("clk", 1, DIR_S_TO_M),
    ("ctl", 1, DIR_M_TO_S),
    ("data", 32, DIR_M_TO_S),
])

pjtag_rec = partial(Record, [
    ("tck", 1, DIR_S_TO_M),
    ("tms", 1, DIR_S_TO_M),
    tristate("td"),
])

usb_rec = partial(Record, [
    ("port_indctl", 2, DIR_M_TO_S),
    ("vbus", [
        ("pwrfault", 1, DIR_S_TO_M),
        ("pwrselect", 1, DIR_M_TO_S),
    ]),
])

sram_rec = partial(Record, [
    ("intin", 1, DIR_S_TO_M),
])

fclk_rec = partial(Record, [
    ("clk", 4, DIR_M_TO_S),
    ("clktrig_n", 4, DIR_S_TO_M),
    ("reset_n", 4, DIR_M_TO_S),
])

event_rec = partial(Record, [
    ("i", 1, DIR_S_TO_M),
    ("o", 1, DIR_M_TO_S),
    ("standbywfe", 2, DIR_M_TO_S),
    ("standbywfi", 2, DIR_M_TO_S),
])

ftmd_rec = partial(Record, [
    ("tracein", [
        ("data", 32, DIR_S_TO_M),
        ("valid", 1, DIR_S_TO_M),
        ("clock", 1, DIR_S_TO_M),
        ("atid", 1, DIR_S_TO_M),
    ]),
])

ftmt_rec = partial(Record, [
    ("f2p", [
        ("trig", 4, DIR_S_TO_M),
        ("trigack", 4, DIR_M_TO_S),
        ("debug", 32, DIR_S_TO_M),
    ]),
    ("p2f", [
        ("trig", 4, DIR_M_TO_S),
        ("trigack", 4, DIR_S_TO_M),
        ("debug", 32, DIR_M_TO_S),
    ]),
])

dma_global_rec = partial(Record, [
    ("aclk", 1, DIR_S_TO_M),
    ("rst_n", 1, DIR_M_TO_S),
])

irq_rec = partial(Record, [
    ("p2f", 29, DIR_M_TO_S),
    ("f2p", 20, DIR_S_TO_M),
])

bibuf = comp(
    apply_map(partial(Instance, "BIBUF")),
    dict, partial(zip, ["io_PAD", "io_IO"]))

bufg = comp(
    apply_map(partial(Instance, "BUFG")),
    dict, partial(zip, ["i_I", "o_O"]))


class ENETRx(Module):
    def __init__(self, pads, gmii):

        ###

        self.sync += [
            gmii.rxd.eq(pads.gmii.rxd),
            gmii.rx_dv.eq(pads.gmii.rx_dv),
            gmii.rx_er.eq(pads.gmii.rx_er),
        ]


class ENETTx(Module):
    def __init__(self, pads, gmii):

        ###

        self.sync += [
            pads.gmii.txd.eq(gmii.txd),
            pads.gmii.tx_en.eq(gmii.tx_en),
            pads.gmii.tx_er.eq(gmii.tx_er),
            gmii.col.eq(pads.gmii.col),
            gmii.crs.eq(pads.gmii.crs),
        ]


class ENET(Module):
    def __init__(self, pads):
        self.enet = enet_rec()

        ###

        if not pads:
            return

        self.clock_domains.cd_eth_rx = ClockDomain(reset_less=False)
        self.clock_domains.cd_eth_tx = ClockDomain(reset_less=False)
        self.comb += [
            ClockSignal("eth_rx").eq(pads.gmii.rx_clk),
            ClockSignal("eth_tx").eq(pads.gmii.tx_clk),
        ]
        self.submodules += [
            ClockDomainsRenamer("eth_rx")(ENETRx(pads, self.enet.gmii)),
            ClockDomainsRenamer("eth_tx")(ENETTx(pads, self.enet.gmii)),
        ]


class PS7(Module):
    def __init__(self, pads=SimpleNamespace(
            ps=None, ddr=None, enet0=None, enet1=None), **kwargs):
        pads.ps = pads.ps or ps_rec()
        pads.ddr = pads.ddr or ddr_rec()

        self.m_axi_gp0 = Interface(id_width=12)
        self.m_axi_gp1 = Interface(id_width=12)
        self.s_axi_gp0 = Interface(id_width=6)
        self.s_axi_gp1 = Interface(id_width=6)
        self.s_axi_acp = Interface(data_width=64, id_width=3)
        self.s_axi_acp_user = acp_user_rec(name="s_axi_acp")
        self.s_axi_hp0 = Interface(
            data_width=64, addr_width=32, id_width=6)
        self.s_axi_hp0_fifo = hp_fifo_rec(name="s_axi_hp0")
        self.s_axi_hp1 = Interface(
            data_width=64, addr_width=32, id_width=6)
        self.s_axi_hp1_fifo = hp_fifo_rec(name="s_axi_hp1")
        self.s_axi_hp2 = Interface(
            data_width=64, addr_width=32, id_width=6)
        self.s_axi_hp2_fifo = hp_fifo_rec(name="s_axi_hp2")
        self.s_axi_hp3 = Interface(
            data_width=64, addr_width=32, id_width=6)
        self.s_axi_hp3_fifo = hp_fifo_rec(name="s_axi_hp3")

        self.ttc0 = ttc_rec()
        self.ttc1 = ttc_rec()
        self.wdt = wdt_rec()
        self.spi0 = spio_rec()
        self.spi1 = spio_rec()
        self.i2c0 = i2c_rec()
        self.i2c1 = i2c_rec()
        self.can0 = can_rec()
        self.can1 = can_rec()
        self.uart0 = uart_rec()
        self.uart1 = uart_rec()
        self.sdio0 = sdio_rec()
        self.sdio1 = sdio_rec()
        self.gpio = gpio_rec()
        self.usb0 = usb_rec()
        self.usb1 = usb_rec()
        self.sram = sram_rec()
        self.fpga_idle_n = Signal()
        self.event = event_rec()
        self.ddr_arb = Signal(4)
        self.mio = Signal(54)

        self.clock_domains.cd_sys = ClockDomain()
        self.clock_domains.cd_por = ClockDomain(reset_less=True)

        self.dma0 = dmac_bus.Interface(name="dma0")
        self.dma1 = dmac_bus.Interface(name="dma1")
        self.dma2 = dmac_bus.Interface(name="dma2")
        self.dma3 = dmac_bus.Interface(name="dma3")

        self.spi = Record([
            ("can1", 1),
            ("uart1", 1),
            ("spi1", 1),
            ("i2c1", 1),
            ("sdio1", 1),
            ("enet1_wake", 1),
            ("enet1", 1),
            ("usb1", 1),
            ("can0", 1),
            ("uart0", 1),
            ("spi0", 1),
            ("i2c0", 1),
            ("sdio0", 1),
            ("enet0_wake", 1),
            ("enet0", 1),
            ("usb0", 1),
            ("gpio", 1),
            ("cti", 1),
            ("qspi", 1),
            ("smc", 1),
            ("dmac", 8),
            ("dmac_abort", 1),
        ])
        self.interrupt = Signal(16)
        self.core = Record([
            ("core0", [("nirq", 1), ("nfiq", 1)]),
            ("core1", [("nirq", 1), ("nfiq", 1)]),
        ])
        self.trace = trace_rec()
        self.pjtag = pjtag_rec()

        ###

        s_axi_gp0_shim = Interface.like(self.s_axi_gp0, "s_axi_gp0")
        s_axi_gp1_shim = Interface.like(self.s_axi_gp1, "s_axi_gp1")
        wrshim_s_axi_gp0 = wrshim.AxiWrshim()
        wrshim_s_axi_gp1 = wrshim.AxiWrshim()
        m_axi_gp_global = [
            axi_global_rec(name="m_axi_gp{}".format(i)) for i in range(2)]
        self.comb += [i.aclk.eq(ClockSignal()) for i in m_axi_gp_global]
        s_axi_gp_global = [
            axi_global_rec(name="s_axi_gp{}".format(i)) for i in range(2)]
        self.comb += [i.aclk.eq(ClockSignal()) for i in s_axi_gp_global]
        s_axi_acp_global = axi_global_rec(name="s_axi_acp")
        self.comb += [s_axi_acp_global.aclk.eq(ClockSignal())]
        s_axi_hp_global = [
            axi_global_rec(name="s_axi_hp{}".format(i)) for i in range(4)]
        self.comb += [i.aclk.eq(ClockSignal()) for i in s_axi_hp_global]
        dma_global = [
            dma_global_rec(name="dma{}".format(i)) for i in range(4)]
        [setattr(self, "dma{}_rst_n".format(i), rec.rst_n)
         for i, rec in enumerate(dma_global)]
        self.comb += [i.aclk.eq(ClockSignal()) for i in dma_global]

        self.submodules.enet0 = ClockDomainsRenamer(
            dict(eth_rx="enet0_rx", eth_tx="enet0_tx"))(
                ENET(getattr(pads, "enet0", None)))
        self.submodules.enet1 = ClockDomainsRenamer(
            dict(eth_rx="enet1_rx", eth_tx="enet1_tx"))(
                ENET(getattr(pads, "enet1", None)))

        ddr_buf, ps_buf = ddr_rec(name="ddr"), ps_rec(name="ps")
        mio_buf = Signal(len(self.mio))

        pads_ddr_v = Signal(len(pads.ddr))
        ddr_buf_v = Signal(len(ddr_buf))
        self.comb += [
            pads_ddr_v.eq(pads.ddr.raw_bits()),
        ]
        self.specials += [bibuf([pads_ddr_v[i], ddr_buf_v[i]])
                          for i in range(len(pads_ddr_v))]
        self.specials += [
            bibuf([pads.ps.clk, ps_buf.clk]),
            bibuf([pads.ps.por_b, ps_buf.por_b]),
            bibuf([pads.ps.srst_b, ps_buf.srst_b])]
        self.specials += [bibuf([self.mio[i], mio_buf[i]])
                          for i in range(len(self.mio))]

        self.submodules += [
            wrshim_s_axi_gp0,
            InterconnectPointToPoint(self.s_axi_gp0, s_axi_gp0_shim),
            wrshim_s_axi_gp1,
            InterconnectPointToPoint(self.s_axi_gp1, s_axi_gp1_shim),
        ]

        self.fclk = fclk_rec()
        # fclk.reset_n considered async
        self.specials += [
            AsyncResetSynchronizer(self.cd_sys, ~self.fclk.reset_n[0]),
            bufg([self.fclk.clk[0], ClockSignal()]),
        ]

        self.comb += self.fclk.clktrig_n.eq(0)
        ftmd = ftmd_rec()
        ftmt = ftmt_rec()
        irq = irq_rec()
        self.comb += [
            irq.f2p[: 16].eq(self.interrupt),
            irq.f2p[16: 20].eq(
                Cat(self.core.core0.nirq, self.core.core1.nirq,
                    self.core.core0.nfiq, self.core.core1.nfiq)),
            self.spi.raw_bits().eq(irq.p2f),
        ]
        ps7_attrs = pipe([
            connect_interface(s_axi_gp_global[0]),
            connect_s_axi(s_axi_gp0_shim),
            connect_interface(s_axi_gp_global[1]),
            connect_s_axi(s_axi_gp1_shim),
            connect_interface(m_axi_gp_global[0]),
            connect_m_axi(self.m_axi_gp0),
            connect_interface(m_axi_gp_global[1]),
            connect_m_axi(self.m_axi_gp1),
            connect_interface(s_axi_acp_global),
            connect_s_axi(self.s_axi_acp),
            connect_interface(self.s_axi_acp_user),
            connect_interface(s_axi_hp_global[0]),
            connect_interface(self.s_axi_hp0, False),
            connect_interface(self.s_axi_hp0_fifo),
            connect_interface(s_axi_hp_global[1]),
            connect_interface(self.s_axi_hp1, False),
            connect_interface(self.s_axi_hp1_fifo),
            connect_interface(s_axi_hp_global[2]),
            connect_interface(self.s_axi_hp2, False),
            connect_interface(self.s_axi_hp2_fifo),
            connect_interface(s_axi_hp_global[3]),
            connect_interface(self.s_axi_hp3, False),
            connect_interface(self.s_axi_hp3_fifo),
            connect_interface(ddr_buf),
            dict(io_MIO=mio_buf),
            connect_interface(self.ttc0),
            connect_interface(self.ttc1),
            connect_interface(self.wdt),
            connect_interface(self.spi0),
            connect_interface(self.spi1),
            connect_interface(self.i2c0),
            connect_interface(self.i2c1),
            connect_interface(self.can0),
            connect_interface(self.can1),
            connect_interface(self.uart0),
            connect_interface(self.uart1),
            connect_interface(self.sdio0),
            connect_interface(self.sdio1),
            connect_interface(self.gpio),
            keymap(str_replace("TRACE", "EMIOTRACE"),
                   connect_interface(self.trace)),
            connect_interface(self.pjtag),
            connect_interface(self.usb0),
            connect_interface(self.usb1),
            connect_interface(self.sram),
            connect_interface(self.fclk),
            dict(i_FPGAIDLEN=self.fpga_idle_n),
            connect_interface(self.event),
            dict(i_DDRARB=self.ddr_arb),
            connect_interface(ftmd),
            connect_interface(ftmt),
            connect_interface(dma_global[0]),
            connect_interface(self.dma0),
            connect_interface(dma_global[1]),
            connect_interface(self.dma1),
            connect_interface(dma_global[2]),
            connect_interface(self.dma2),
            connect_interface(dma_global[3]),
            connect_interface(self.dma3),
            connect_interface(irq),
            dict(io_PSPORB=ps_buf.por_b,
                 io_PSSRSTB=ps_buf.srst_b,
                 io_PSCLK=ps_buf.clk),
            keymap(str_replace("ENET", "EMIOENET0"),
                   connect_interface(self.enet0.enet)),
            keymap(str_replace("ENET", "EMIOENET1"),
                   connect_interface(self.enet1.enet)),
        ],
            R.apply(merge),
            keymap(str_replace("TTC", "EMIOTTC")),
            keymap(str_replace("WDT", "EMIOWDT")),
            keymap(str_replace("SPI", "EMIOSPI")),
            keymap(str_replace("I2C", "EMIOI2C")),
            keymap(str_replace("CAN", "EMIOCAN")),
            keymap(str_replace("UART", "EMIOUART")),
            keymap(str_replace("SDIO", "EMIOSDIO")),
            keymap(str_replace("GPIO", "EMIOGPIO")),
            keymap(str_replace("PJTAG", "EMIOPJTAG")),
            keymap(str_replace("USB", "EMIOUSB")),
            keymap(str_replace("SRAM", "EMIOSRAM")),
            keymap(str_replace("DDRDRSTN", "DDRDRSTB")),
            keymap(str_replace("DDRWEN", "DDRWEB")),
            keymap(str_replace("DDRRASN", "DDRRASB")),
            keymap(str_replace("DDRCASN", "DDRCASB")),
            keymap(str_replace("DDRCSN", "DDRCSB")),
            keymap(str_replace("EMIOSPI0SSTN", "EMIOSPI0SSNTN")),
            keymap(str_replace("EMIOSPI1SSTN", "EMIOSPI1SSNTN")),
            keymap(str_replace("EMIOSPI0MTN", "EMIOSPI0MOTN")),
            keymap(str_replace("EMIOSPI1MTN", "EMIOSPI1MOTN")),
            keymap(str_replace("EVENTO", "EVENTEVENTO")),
            keymap(str_replace("EVENTI", "EVENTEVENTI")),
        )
        self.specials += Instance("PS7", **ps7_attrs)
