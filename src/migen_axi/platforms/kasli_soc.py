from migen import *  # noqa
from migen.build.platforms.sinara import kasli_soc
from migen.build.generic_platform import Pins, Subsignal, IOStandard


__all__ = ["Platform"]


class Platform(kasli_soc.Platform):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().__getattribute__("add_extension")([
            ("ps", 0,
             Subsignal("clk", Pins("B24"), IOStandard("LVCMOS33")),
             Subsignal("por_b", Pins("C23"), IOStandard("LVCMOS33")),
             Subsignal("srst_b", Pins("A22"), IOStandard("LVCMOS18"))),
            ("ddr", 0,
             Subsignal("dq",
                       Pins("J26 F25 J25 G26 H26 H23 J24 J23 K26 L23 M26 K23 M25 N24 M24 N23 "
                            "R26 P24 N26 P23 T24 T25 T23 R23 V24 U26 U24 U25 W26 Y25 Y26 W23"),
                       IOStandard("SSTL15_T_DCI")),
             Subsignal("dm", Pins("G24 K25 P26 V26"), IOStandard("SSTL15_T_DCI")),
             Subsignal("dqs_n",
                       Pins("G25 L25 R25 W25"),
                       IOStandard("DIFF_SSTL15_T_DCI")),
             Subsignal("dqs_p",
                       Pins("H24 L24 P25 W24"),
                       IOStandard("DIFF_SSTL15_T_DCI")),
             Subsignal("a",
                       Pins("K22 K20 N21 L22 M20 N22 L20 J21 T20 U20 M22 H21 P20 J20 R20"),
                       IOStandard("SSTL15")),
             Subsignal("ba", Pins("U22 T22 R22"), IOStandard("SSTL15")),
             Subsignal("cas_n", Pins("Y23"), IOStandard("SSTL15")),
             Subsignal("vrn", Pins("V21"), IOStandard("SSTL15_T_DCI")),
             Subsignal("vrp", Pins("W21"), IOStandard("SSTL15_T_DCI")),
             Subsignal("ras_n", Pins("V23"), IOStandard("SSTL15")),
             Subsignal("we_n", Pins("V22"), IOStandard("SSTL15")),
             Subsignal("odt", Pins("Y22"), IOStandard("SSTL15")),
             Subsignal("cke", Pins("U21"), IOStandard("SSTL15")),
             Subsignal("cs_n", Pins("Y21"), IOStandard("SSTL15")),
             Subsignal("clk_n", Pins("P21"), IOStandard("DIFF_SSTL15")),
             Subsignal("clk_p", Pins("R21"), IOStandard("DIFF_SSTL15")),
             Subsignal("reset_n", Pins("H22"), IOStandard("SSTL15"))),
        ])
