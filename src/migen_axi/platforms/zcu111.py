from migen import *  # noqa
from migen.build.generic_platform import Pins, Subsignal, IOStandard
from migen.build.xilinx import XilinxPlatform


__all__ = ["Platform"]


# Xilinx Zynq UltraScale+ RFSoC ZCU111 Evaluation Board (xczu28dr-ffvg1517-2-e)
# Pin assignments taken from ZCU111_Rev1.0.xdc (rdf0466).

_io = [
    ("user_led", 0, Pins("AR13"), IOStandard("LVCMOS18")),
    ("user_led", 1, Pins("AP13"), IOStandard("LVCMOS18")),
    ("user_led", 2, Pins("AR16"), IOStandard("LVCMOS18")),
    ("user_led", 3, Pins("AP16"), IOStandard("LVCMOS18")),
    ("user_led", 4, Pins("AP15"), IOStandard("LVCMOS18")),
    ("user_led", 5, Pins("AN16"), IOStandard("LVCMOS18")),
    ("user_led", 6, Pins("AN17"), IOStandard("LVCMOS18")),
    ("user_led", 7, Pins("AV15"), IOStandard("LVCMOS18")),

    # 5-way joystick (N/S/E/W/C)
    ("user_btn", 0, Pins("AW3"),  IOStandard("LVCMOS18")),  # N
    ("user_btn", 1, Pins("E8"),   IOStandard("LVCMOS18")),  # S
    ("user_btn", 2, Pins("AW4"),  IOStandard("LVCMOS18")),  # E
    ("user_btn", 3, Pins("AW6"),  IOStandard("LVCMOS18")),  # W
    ("user_btn", 4, Pins("AW5"),  IOStandard("LVCMOS18")),  # C

    # User-programmable SI570 oscillator; default ~300 MHz (Bank 69, VCC1V2)
    ("user_si570", 0,
     Subsignal("p", Pins("J19"), IOStandard("DIFF_POD12")),
     Subsignal("n", Pins("J18"), IOStandard("DIFF_POD12"))),

    # PL UART (FTDI UART2 channel)
    ("serial", 0,
     Subsignal("tx", Pins("AU15")),
     Subsignal("rx", Pins("AT15")),
     IOStandard("LVCMOS18")),

    # PS hard-block pads (Bank 503)
    ("ps", 0,
     Subsignal("clk",    Pins("AC30"), IOStandard("LVCMOS18")),
     Subsignal("por_b",  Pins("AB29"), IOStandard("LVCMOS18")),
     Subsignal("srst_b", Pins("AB28"), IOStandard("LVCMOS18"))),

    # PS DDR4 SODIMM interface (Bank 504)
    # 64-bit data bus (DQ0-63) + 8 ECC lanes (DQ64-71, NC on this board)
    ("ddr", 0,
     Subsignal("a",
               Pins("AV31 AW28 AV28 AU29 AW31 AU28 AL29 AM30 "
                    "AM29 AP29 AT31 AT32 AT30 AU32 AR28 AP30 AP28 AK29"),
               IOStandard("SSTL12")),
     Subsignal("act_n",    Pins("AL30"),         IOStandard("SSTL12")),
     Subsignal("alert_n",  Pins("AL32"),         IOStandard("POD12")),
     Subsignal("ba",       Pins("AN30 AM32"),     IOStandard("SSTL12")),
     Subsignal("bg",       Pins("AN32 AL31"),     IOStandard("SSTL12")),
     Subsignal("ck",       Pins("AU30 AR29"),     IOStandard("DIFF_POD12")),
     Subsignal("ck_n",     Pins("AV30 AT29"),     IOStandard("DIFF_POD12")),
     Subsignal("cke",      Pins("AW30 AR32"),     IOStandard("SSTL12")),
     Subsignal("cs_n",     Pins("AW29 AR31"),     IOStandard("SSTL12")),
     Subsignal("dm",
               Pins("AU23 AT27 AL24 AM27 AV36 AT35 AM36 AJ32 AR38"),
               IOStandard("POD12")),
     Subsignal("dq",
               Pins("AW25 AW24 AV25 AW23 AV23 AV22 AR24 AR23 "
                    "AT25 AP26 AU25 AR27 AU27 AV26 AV27 AW26 "
                    "AP25 AP24 AP23 AN25 AM25 AK24 AN23 AK23 "
                    "AK26 AL25 AK28 AK27 AN27 AN26 AN28 AM28 "
                    "AU39 AU38 AU37 AU35 AV38 AW36 AV35 AW35 "
                    "AU33 AV33 AW34 AW33 AR34 AR33 AP33 AP34 "
                    "AL39 AM38 AM39 AN38 AM35 AM34 AN36 AN35 "
                    "AK32 AK31 AJ31 AJ30 AH30 AG32 AF32 AG30 "
                    "AT36 AR36 AT39 AP35 AR39 AP38 AP36 AP39"),
               IOStandard("POD12")),
     Subsignal("dqs",
               Pins("AT24 AR26 AM23 AL26 AV37 AT34 AM37 AH31 AR37"),
               IOStandard("DIFF_POD12")),
     Subsignal("dqs_n",
               Pins("AU24 AT26 AM24 AL27 AW37 AU34 AN37 AH32 AT37"),
               IOStandard("DIFF_POD12")),
     Subsignal("odt",      Pins("AV32 AP31"),     IOStandard("SSTL12")),
     Subsignal("parity",   Pins("AN31"),          IOStandard("POD12")),
     Subsignal("ram_rst_n", Pins("AM33"),         IOStandard("LVCMOS12"))),
]

_connectors = []


class Platform(XilinxPlatform):
    default_clk_name = "user_si570"
    default_clk_period = 3.333  # 300 MHz

    def __init__(self):
        XilinxPlatform.__init__(self, "xczu28dr-ffvg1517-2-e", _io, _connectors,
                                toolchain="vivado")
