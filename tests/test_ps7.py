import pytest
from migen.sim import run_simulation
from migen_misc.interconnect import Interface, wrshim
from migen_misc.cores import ps7

rec = Interface()


@pytest.mark.parametrize(
    "rec, ps_m, res",
    [
        (rec, True, dict([
            ("o_RECARADDR", rec.ar.addr),
            ("o_RECARBURST", rec.ar.burst),
            ("o_RECARCACHE", rec.ar.cache),
            ("o_RECARID", rec.ar.id),
            ("o_RECARLEN", rec.ar.len),
            ("o_RECARLOCK", rec.ar.lock),
            ("o_RECARPROT", rec.ar.prot),
            ("o_RECARQOS", rec.ar.qos),
            ("o_RECARSIZE", rec.ar.size),
            ("o_RECARVALID", rec.ar.valid),
            ("o_RECAWADDR", rec.aw.addr),
            ("o_RECAWBURST", rec.aw.burst),
            ("o_RECAWCACHE", rec.aw.cache),
            ("o_RECAWID", rec.aw.id),
            ("o_RECAWLEN", rec.aw.len),
            ("o_RECAWLOCK", rec.aw.lock),
            ("o_RECAWPROT", rec.aw.prot),
            ("o_RECAWQOS", rec.aw.qos),
            ("o_RECAWSIZE", rec.aw.size),
            ("o_RECAWVALID", rec.aw.valid),
            ("o_RECBREADY", rec.b.ready),
            ("o_RECRREADY", rec.r.ready),
            ("o_RECWDATA", rec.w.data),
            ("o_RECWID", rec.w.id),
            ("o_RECWLAST", rec.w.last),
            ("o_RECWSTRB", rec.w.strb),
            ("o_RECWVALID", rec.w.valid),
            ("i_RECARREADY", rec.ar.ready),
            ("i_RECAWREADY", rec.aw.ready),
            ("i_RECBID", rec.b.id),
            ("i_RECBRESP", rec.b.resp),
            ("i_RECBVALID", rec.b.valid),
            ("i_RECRDATA", rec.r.data),
            ("i_RECRID", rec.r.id),
            ("i_RECRLAST", rec.r.last),
            ("i_RECRRESP", rec.r.resp),
            ("i_RECRVALID", rec.r.valid),
            ("i_RECWREADY", rec.w.ready)])),
        (rec, False, dict([
            ("i_RECARADDR", rec.ar.addr),
            ("i_RECARBURST", rec.ar.burst),
            ("i_RECARCACHE", rec.ar.cache),
            ("i_RECARID", rec.ar.id),
            ("i_RECARLEN", rec.ar.len),
            ("i_RECARLOCK", rec.ar.lock),
            ("i_RECARPROT", rec.ar.prot),
            ("i_RECARQOS", rec.ar.qos),
            ("i_RECARSIZE", rec.ar.size),
            ("i_RECARVALID", rec.ar.valid),
            ("i_RECAWADDR", rec.aw.addr),
            ("i_RECAWBURST", rec.aw.burst),
            ("i_RECAWCACHE", rec.aw.cache),
            ("i_RECAWID", rec.aw.id),
            ("i_RECAWLEN", rec.aw.len),
            ("i_RECAWLOCK", rec.aw.lock),
            ("i_RECAWPROT", rec.aw.prot),
            ("i_RECAWQOS", rec.aw.qos),
            ("i_RECAWSIZE", rec.aw.size),
            ("i_RECAWVALID", rec.aw.valid),
            ("i_RECBREADY", rec.b.ready),
            ("i_RECRREADY", rec.r.ready),
            ("i_RECWDATA", rec.w.data),
            ("i_RECWID", rec.w.id),
            ("i_RECWLAST", rec.w.last),
            ("i_RECWSTRB", rec.w.strb),
            ("i_RECWVALID", rec.w.valid),
            ("o_RECARREADY", rec.ar.ready),
            ("o_RECAWREADY", rec.aw.ready),
            ("o_RECBID", rec.b.id),
            ("o_RECBRESP", rec.b.resp),
            ("o_RECBVALID", rec.b.valid),
            ("o_RECRDATA", rec.r.data),
            ("o_RECRID", rec.r.id),
            ("o_RECRLAST", rec.r.last),
            ("o_RECRRESP", rec.r.resp),
            ("o_RECRVALID", rec.r.valid),
            ("o_RECWREADY", rec.w.ready)])),
    ])
