from migen import *  # noqa
from migen.build.platforms import coraz7
from migen.build.generic_platform import Pins, Subsignal, IOStandard


__all__ = ["Platform"]


# Digilent Cora Z7-07S, and Z7-10
class Platform(coraz7.Platform):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().__getattribute__("add_extension")([
            ("ps", 0,
             Subsignal("clk", Pins("E7"), IOStandard("LVCMOS33")),
             Subsignal("por_b", Pins("C7"), IOStandard("LVCMOS33")),
             Subsignal("srst_b", Pins("B10"), IOStandard("LVCMOS18"))),
            ("ddr", 0,
             Subsignal("a",
                       Pins("N2 K2 M3 K3 M4 L1 L4 K4 K1 J4 F5 G4 E4 D4 F4"),
                       IOStandard("SSTL15")),
             Subsignal("ba", Pins("L5 R4 J5"), IOStandard("SSTL15")),
             Subsignal("cas_n", Pins("P5"), IOStandard("SSTL15")),
             Subsignal("cke", Pins("N3"), IOStandard("SSTL15")),
             Subsignal("ck_n", Pins("M2"), IOStandard("DIFF_SSTL15")),
             Subsignal("ck_p", Pins("L2"), IOStandard("DIFF_SSTL15")),
             Subsignal("cs_n", Pins("N1"), IOStandard("SSTL15")),
             Subsignal("dm", Pins("A1 F1 T1 Y1"), IOStandard("SSTL15_T_DCI")),
             Subsignal("dq",
                       Pins("C3 B3 A2 A4 D3 D1 C1 E1 E2 E3 G3 H3 J3 H2 H1 J1 "
                            "P1 P3 R3 R1 T4 U4 U2 U3 V1 Y3 W1 Y4 Y2 W3 V2 V3"),
                       IOStandard("SSTL15_T_DCI")),
             Subsignal("dqs_n",
                       Pins("B2 F2 T2 W4"),
                       IOStandard("DIFF_SSTL15_T_DCI")),
             Subsignal("dqs_p",
                       Pins("C2 G2 R2 W5"),
                       IOStandard("DIFF_SSTL15_T_DCI")),
             Subsignal("drst_n", Pins("B4"), IOStandard("SSTL15")),
             Subsignal("odt", Pins("N5"), IOStandard("SSTL15")),
             Subsignal("ras_n", Pins("P4"), IOStandard("SSTL15")),
             Subsignal("vrn", Pins("G5"), IOStandard("SSTL15_T_DCI")),
             Subsignal("vrp", Pins("H5"), IOStandard("SSTL15_T_DCI")),
             Subsignal("we_n", Pins("M5"), IOStandard("SSTL15"))),
        ])
