"""Zynq UltraScale+ MPSoC "PS8" hard-block wrapper.

This is the PS8-generation counterpart of :mod:`migen_axi.cores.ps7`: it wraps
the raw ``PS8`` primitive (as instantiated directly, the way Vivado's
``zynq_ultra_ps_e`` IP would generate it, without going through that IP's
GUI/TCL layer) the same way ``ps7.py`` wraps ``PS7``. All port names and
widths were taken from Xilinx's own (Apache-2.0) unisim simulation model for
PS8, so they should match what Vivado expects when elaborating the design.
(https://github.com/Xilinx/XilinxUnisimLibrary/blob/master/verilog/src/unisims/PS8.v)

The PS8 primitive is dramatically larger than PS7 (~1000 ports vs. ~150), so
this wrapper only covers the subset that has a direct PS7 analogue and that
most fabric-facing designs actually use:

* the general purpose AXI ports (3 master, 7 slave) and the ACP port
* the DDR (DDR3/3L/4, LPDDR3/4) memory interface and MIO/boot pins
* the EMIO peripherals: GPIO, I2C0/1, CAN0/1, UART0/1, SPI0/1, SDIO0/1,
  TTC0-3, WDT0/1, and the 4 gigabit Ethernet (GEM) MACs
* PL clocks, the coarse PL<->PS interrupt buses, and the WFE/WFI event pins
"""
from types import SimpleNamespace
from toolz.curried import *  # noqa
import operator
import ramda as R
from migen import *  # noqa
from migen.genlib.record import DIR_S_TO_M, DIR_M_TO_S, DIR_NONE
from ..interconnect import Interface


__all__ = ["PS8", "ddr_rec", "enet_rec"]


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


# unlike PS7's AXI3-derived GP/HP/ACP ports, PS8's are full AXI4 and have no
# per-beat write ID (WID) pin, so drop the "id" field of the (shared)
# Interface class's write-data channel before connecting. Filtering by key
# name suffix would also catch AWID (e.g. "RECAWID".endswith("WID")), which
# is a real AXI4 field and must stay connected -- so filter by identity of
# the underlying signal instead.
def _drop_wid(interface, mapping):
    return {k: v for k, v in mapping.items() if v is not interface.w.id}


def connect_s_axi(interface):
    return _drop_wid(interface, connect_interface(interface, False))


def connect_m_axi(interface):
    return _drop_wid(interface, connect_interface(interface, True))


# unlike PS7's S/M_AXI_GP ports, PS8's AR/AWSIZE pins are full AXI4 width
# (3 bits) on every port, so no truncation is needed here.

axi_m_global_rec = partial(Record, [
    ("aclk", 1, DIR_M_TO_S),
])

axi_s_global_rec = partial(Record, [
    ("rclk", 1, DIR_M_TO_S),
    ("wclk", 1, DIR_M_TO_S),
])

gp_m_user_rec = partial(Record, [
    ("awuser", 16, DIR_M_TO_S),
    ("aruser", 16, DIR_M_TO_S),
])

gp_s_user_rec = partial(Record, [
    ("awuser", 1, DIR_S_TO_M),
    ("aruser", 1, DIR_S_TO_M),
])

acp_user_rec = partial(Record, [
    ("awuser", 2, DIR_S_TO_M),
    ("aruser", 2, DIR_S_TO_M),
])

ps_rec = partial(Record, [
    ("clk", 1),
    ("por_b", 1),
    ("srst_b", 1),
])

# DDR4/LPDDR4-style pinout (PS8 replaced RAS#/CAS#/WE# with ACT_n, and added
# BG/parity/alert pins versus PS7's DDR2/DDR3-only ddr_rec).
ddr_rec = partial(Record, [
    ("a", 18),
    ("act_n", 1),
    ("alert_n", 1),
    ("ba", 2),
    ("bg", 2),
    ("ck", 2),
    ("ck_n", 2),
    ("cke", 2),
    ("cs_n", 2),
    ("dm", 9),
    ("dq", 72),
    ("dqs", 9),
    ("dqs_n", 9),
    ("odt", 2),
    ("parity", 1),
    ("ram_rst_n", 1),
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
    ("ext_intin", 1, DIR_S_TO_M),
])

