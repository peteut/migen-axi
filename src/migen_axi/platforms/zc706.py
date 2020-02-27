from migen import *  # noqa
from migen.build.platforms import zc706
from migen.build.generic_platform import Pins, Subsignal, IOStandard


__all__ = ["Platform"]


class Platform(zc706.Platform):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().__getattribute__("add_extension")([
            ("ps", 0,
             Subsignal("clk", Pins("A22"), IOStandard("LVCMOS18")),
             Subsignal("por_b", Pins("D21"), IOStandard("LVCMOS18")),
             Subsignal("srst_b", Pins("B19"), IOStandard("LVCMOS18"))),
            ("ddr", 0,
             Subsignal("dq",
                       Pins("A25 E25 B27 D25 B25 E26 D26 E27 A29 A27 A30 A28 C28 D30 D28 D29 "
                            "H27 G27 H28 E28 E30 F28 G30 F30 J29 K27 J30 J28 K30 M29 L30 M30"),
                       IOStandard("SSTL15_T_DCI")),
             Subsignal("dm", Pins("C27 B30 H29 K28"), IOStandard("SSTL15_T_DCI")),
             Subsignal("dqs_n",
                       Pins("B26 B29 F29 L29"),
                       IOStandard("DIFF_SSTL15_T_DCI")),
             Subsignal("dqs_p",
                       Pins("C26 C29 G29 L28"),
                       IOStandard("DIFF_SSTL15_T_DCI")),
             Subsignal("a",
                       Pins("L25 K26 L27 G25 J26 G24 H26 K22 F27 J23 G26 H24 K23 H23 J24"),
                       IOStandard("SSTL15")),
             Subsignal("ba", Pins("M27 M26 M25"), IOStandard("SSTL15")),
             Subsignal("cas_n", Pins("M24"), IOStandard("SSTL15")),
             Subsignal("vrn", Pins("N21"), IOStandard("SSTL15_T_DCI")),
             Subsignal("vrp", Pins("M21"), IOStandard("SSTL15_T_DCI")),
             Subsignal("ras_n", Pins("N24"), IOStandard("SSTL15")),
             Subsignal("we_n", Pins("N23"), IOStandard("SSTL15")),
             Subsignal("odt", Pins("L23"), IOStandard("SSTL15")),
             Subsignal("cke", Pins("M22"), IOStandard("SSTL15")),
             Subsignal("cs_n", Pins("N22"), IOStandard("SSTL15")),
             Subsignal("clk_n", Pins("J25"), IOStandard("DIFF_SSTL15")),
             Subsignal("clk_p", Pins("K25"), IOStandard("DIFF_SSTL15")),
             Subsignal("reset_n", Pins("F25"), IOStandard("SSTL15"))),
        ])
