import ramda as R
from migen_axi.interconnect import axi4
from nmigen import *  # noqa
from nmigen.hdl.rec import DIR_FANIN, DIR_FANOUT


get_name = R.head
get_width = R.nth(1)
get_direction = R.nth(-1)
get_names = R.map(get_name)


def get_item_by_name(name):
    return R.find(R.compose(R.equals(name), get_name))


def test_axi4config():
    dut = axi4.Axi4Config(16, 32, use_region=False)
    assert dut.addr_width == 16
    assert dut.data_width == 32
    assert dut.use_ar_user is False
    assert dut.use_aw_user is False
    assert dut.use_w_user is False
    assert dut.use_b_user is False
    assert dut.use_arw_user is False
    assert dut.arw_user_width == -1
    assert dut.byte_per_word == 4


def test_axi4_aw():
    cfg = axi4.Axi4Config(16, 32, use_region=False)
    dut = axi4.axi4_aw(cfg, 0)
    assert len(dut) == 9
    assert "region" not in get_names(dut)
    assert "user" not in get_names(dut)


def test_axi4_ar():
    cfg = axi4.Axi4Config(16, 32, use_region=False, use_lock=False)
    dut = axi4.axi4_ar(cfg, 0)
    assert len(dut) == 8
    assert "region" not in get_names(dut)
    assert "lock" not in get_names(dut)


def test_axi4_arw():
    cfg = axi4.Axi4Config(16, 32, use_region=False, use_lock=False)
    dut = axi4.axi4_arw(cfg, 0)
    assert len(dut) == 9
    assert "region" not in get_names(dut)
    assert "write" in get_names(dut)
    assert R.compose(get_width, get_item_by_name("write"))(dut) == 1


def test_axi4_w():
    cfg = axi4.Axi4Config(16, 32)
    dut = axi4.axi4_w(cfg, 0)
    assert len(dut) == 3
    assert "data" in get_names(dut)
    assert "strb" in get_names(dut)
    assert "user" not in get_names(dut)
    assert R.compose(get_width, get_item_by_name("data"))(dut) == 32
    assert R.compose(get_width, get_item_by_name("last"))(dut) == 1


def test_axi4_b():
    cfg = axi4.Axi4Config(16, 32)
    dut = axi4.axi4_b(cfg, 0)
    assert len(dut) == 2
    assert "id" in get_names(dut)
    assert "resp" in get_names(dut)
    assert R.compose(get_width, get_item_by_name("resp"))(dut) == 2


def test_axi4_unburstified():
    cfg = axi4.Axi4Config(16, 32)
    dut = axi4.axi4_ax_unburstified(cfg, 0)
    assert len(dut) == 9
    assert "id" in get_names(dut)
    assert "user" not in get_names(dut)


# def test_axi4_clone_of():
#     assert axi4.clone_of(Record([("foo", 42)])).foo.nbits == 42
#     assert axi4.clone_of(Const(42)).value == 42
#     assert axi4.clone_of(Signal(42)).nbits == 42


def test_flip_layout():
    assert axi4.flip_layout([
        ("foo", 10, DIR_FANOUT),
        ("bar", 20, DIR_FANIN)]) == [
            ("foo", 10, DIR_FANIN),
            ("bar", 20, DIR_FANOUT)]
