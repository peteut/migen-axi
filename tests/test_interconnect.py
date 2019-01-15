from operator import attrgetter
import types
from toolz.curried import *  # noqa
from migen import *  # noqa
from migen.sim import run_simulation
from misoc.interconnect import csr_bus
import pytest
from migen_axi.interconnect import *  # noqa
from migen_axi.interconnect import dmac_bus, stream2axi
from .common import write_ack, wait_stb, ack, csr_w_mon, file_tmp_folder


attrgetter_r = attrgetter("id", "data", "resp", "last")

attrgetter_b = attrgetter("id", "resp")

attrgetter_csr_w_mon = attrgetter("adr", "dat_w")

attrgetter_w = attrgetter("data", "strb", "last")

attrgetter_aw = attrgetter("addr", "len", "burst")

attrgetter_ar = attrgetter("addr", "len", "burst")

okay = Response.okay


@pytest.mark.parametrize(
    "n_bytes, size", [
        (1, 0x0),
        (4, 0x2),
    ])
def test_burst_size(n_bytes, size):
    assert burst_size(n_bytes) == size


@pytest.mark.parametrize(
    "attr, value", [
        ("fixed", 0),
        ("incr", 1),
    ])
def test_burst(attr, value):
    assert getattr(Burst, attr) == value


@pytest.mark.parametrize(
    "attr, value", [
        ("normal_access", 0),
        ("exclusive_access", 1),
    ])
def test_alock(attr, value):
    assert getattr(Alock, attr) == value


@pytest.mark.parametrize(
    "attr, value", [
        ("okay", 0),
        ("exokay", 1),
    ])
def test_response(attr, value):
    assert getattr(Response, attr) == value


@pytest.mark.parametrize(
    "data_width", [
        8,
        16,
    ])