def test_connect_interface(rec, ps_m, res):
    assert ps7.connect_interface(rec, ps_m) == res


def test_axi_wrshim():
    dut = wrshim.AxiWrshim()

    def testbench_wrshim(wrshim):
        i, o = dut.m_axi_i, dut.m_axi_o
        assert (yield o.aw.valid) == 0
        assert (yield i.aw.ready) == 0
        assert (yield o.w.valid) == 0
        assert (yield i.w.ready) == 0
        yield i.aw.valid.eq(1)
        yield o.aw.ready.eq(1)
        yield i.w.last.eq(1)
        yield
        assert (yield o.aw.valid) == 1
        assert (yield i.aw.ready) == 1
        assert (yield o.w.valid) == 0
        assert (yield i.w.ready) == 0
        yield o.w.ready.eq(1)
        yield
        assert (yield o.aw.valid) == 1
        assert (yield i.aw.ready) == 1
        assert (yield o.w.valid) == 0
        assert (yield i.w.ready) == 1
        yield i.w.valid.eq(1)
        yield
        assert (yield o.aw.valid) == 1
        assert (yield i.aw.ready) == 1
        assert (yield o.w.valid) == 1
        assert (yield i.w.ready) == 1
        yield i.aw.valid.eq(0)
        yield i.w.valid.eq(0)
        yield
        assert (yield o.aw.valid) == 0
        assert (yield i.aw.ready) == 1
        assert (yield o.w.valid) == 0
        assert (yield i.w.ready) == 1
        yield i.aw.addr.eq(0x5550)
        yield i.w.strb.eq(0x1)
        yield
        assert (yield o.aw.addr) == 0x5550
        assert (yield o.aw.size) == 0x0
        yield i.w.strb.eq(0x2)
        yield
        assert (yield o.aw.addr) == 0x5551
        assert (yield o.aw.size) == 0x0
        yield i.w.strb.eq(0x4)
        yield
        assert (yield o.aw.addr) == 0x5552
        assert (yield o.aw.size) == 0x0
        yield i.w.strb.eq(0x8)
        yield
        assert (yield o.aw.addr) == 0x5553
        assert (yield o.aw.size) == 0x0
        yield i.w.strb.eq(0x3)
        yield
        assert (yield o.aw.addr) == 0x5550
        assert (yield o.aw.size) == 0x1
        yield i.w.strb.eq(0xc)
        yield
        assert (yield o.aw.addr) == 0x5552
        assert (yield o.aw.size) == 0x1
        yield i.aw.size.eq(0x2)
        yield i.w.strb.eq(0x0)
        yield
        assert (yield o.aw.addr) == 0x5550
        assert (yield o.aw.size) == 0x2

    run_simulation(dut, testbench_wrshim(dut),
                   vcd_name="wrshim.vcd")


def test_axi_inteface_like():
    rec = Interface(data_width=64)
    assert len(Interface.like(rec).w.data) == 64


def test_connect_s_axi():
    rec = Interface()
    assert len(ps7.connect_s_axi(rec)["i_RECAWSIZE"]) == 2
    assert len(ps7.connect_s_axi(rec)["i_RECARSIZE"]) == 2


def test_connect_m_axi():
    rec = Interface()
    assert len(ps7.connect_m_axi(rec)["o_RECAWADDR"]) == 32
    assert len(ps7.connect_m_axi(rec)["o_RECAWSIZE"]) == 2
    assert len(ps7.connect_m_axi(rec)["o_RECARSIZE"]) == 2
