from toolz.curried import *  # noqa
from misoc.interconnect import stream
from migen_misc.interconnect import *  # noqa
from .common import write_ack, wait_stb, file_tmp_folder
from migen.sim import run_simulation


def write_data(sink, val, eop=None):
    yield sink.data.eq(val)
    if eop:
        yield sink.eop.eq(1)
    yield from write_ack(sink)
    if eop:
        yield sink.eop.eq(0)


def request_addr(sink, addr, eop=None):
    yield sink.addr.eq(addr)
    if eop:
        yield sink.eop.eq(1)
    yield from write_ack(sink)
    if eop:
        yield sink.eop.eq(0)


def read_data(source):
    yield from wait_stb(source)
    return (yield source.data)


def test_upscaler():
    i = axi.Interface()
    dw = i.data_width
    dut = stream.Converter(8, dw)
    source, sink = dut.source, dut.sink
    write = partial(write_data, sink)
    read = partial(read_data, source)

    def testbench_upscaler():

        def push():
            yield from write(0x11)
            yield from write(0x22)
            yield from write(0x33)
            yield from write(0x44)
            yield from write(0x55)
            yield from write(0x66)
            yield from write(0x77)
            yield from write(0x88)
            yield from write(0x99, eop=1)

        def pull():
            yield source.ack.eq(1)
            assert (yield from read()) == 0x44332211
            yield
            assert (yield from read()) == 0x88776655
            yield
            assert (yield from read()) & 0xff == 0x99

        return [
            push(), pull(),
        ]

    run_simulation(dut, testbench_upscaler())


def test_downscaler():
    i = axi.Interface()
    dw = i.data_width
    dut = stream.Converter(dw, 8)
    source, sink = dut.source, dut.sink
    write = partial(write_data, sink)
    read = partial(read_data, source)

    def testbench_downscaler():

        def push():
            yield from write(0x44332211)
            yield from write(0x88776655, eop=True)

        def pull():
            yield source.ack.eq(1)
            assert (yield from read()) == 0x11
            yield
            assert (yield from read()) == 0x22
            yield
            assert (yield from read()) == 0x33
            yield
            assert (yield from read()) == 0x44
            yield
            assert (yield from read()) == 0x55
            yield
            assert (yield from read()) == 0x66
            yield
            assert (yield from read()) == 0x77
            yield
            assert (yield from read()) == 0x88
            assert (yield source.eop) == 1

        return [
            push(), pull(),
        ]

    run_simulation(
        dut, testbench_downscaler(),
        vcd_name=file_tmp_folder("test_downscaler.vcd"))


def test_reader_integration():
    i = axi.Interface()
    dw = i.data_width
    dut = Reader(i)
    dut.submodules.downscaler = stream.Converter(dw, 8)
    dut.comb += dut.source.connect(dut.downscaler.sink)

    source, sink = dut.downscaler.source, dut.sink
    request = partial(request_addr, sink)
    read = partial(read_data, source)

    def tesetbench_reader_integration():

        def push_addr():
            yield from request(0x11223344, eop=True)

        def pull_data():
            yield source.ack.eq(1)
            assert (yield from read()) == 0x04
            yield
            assert (yield from read()) == 0x03
            yield
            assert (yield from read()) == 0x02
            yield
            assert (yield from read()) == 0x01
            assert (yield source.eop) == 1

        def ar_and_r_channel():
            assert (yield from i.read_ar()).addr == 0x11223344
            yield from i.write_r(0x55, 0x01020304, last=1)

        return [
            push_addr(), pull_data(), ar_and_r_channel(),
        ]

    run_simulation(
        dut, tesetbench_reader_integration(),
        vcd_name=file_tmp_folder("test_reader_integration.vcd"))
