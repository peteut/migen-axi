from nmigen import *  # noqa
from nmigen.hdl.ast import Operator
from migen_axi.interconnect.stream import *  # noqa


def test_stream():
    dut = Stream(Record([("foo", 42)]))
    assert isinstance(dut.clone(), Stream)
    m, s = dut.clone(), dut.clone()
    m.master()
    s.slave()
    dut.slave()
    assert isinstance(dut << m, Stream)
    assert isinstance(dut.lt_dash_lt(m), Stream)
    dut.master()
    assert isinstance(dut >> s, Stream)
    assert isinstance(dut.gt_dash_gt(s), Stream)
    assert isinstance(dut.get_fragment(), Fragment)

    assert isinstance(dut.free_run(), Stream)
    assert isinstance(dut.is_stall(), Operator)
    assert isinstance(dut.is_new(), Operator)
    assert isinstance(dut.fire(), Operator)
    assert isinstance(dut.is_free(), Operator)
    assert isinstance(dut.valid_pipe(), Stream)
    assert isinstance(dut.half_pipe(), Stream)
    assert isinstance(dut.continue_when(Const(1)), Stream)
    assert isinstance(dut.throw_when(Const(1)), Stream)
    assert isinstance(dut.halt_when(Const(1)), Stream)
    assert isinstance(dut.take_when(Const(1)), Stream)
    assert isinstance(dut.add_fraction_last(Const(1)), Stream)