# the GEM timestamp-unit/PTP pins live under a separate "EMIOGEM<n>" prefix
# rather than "EMIOENET<n>" -- connected separately from enet_rec, below.
gem_rec = partial(Record, [
    ("delay_req_rx", 1, DIR_M_TO_S),
    ("delay_req_tx", 1, DIR_M_TO_S),
    ("pdelay_req_rx", 1, DIR_M_TO_S),
    ("pdelay_req_tx", 1, DIR_M_TO_S),
    ("pdelay_resp_rx", 1, DIR_M_TO_S),
    ("pdelay_resp_tx", 1, DIR_M_TO_S),
    ("rx_sof", 1, DIR_M_TO_S),
    ("sync_frame_rx", 1, DIR_M_TO_S),
    ("sync_frame_tx", 1, DIR_M_TO_S),
    ("tsu_timer_cmp_val", 1, DIR_M_TO_S),
    ("txr_fixed_lat", 1, DIR_M_TO_S),
    ("tx_sof", 1, DIR_M_TO_S),
    ("tsu_inc_ctrl", 2, DIR_S_TO_M),
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

# PS8's SDIO EMIO pins use different field names than PS7's (e.g. CLKOUT
# rather than CLK, and dedicated *ENA enable pins rather than generic
# tristate() *TN pins), so this isn't shared with ps7.py's sdio_rec.
sdio_rec = partial(Record, [
    ("clkout", 1, DIR_M_TO_S),
    ("fbclkin", 1, DIR_S_TO_M),
    ("cmdin", 1, DIR_S_TO_M),
    ("cmdout", 1, DIR_M_TO_S),
    ("cmdena", 1, DIR_M_TO_S),
    ("datain", 8, DIR_S_TO_M),
    ("dataout", 8, DIR_M_TO_S),
    ("dataena", 8, DIR_M_TO_S),
    ("cdn", 1, DIR_S_TO_M),
    ("wp", 1, DIR_S_TO_M),
    ("ledcontrol", 1, DIR_M_TO_S),
    ("buspower", 1, DIR_M_TO_S),
    ("busvolt", 3, DIR_M_TO_S),
])

gpio_rec = partial(Record, [
    ("i", 96, DIR_S_TO_M),
    ("o", 96, DIR_M_TO_S),
    ("t_n", 96, DIR_M_TO_S)])

# minimal EMIO USB pins PS8 exposes: per dual-role USB2/USB3 downstream
# port VBUS control, and per hub-port overcurrent indication. Everything
# else about USB0/1 goes through the dedicated (non-EMIO) USB3 PHY pins.
usb_rec = partial(Record, [
    ("u2dsport_vbusctrl_usb30", 1, DIR_M_TO_S),
    ("u2dsport_vbusctrl_usb31", 1, DIR_M_TO_S),
    ("u3dsport_vbusctrl_usb30", 1, DIR_M_TO_S),
    ("u3dsport_vbusctrl_usb31", 1, DIR_M_TO_S),
    ("hubportovercrnt_usb20", 1, DIR_S_TO_M),
    ("hubportovercrnt_usb21", 1, DIR_S_TO_M),
    ("hubportovercrnt_usb30", 1, DIR_S_TO_M),
    ("hubportovercrnt_usb31", 1, DIR_S_TO_M),
])

# PS8 has no discrete per-fclk reset pin the way PS7's FCLKRESETN is;
# pl_resetn-style signals come from PS8's internal reset controller instead
# and aren't exposed on the primitive, so fclk only carries the clocks.
fclk_rec = partial(Record, [
    ("clk", 4, DIR_M_TO_S),
])

event_rec = partial(Record, [
    ("i", 1, DIR_S_TO_M),
    ("o", 1, DIR_M_TO_S),
    ("standbywfe", 4, DIR_M_TO_S),
    ("standbywfi", 4, DIR_M_TO_S),
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
        self.mac = enet_rec(name="enet")
        self.gem = gem_rec(name="gem")

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
            ClockDomainsRenamer("eth_rx")(ENETRx(pads, self.mac.gmii)),
            ClockDomainsRenamer("eth_tx")(ENETTx(pads, self.mac.gmii)),
        ]


class PS8(Module):
    def __init__(self, pads=SimpleNamespace(
            ps=None, ddr=None, enet0=None, enet1=None, enet2=None,
            enet3=None), ps_cd_sys=True, **kwargs):
        pads.ps = pads.ps or ps_rec()
        pads.ddr = pads.ddr or ddr_rec()

        # 3 master GP AXI ports, named after the raw PS8 primitive's own
        # MAXIGP0/1/2 pins: same convention as ps7.py's m_axi_gp0/gp1.
        # The public (UG1085) names for these pins are:
        # - gp0 --> HPM0_FPD
        # - gp1 --> HPM1_FPD
        # - gp2 --> HPM0_LPD
        for i in range(3):
            name = "m_axi_gp{}".format(i)
            setattr(self, name, Interface(
                data_width=128, addr_width=40, id_width=16, name=name))
            setattr(self, name + "_user", gp_m_user_rec(name=name))

        # 7 slave GP AXI ports, named after the raw SAXIGP0-6 pins. The public (UG1085)
        # names for these pins are:
        # - gp0/1 = S_AXI_HPC0_FPD/HPC1_FPD (cache-coherent, via the CCI)
        # - gp2-5 = S_AXI_HP0-3_FPD (high-performance, non-coherent)
        # - gp6 = S_AXI_PL_LPD (routed through the Low Power Domain switch)
        for i in range(7):
            name = "s_axi_gp{}".format(i)
            setattr(self, name, Interface(
                data_width=128, addr_width=49, id_width=6, name=name))
            setattr(self, name + "_user", gp_s_user_rec(name=name))

        # ACP AXI slave port
        self.s_axi_acp = Interface(
            data_width=128, addr_width=40, id_width=5, name="s_axi_acp")
        self.s_axi_acp_user = acp_user_rec(name="s_axi_acp")

        # All peripherals
        self.ttc0 = ttc_rec(name="ttc0")
        self.ttc1 = ttc_rec(name="ttc1")
        self.ttc2 = ttc_rec(name="ttc2")
        self.ttc3 = ttc_rec(name="ttc3")
        self.wdt0 = wdt_rec(name="wdt0")
        self.wdt1 = wdt_rec(name="wdt1")
        self.spi0 = spio_rec(name="spi0")
        self.spi1 = spio_rec(name="spi1")
        self.i2c0 = i2c_rec(name="i2c0")
        self.i2c1 = i2c_rec(name="i2c1")
        self.can0 = can_rec(name="can0")
        self.can1 = can_rec(name="can1")
        self.uart0 = uart_rec(name="uart0")
        self.uart1 = uart_rec(name="uart1")
        self.sdio0 = sdio_rec(name="sdio0")
        self.sdio1 = sdio_rec(name="sdio1")
        self.gpio = gpio_rec(name="gpio")
        self.usb = usb_rec(name="usb")
        self.event = event_rec(name="event")
        self.mio = Signal(78)

        if ps_cd_sys:
            self.clock_domains.cd_sys = ClockDomain()

        # PL <-> PS interrupts. PLPSIRQ0/1 (16 bits total) are the coarse
        # fabric-to-PS interrupt lines; PSPLIRQFPD/LPD are the PS's GIC
        # interrupt outputs to the PL. Per-peripheral bit assignment isn't
        # broken out the way PS7's `spi` record does -- see the module
        # docstring.
        self.interrupt = Signal(16)
        self.irq_p2f_fpd = Signal(64)
        self.irq_p2f_lpd = Signal(100)

        self.fclk = fclk_rec(name="fclk")

        ###

        m_axi_gp_global = [
            axi_m_global_rec(name="m_axi_gp{}".format(i)) for i in range(3)]
        self.comb += [i.aclk.eq(ClockSignal()) for i in m_axi_gp_global]
        s_axi_gp_global = [
            axi_s_global_rec(name="s_axi_gp{}".format(i)) for i in range(7)]
        self.comb += [i.rclk.eq(ClockSignal()) for i in s_axi_gp_global]
        self.comb += [i.wclk.eq(ClockSignal()) for i in s_axi_gp_global]
        s_axi_acp_global = axi_m_global_rec(name="s_axi_acp")
        self.comb += [s_axi_acp_global.aclk.eq(ClockSignal())]

        enets = [ClockDomainsRenamer(
            dict(eth_rx="enet{}_rx".format(i), eth_tx="enet{}_tx".format(i)))(
                ENET(getattr(pads, "enet{}".format(i), None)))
            for i in range(4)]
        for i, enet in enumerate(enets):
            setattr(self.submodules, "enet{}".format(i), enet)

        ddr_buf, ps_buf = ddr_rec(name="ddr"), ps_rec(name="ps")
        mio_buf = Signal(len(self.mio))

        pads_ddr_v = Signal(len(pads.ddr))
        # bibuf each pad bit straight into the matching bit of ddr_buf's own
        # (named) fields -- those are what actually gets wired to the PS8
        # instance below, so an intermediate ddr_buf_v would just be a
        # same-width signal that's never connected to anything.
        ddr_buf_v = ddr_buf.raw_bits()
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

        if ps_cd_sys:
            # PS8 has no dedicated per-PLCLK reset output to synchronize
            # off of (unlike PS7's FCLKRESETN); cd_sys is left un-reset
            # here and it's up to the design to reset it (e.g. from a
            # software-controlled GPIO/register) if needed.
            self.specials += [
                bufg([self.fclk.clk[0], ClockSignal()]),
            ]

        gp_m_users = [getattr(self, "m_axi_gp{}_user".format(i))
                      for i in range(3)]
        gp_s_users = [getattr(self, "s_axi_gp{}_user".format(i))
                      for i in range(7)]

        ps8_attrs = pipe([
            *concat(
                [connect_interface(m_axi_gp_global[i]),
                 connect_interface(gp_m_users[i]),
                 connect_m_axi(getattr(self, "m_axi_gp{}".format(i)))]
                for i in range(3)),
            *concat(
                [connect_interface(s_axi_gp_global[i]),
                 connect_interface(gp_s_users[i]),
                 connect_s_axi(getattr(self, "s_axi_gp{}".format(i)))]
                for i in range(7)),
            connect_interface(s_axi_acp_global),
            connect_interface(self.s_axi_acp_user),
            connect_s_axi(self.s_axi_acp),
            connect_interface(ddr_buf),
            dict(io_PSS_ALTO_CORE_PAD_MIO=mio_buf),
            connect_interface(self.ttc0),
            connect_interface(self.ttc1),
            connect_interface(self.ttc2),
            connect_interface(self.ttc3),
            connect_interface(self.wdt0),
            connect_interface(self.wdt1),
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
            *concat(
                [keymap(str_replace("ENET", "EMIOENET{}".format(i)),
                        connect_interface(enets[i].mac)),
                 keymap(str_replace("GEM", "EMIOGEM{}".format(i)),
                        connect_interface(enets[i].gem))]
                for i in range(4)),
            dict(
                o_EMIOU2DSPORTVBUSCTRLUSB30=self.usb.u2dsport_vbusctrl_usb30,
                o_EMIOU2DSPORTVBUSCTRLUSB31=self.usb.u2dsport_vbusctrl_usb31,
                o_EMIOU3DSPORTVBUSCTRLUSB30=self.usb.u3dsport_vbusctrl_usb30,
                o_EMIOU3DSPORTVBUSCTRLUSB31=self.usb.u3dsport_vbusctrl_usb31,
                i_EMIOHUBPORTOVERCRNTUSB20=self.usb.hubportovercrnt_usb20,
                i_EMIOHUBPORTOVERCRNTUSB21=self.usb.hubportovercrnt_usb21,
                i_EMIOHUBPORTOVERCRNTUSB30=self.usb.hubportovercrnt_usb30,
                i_EMIOHUBPORTOVERCRNTUSB31=self.usb.hubportovercrnt_usb31,
            ),
            dict(
                o_PSPLEVENTO=self.event.o,
                i_PLPSEVENTI=self.event.i,
                o_PSPLSTANDBYWFE=self.event.standbywfe,
                o_PSPLSTANDBYWFI=self.event.standbywfi,
            ),
            dict(
                i_PLPSIRQ0=self.interrupt[:8],
                i_PLPSIRQ1=self.interrupt[8:],
                o_PSPLIRQFPD=self.irq_p2f_fpd,
                o_PSPLIRQLPD=self.irq_p2f_lpd,
            ),
            dict(o_PLCLK=self.fclk.clk),
            dict(io_PSS_ALTO_CORE_PAD_CLK=ps_buf.clk,
                 io_PSS_ALTO_CORE_PAD_PORB=ps_buf.por_b,
                 io_PSS_ALTO_CORE_PAD_SRSTB=ps_buf.srst_b),
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
            # PS8's DDR pins live under PSS_ALTO_CORE_PAD_DRAM* (with real
            # underscores in the literal port name), which the ddr_buf ->
            # "io_DDR<FIELD>" derivation above can't produce directly.
            keymap(str_replace("io_DDR", "io_PSS_ALTO_CORE_PAD_DRAM")),
            keymap(str_replace("EMIOSPI0MTN", "EMIOSPI0MOTN")),
            keymap(str_replace("EMIOSPI1MTN", "EMIOSPI1MOTN")),
            keymap(str_replace("EMIOSPI0SSTN", "EMIOSPI0SSNTN")),
            keymap(str_replace("EMIOSPI1SSTN", "EMIOSPI1SSNTN")),
        )
        self.specials += Instance("PS8", **ps8_attrs)
