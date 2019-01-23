from nmigen import *  # noqa
from nmigen.hdl.ast import Operator
from migen_axi.interconnect.fraction import *  # noqa
from migen_axi.interconnect.misc import IDataCarrier


def test_fraction():
    dut = Fraction(Record([("foo", 1)]))
    assert isinstance(dut.last, Signal)
    assert isinstance(dut.fraction, Record)


def test_data_carrier_fraction_pimped():
    assert issubclass(DataCarrierFractionPimped, IDataCarrier)
    dut = DataCarrierFractionPimped(Record([("foo", 1)]))
    assert isinstance(dut.tail(), Operator)
    assert isinstance(dut.is_first(), Operator)