def test_axi2csr(data_width):
    dut = AXI2CSR(bus_csr=csr_bus.Interface(data_width=data_width))
    dut.submodules.sram = csr_bus.SRAM(
        0x100, 0, bus=csr_bus.Interface(data_width=data_width))
    dut.submodules += csr_bus.Interconnect(dut.csr, [dut.sram.bus])

    write_aw = partial(
        dut.bus.write_aw,
        size=burst_size(dut.bus.data_width // 8), len_=0,
        burst=Burst.fixed)
    write_w = dut.bus.write_w
    read_b = dut.bus.read_b
    write_ar = partial(
        dut.bus.write_ar,
        size=burst_size(dut.bus.data_width // 8), len_=0,
        burst=Burst.fixed)
    read_r = dut.bus.read_r
    w_mon = partial(csr_w_mon, dut.csr)

    def testbench_axi2csr():
        i = dut.bus

        def aw_channel():
            assert (yield i.aw.ready) == 1
            yield from write_aw(0x01, 0x00)
            yield from write_aw(0x02, 0x04)
            yield from write_aw(0x03, 0x08)
            yield from write_aw(0x04, 0x0c)
            yield from write_aw(0x05, 0x40)

        def w_channel():
            yield from write_w(0, 0x11, strb=1)
            yield from write_w(0, 0x22, strb=1)
            yield from write_w(0, 0x33, strb=1)
            yield from write_w(0, 0x44, strb=1)
            yield from write_w(0, 0x11223344)

        def b_channel():
            assert attrgetter_b((yield from read_b())) == (0x01, okay)
            assert attrgetter_b((yield from read_b())) == (0x02, okay)
            assert attrgetter_b((yield from read_b())) == (0x03, okay)
            assert attrgetter_b((yield from read_b())) == (0x04, okay)
            assert attrgetter_b((yield from read_b())) == (0x05, okay)

        def ar_channel():
            # ensure data was actually written
            assert attrgetter_csr_w_mon((yield from w_mon())) == (0x00, 0x11)
            assert attrgetter_csr_w_mon((yield from w_mon())) == (0x01, 0x22)
            assert attrgetter_csr_w_mon((yield from w_mon())) == (0x02, 0x33)
            assert attrgetter_csr_w_mon((yield from w_mon())) == (0x03, 0x44)
            if data_width == 8:
                assert attrgetter_csr_w_mon(
                    (yield from w_mon())) == (0x10, 0x44)
            elif data_width == 16:
                assert attrgetter_csr_w_mon(
                    (yield from w_mon())) == (0x10, 0x3344)
            # ok, read it now
            yield from write_ar(0x11, 0x00)
            yield from write_ar(0x22, 0x04)
            yield from write_ar(0x33, 0x08)
            yield from write_ar(0x44, 0x0c)
            yield from write_ar(0x55, 0x40)

        def r_channel():
            assert attrgetter_r((yield from read_r())) == (0x11, 0x11, okay, 1)
            assert attrgetter_r((yield from read_r())) == (0x22, 0x22, okay, 1)
            assert attrgetter_r((yield from read_r())) == (0x33, 0x33, okay, 1)
            assert attrgetter_r((yield from read_r())) == (0x44, 0x44, okay, 1)
            if data_width == 8:
                assert attrgetter_r((yield from read_r())) == (
                    0x55, 0x44, okay, 1)
            elif data_width == 16:
                assert attrgetter_r((yield from read_r())) == (
                    0x55, 0x3344, okay, 1)

        return [
            aw_channel(), w_channel(), b_channel(), r_channel(), ar_channel(),
        ]

    run_simulation(dut, testbench_axi2csr(),
                   vcd_name=file_tmp_folder("test_axi2csr.vcd"))


def test_read_requester():
    bus = dmac_bus.Interface()
    dut = stream2axi._ReadRequester(bus)

    def testbench_read_requester():
        assert (yield bus.da.ready) == 1
        yield bus.dr.ready.eq(1)
        assert (yield bus.da.valid) == 0
        yield dut.burst_request.eq(1)
        yield

        for _ in range(2):
            assert (yield bus.dr.valid) == 1
            assert (yield bus.dr.type) == dmac_bus.Type.burst
            for __ in range(16):
                yield
                assert (yield bus.dr.valid) == 0

            yield from bus.write_da(dmac_bus.Type.burst)
            yield

        # single transfers
        assert (yield bus.dr.valid) == 1
        assert (yield bus.dr.type) == dmac_bus.Type.burst

        for _ in range(16):
            yield from bus.write_da(dmac_bus.Type.single)
            yield
            # still in read mode?
            assert (yield bus.dr.valid) == 0
        # flush request
        yield from bus.write_da(dmac_bus.Type.flush)
        yield
        yield dut.burst_request.eq(0)
        # flush ack
        assert (yield bus.dr.valid) == 1
        assert (yield bus.dr.type) == dmac_bus.Type.flush
        yield
        assert (yield bus.dr.valid) == 0
        # flush request when idle
        yield from bus.write_da(dmac_bus.Type.flush)
        yield
        # flush ack
        assert (yield bus.dr.valid) == 1
        assert (yield bus.dr.type) == dmac_bus.Type.flush
        yield
        assert (yield bus.dr.valid) == 0

    run_simulation(dut, testbench_read_requester(),
                   vcd_name=file_tmp_folder("test_read_requester.vcd"))


def test_stream2axi_writer():  # noqa
    bus = types.SimpleNamespace(
        axi=axi.Interface(), dmac=dmac_bus.Interface())
    dut = stream2axi.Writer(bus.axi, bus.dmac)

    write_aw = partial(
        bus.axi.write_aw,
        size=burst_size(bus.axi.data_width // 8),
        burst=Burst.fixed)
    write_w = bus.axi.write_w
    read_b = bus.axi.read_b
    write_ar = partial(
        bus.axi.write_ar,
        size=burst_size(bus.axi.data_width // 8),
        burst=Burst.fixed)
    read_r = bus.axi.read_r

    def testbench_stream2axi_writer():

        def source():
            sink = dut.sink
            yield sink.stb.eq(1)
            for i in range(32):
                while (yield sink.ack) == 0:
                    yield
                yield sink.data.eq(i)
                yield

        def aw_channel():
            assert (yield bus.axi.aw.ready) == 1
            yield from write_aw(0x01, 0x00, len_=16 - 1)

        def w_channel():
            for _ in range(15):
                yield from write_w(0, 0x11223344, last=0)
            yield from write_w(0, 0x11223344, last=1)

        def b_channel():
            assert attrgetter_b((yield from read_b())) == (0x01, okay)

        def ar_channel():
            # wait for request
            assert (yield from bus.dmac.read_dr()
                    ).type == dmac_bus.Type.burst
            yield from write_ar(0x11, 0, len_=16 - 1)
            # write ack
            yield from bus.dmac.write_da(dmac_bus.Type.burst)

            # wait for request
            assert (yield from bus.dmac.read_dr()
                    ).type == dmac_bus.Type.burst
            for i in range(10):
                yield from write_ar(i, 0, len_=0)
                # ack single tx
                yield from bus.dmac.write_da(dmac_bus.Type.single)

            # flush request
            yield from bus.dmac.write_da(dmac_bus.Type.flush)
            # wait for flush ack
            assert (yield from bus.dmac.read_dr()
                    ).type == dmac_bus.Type.flush

        def r_channel():
            yield bus.axi.r.ready.eq(1)
            for i in range(15):
                assert attrgetter_r((yield from read_r())) == (
                    0x11, i, okay, 0)
            assert attrgetter_r((yield from read_r())) == (0x11, 15, okay, 1)
            for i in range(10):
                assert attrgetter_r((yield from read_r())) == (
                    i, i + 16, okay, 1)

        return [
            source(), aw_channel(), w_channel(), b_channel(),
            ar_channel(), r_channel(),
        ]

    run_simulation(dut, testbench_stream2axi_writer(),
                   vcd_name=file_tmp_folder("test_stream2axi_writer.vcd"))


def test_countdown():
    dut = axi_dma.Countdown(4)

    def testbench_countdown():
        assert (yield dut.done) == 1
        yield dut.we.eq(1)
        yield dut.count_w.eq(4)
        yield
        yield dut.we.eq(0)
        yield
        assert (yield dut.done) == 0
        yield dut.ce.eq(1)
        yield
        yield
        yield
        yield
        yield
        assert (yield dut.done) == 1
        yield dut.ce.eq(0)
        yield

    run_simulation(dut, testbench_countdown(),
                   vcd_name=file_tmp_folder("test_countdown.vcd"))


@pytest.mark.xfail(raises=ValueError)
def test_reader_check_fifo_depth():
    i = axi.Interface()
    axi_dma.Reader(i, fifo_depth=5)


def test_reader():
    i = axi.Interface()
    dut = axi_dma.Reader(i, fifo_depth=4)
    sink, source = dut.sink, dut.source

    def testbench_reader():

        def request_rx():
            yield
            # 1st burst
            yield sink.addr.eq(0x11223344)
            yield sink.n.eq(4)
            yield sink.eop.eq(1)
            yield from write_ack(sink)
            yield sink.eop.eq(0)
            # 2nd, 3rd burst
            yield sink.addr.eq(0x11223350)
            yield sink.n.eq(7)
            yield from write_ack(sink)

        def rx():
            # 1st burst
            yield source.ack.eq(1)
            yield from wait_stb(source)
            assert (yield source.data) == 0x11111111
            assert (yield source.eop) == 0
            yield
            assert (yield source.data) == 0x22222222
            assert (yield source.eop) == 0
            yield
            assert (yield source.data) == 0x33333333
            assert (yield source.eop) == 0
            yield
            assert (yield source.data) == 0x44444444
            assert (yield source.eop) == 1
            yield
            # 2nd burst
            yield from wait_stb(source)
            assert (yield source.data) == 0x11111100
            assert (yield source.eop) == 0
            yield
            assert (yield source.data) == 0x22222200
            assert (yield source.eop) == 0
            yield
            assert (yield source.data) == 0x33333300
            assert (yield source.eop) == 0
            yield
            assert (yield source.data) == 0x44444400
            assert (yield source.eop) == 0
            yield
            # 3rd burst
            yield from wait_stb(source)
            assert (yield source.data) == 0x11111101
            assert (yield source.eop) == 0
            yield
            assert (yield source.data) == 0x22222202
            assert (yield source.eop) == 0
            yield
            assert (yield source.data) == 0x33333303
            assert (yield source.eop) == 1
            yield
            assert (yield source.stb) == 0

        def ar_and_r_channel():
            # 1st burst
            assert attrgetter_ar((yield from i.read_ar())) == (
                0x11223344, 3, Burst.incr)
            yield from i.write_r(0x55, 0x11111111, okay, 0)
            yield from i.write_r(0x55, 0x22222222, okay, 0)
            yield from i.write_r(0x55, 0x33333333, okay, 0)
            yield from i.write_r(0x55, 0x44444444, okay, 1)
            # 2nd burst
            assert attrgetter_ar((yield from i.read_ar())) == (
                0x11223350, 3, Burst.incr)
            yield from i.write_r(0x55, 0x11111100, okay, 0)
            yield from i.write_r(0x55, 0x22222200, okay, 0)
            yield from i.write_r(0x55, 0x33333300, okay, 0)
            yield from i.write_r(0x55, 0x44444400, okay, 1)
            # 3rd burst, subsequent
            assert attrgetter_ar((yield from i.read_ar())) == (
                0x11223360, 3, Burst.incr)
            yield from i.write_r(0x55, 0x11111101, okay, 0)
            yield from i.write_r(0x55, 0x22222202, okay, 0)
            yield from i.write_r(0x55, 0x33333303, okay, 0)
            yield from i.write_r(0x55, 0x44444404, okay, 1)

        return [
            request_rx(), rx(), ar_and_r_channel(),
        ]

    run_simulation(dut, testbench_reader(),
                   vcd_name=file_tmp_folder("test_reader.vcd"))


def test_writer():
    i = axi.Interface()
    dut = axi_dma.Writer(i, fifo_depth=4)
    sink = dut.sink

    def testbench_writer():

        def tx():
            yield sink.addr.eq(0x11223344)
            yield sink.data.eq(0x11111111)
            yield from write_ack(sink)
            yield sink.data.eq(0x22222222)
            yield from write_ack(sink)
            yield sink.data.eq(0x33333333)
            yield from write_ack(sink)
            yield sink.data.eq(0x44444444)
            yield from write_ack(sink)
            # 2nd burst
            yield sink.data.eq(0x11111111)
            yield from write_ack(sink)
            yield sink.data.eq(0x22222222)
            yield from write_ack(sink)
            yield sink.data.eq(0x33333333)
            yield from write_ack(sink)
            yield sink.data.eq(0x44444444)
            yield from write_ack(sink)
            yield sink.eop.eq(1)
            yield from write_ack(sink)
            yield sink.eop.eq(0)
            # 3rd burst, partial, send only 8 bytes
            yield sink.addr.eq(0x11223344)
            yield sink.data.eq(0x11111100)
            yield from write_ack(sink)
            yield sink.data.eq(0x22222200)
            yield from write_ack(sink)
            yield sink.eop.eq(1)
            yield from write_ack(sink)
            yield sink.eop.eq(0)

        def aw_channel():
            assert attrgetter_aw((yield from i.read_aw())) == (
                0x11223344, 3, Burst.incr)
            # 2nd burst
            assert attrgetter_aw((yield from i.read_aw())) == (
                0x11223354, 3, Burst.incr)
            # 3rd burst
            assert attrgetter_aw((yield from i.read_aw())) == (
                0x11223344, 3, Burst.incr)

        def w_channel():
            yield i.w.ready.eq(1)
            assert attrgetter_w((yield from i.read_w())) == (
                0x11111111, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x22222222, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x33333333, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x44444444, 0xf, 1)
            # 2nd burst
            assert attrgetter_w((yield from i.read_w())) == (
                0x11111111, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x22222222, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x33333333, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x44444444, 0xf, 1)
            # 3rd burst
            assert attrgetter_w((yield from i.read_w())) == (
                0x11111100, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x22222200, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x22222200, 0xf, 0)
            assert attrgetter_w((yield from i.read_w())) == (
                0x22222200, 0xf, 1)
            yield i.w.ready.eq(0)

        def b_channel():
            yield from i.write_b(0)
            yield from i.write_b(0)
            yield from i.write_b(0)

        return [
            tx(), aw_channel(), w_channel(), b_channel()
        ]

    run_simulation(dut, testbench_writer(),
                   vcd_name=file_tmp_folder("test_writer.vcd"))


def mem_decoder(address, start=28, end=31):
    def decoder(addr):
        return addr[start:end] == (
            (address >> start) & (2**(end - start)) - 1)

    return decoder


def test_transaction_arbiter():
    mem_map = {
        "s_0": 0x10000000,
        "s_1": 0x20000000,
    }
    m_0 = axi.Interface()
    m_1 = axi.Interface()
    m = [m_0, m_1]
    s_0 = axi.Interface()
    s_1 = axi.Interface()
    s = [
        (mem_decoder(mem_map["s_0"]), s_0),
        (mem_decoder(mem_map["s_1"]), s_1)]
    dut = axi.TransactionArbiter(m, s, npending=2)

    def testbench_transaction_arbiter():

        def request_m_0():
            yield from m_0.write_ar(
                0x01, mem_map["s_0"], 0, m_0.data_width // 8, Burst.fixed)

        def response_s_0():
            ar = s_0.ar
            yield
            yield
            yield
            yield ar.ready.eq(1)
            yield
            assert attrgetter_ar((yield from s_0.read_ar())) == (
                mem_map["s_0"], 0, Burst.fixed)
            yield ar.ready.eq(0)

        def transaction_s_0():
            source = dut.r_transaction[0].source
            yield from wait_stb(source)
            assert (yield source.sel) == 1 << 0
            yield from ack(source)

        def request_m_1():
            yield
            yield from m_1.write_aw(
                0x02, mem_map["s_1"], 0, m_0.data_width // 8, Burst.fixed)

        def response_s_1():
            aw = s_1.aw
            yield
            yield aw.ready.eq(1)
            yield
            assert attrgetter_aw((yield from s_1.read_aw())) == (
                mem_map["s_1"], 0, Burst.fixed)
            yield aw.ready.eq(0)

        def transaction_s_1():
            source = dut.w_transaction[1].source
            yield from wait_stb(source)
            assert (yield source.sel) == 1 << 1
            yield from ack(source)

        return [
            request_m_0(), response_s_0(), transaction_s_0(),
            request_m_1(), response_s_1(), transaction_s_1(),
        ]

    run_simulation(
        dut, testbench_transaction_arbiter(),
        vcd_name=file_tmp_folder("test_transaction_arbiter.vcd"))


def test_incr():
    bus = axi.Interface()
    dut = Incr(bus.aw)

    def _test_fixed():
        yield from bus.write_aw(
            0, 0xff100, 16 - 1, burst_size(4), Burst.fixed)
        assert (yield dut.addr) == 0xff100

    def _test_incr():
        yield from bus.write_aw(
            0, 0xff101, 16 - 1, burst_size(4), Burst.incr)
        assert (yield dut.addr) == 0xff104

    def _test_wrap():
        yield from bus.write_aw(
            0, 0xff100, 16 - 1, burst_size(4), Burst.wrap)
        assert (yield dut.addr) == 0xff104
        wrap_boundary = int(0xff100 / (16 * 4)) * 16 * 4
        yield from bus.write_aw(
            0, wrap_boundary + 14 * 4, 16 - 1,
            burst_size(4), Burst.wrap)
        assert (yield dut.addr) == wrap_boundary + 15 * 4
        yield from bus.write_aw(
            0, wrap_boundary + 15 * 4, 16 - 1,
            burst_size(4), Burst.wrap)
        assert (yield dut.addr) == wrap_boundary

    def testbench_incr():
        yield bus.aw.ready.eq(1)
        yield from _test_fixed()
        yield from _test_incr()
        yield from _test_wrap()

    run_simulation(
        dut, testbench_incr(),
        vcd_name=file_tmp_folder("test_incr.vcd"))
