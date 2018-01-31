from types import SimpleNamespace
import tempfile
from os import path
from toolz import partial

__all__ = ["write_ack", "wait_stb", "ack", "csr_w_mon", "file_tmp_folder"]


def write_ack(sink):
    yield sink.stb.eq(1)
    yield
    while (yield sink.ack) == 0:
        yield

    yield sink.stb.eq(0)


def wait_stb(source):
    while (yield source.stb) == 0:
        yield


def ack(source):
    yield source.ack.eq(1)
    yield
    yield source.ack.eq(0)


def csr_w_mon(csr_bus):
    while (yield csr_bus.we) == 0:
        yield

    ns = SimpleNamespace()
    ns.adr = (yield csr_bus.adr)
    ns.dat_w = (yield csr_bus.dat_w)
    yield
    return ns


file_tmp_folder = partial(path.join, tempfile.gettempdir())
