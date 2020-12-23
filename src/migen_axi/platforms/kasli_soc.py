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
        ])
