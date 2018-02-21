from migen import *  # noqa
from migen.build.platforms import zedboard
from migen.build.generic_platform import Pins, Subsignal, IOStandard


__all__ = ["Platform"]


class Platform(zedboard.Platform):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().__getattribute__("add_extension")([
            ("ps", 0,
             Subsignal("clk", Pins("F7"), IOStandard("LVCMOS33")),
             Subsignal("por_b", Pins("B5"), IOStandard("LVCMOS33")),
             Subsignal("srst_b", Pins("C9"), IOStandard("LVCMOS18"))),
            ("ddr", 0,
             Subsignal("a",
                       Pins("M4 M5 K4 L4 K6 K5 J7 J6 J5 H5 J3 G5 H4 F4 G4"),
                       IOStandard("SSTL15")),
             Subsignal("ba", Pins("L7 L6 M6"), IOStandard("SSTL15")),
             Subsignal("cas_n", Pins("P3"), IOStandard("SSTL15")),
             Subsignal("cke", Pins("V3"), IOStandard("SSTL15")),
             Subsignal("ck_n", Pins("N5"), IOStandard("DIFF_SSTL15")),
             Subsignal("ck_p", Pins("N4"), IOStandard("DIFF_SSTL15")),
             Subsignal("cs_n", Pins("P6"), IOStandard("SSTL15")),
             Subsignal("dm", Pins("B1 H3 P1 AA2"), IOStandard("SSTL15_T_DCI")),
             Subsignal("dq",
                       Pins("D1 C3 B2 D3 E3 E1 F2 F1 G2 G1 L1 L2 L3 K1 J1 K3 "
                            "M1 T3 N3 T1 R3 T2 M2 R1 AA3 U1 AA1 U2 W1 Y3 W3 Y1"),
                       IOStandard("SSTL15_T_DCI")),
             Subsignal("dqs_n",
                       Pins("D2 J2 P2 W2"),
                       IOStandard("DIFF_SSTL15_T_DCI")),
             Subsignal("dqs_p",
                       Pins("C2 H2 N2 V2"),
                       IOStandard("DIFF_SSTL15_T_DCI")),
             Subsignal("drst_n", Pins("F3"), IOStandard("SSTL15")),
             Subsignal("odt", Pins("P5"), IOStandard("SSTL15")),
             Subsignal("ras_n", Pins("R5"), IOStandard("SSTL15")),
             Subsignal("vrn", Pins("M7"), IOStandard("SSTL15_T_DCI")),
             Subsignal("vrp", Pins("N7"), IOStandard("SSTL15_T_DCI")),
             Subsignal("we_n", Pins("R4"), IOStandard("SSTL15"))),
        ])
