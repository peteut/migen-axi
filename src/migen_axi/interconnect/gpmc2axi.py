from collections import Iterable
from operator import attrgetter

from migen import *  # noqa
from . import axi

__all__ = ["GPMC2AXI", "rising_edge"]

_layout = [
    ("a", "address_width", DIR_M_TO_S),   # a[16:<address_width> + 16 + 1]
    ("ad", 16, DIR_NONE),  # a[1:17], d[:16]
    ("cs_n", 1, DIR_M_TO_S),  # chip select
    ("adv_n", 1, DIR_M_TO_S),  # address valid
    ("oe_n", 1, DIR_M_TO_S),  # output enable
    ("we_n", 1, DIR_M_TO_S),  # write enable
    ("be_n", 2, DIR_M_TO_S),  # upper (be_n[1]), lower (be_n[0])
    ("wp_n", 1, DIR_M_TO_S),  # write protect
    ("wait", 1, DIR_S_TO_M),  # wait signal
    ("dir", 1, DIR_M_TO_S),  # signal direction control
]

_BURST = (1, 4, 8, 16)
_WIDTH = (8, 16)


def _be_n(sig, adr, burst, width):
    # only non-wrapping bursts to issue
    assert adr % burst == 0
    if burst > 1:
        assert width == 16
        yield sig.eq(0)
    elif width == 16:
        yield sig.eq(0)
    else:
        yield sig.eq(0x3 ^ ((adr % 2) + 1))


def _adr(sig_a, sig_ad, adr):
    yield sig_a.eq(adr >> 17)
    yield sig_ad.eq((adr >> 1) & 0xffff)


def rising_edge(domain):
    while (yield ClockSignal(domain)) == 1:
        yield

    while (yield ClockSignal(domain)) == 0:
        yield


class Interface(Record):
    def __init__(self, address_width=8):
        super().__init__(set_layout_parameters(
            _layout, address_width=address_width))

    def write(self, domain, adr, dat, width=16):
        dat = dat if isinstance(dat, Iterable) else [dat]
        assert len(dat) in _BURST
        assert width in _WIDTH

        yield from rising_edge(domain)

        yield from _be_n(self.be_n, adr, len(dat), width)
        yield from _adr(self.a, self.ad, adr)
        yield self.cs_n.eq(0)
        yield self.adv_n.eq(0)
        yield self.oe_n.eq(1)
        yield self.we_n.eq(1)
        yield self.dir.eq(0)
        yield from rising_edge(domain)
        yield self.adv_n.eq(1)
        yield self.we_n.eq(0)
        for d in dat:
            yield self.ad.eq(d)
            yield from rising_edge(domain)

        yield self.cs_n.eq(1)
        yield self.we_n.eq(1)
        yield self.be_n.eq(0x3)
        yield from rising_edge(domain)

    def read(self, domain, adr, burst=1, width=16):
        assert burst in _BURST
        assert width in _WIDTH

        yield from rising_edge(domain)

        yield from _be_n(self.be_n, adr, burst, width)
        yield from _adr(self.a, self.ad, adr)
        yield self.cs_n.eq(0)
        yield self.adv_n.eq(0)
        yield self.oe_n.eq(1)
        yield self.we_n.eq(1)
        yield self.dir.eq(0)
        yield from rising_edge(domain)
        yield self.adv_n.eq(1)
        yield self.oe_n.eq(0)
        yield self.dir.eq(1)
        yield
        d = []
        for _ in range(burst):
            yield from rising_edge(domain)
            d.append((yield self.ad))

        yield self.oe_n.eq(1)
        yield self.dir.eq(0)
        yield self.be_n.eq(0x3)
        yield from rising_edge(domain)
        return d


class GPMC2AXI(Module):
    def __init__(self, bus_gpmc=None, bus_axi=None):
        self.gpmc = bus_gpmc or Interface()
        self.bus = bus_axi or axi.Interface()
        self.clock_domains.cd_gpmc = ClockDomain(reset_less=True)

        ###

        adr = Signal(sum(map(len, attrgetter("ad", "a")(self.gpmc))))

        self.sync.gpmc += [
            If(
                (~self.gpmc.adv_n) & (~self.gpmc.cs_n),
                adr.eq(Cat(C(0, 1), self.gpmc.ad, self.gpmc.a))
            ),
        ]
