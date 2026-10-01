import pytest
from migen_axi.interconnect import Interface
from migen_axi.cores import ps8

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
    assert ps8.connect_interface(rec, ps_m) == res


def test_connect_m_axi_drops_wid_only():
    rec = Interface()
    result = ps8.connect_m_axi(rec)
    # PS8's AXI4 ports have no per-beat write-data ID pin ...
    assert "o_RECWID" not in result
    # ... but AWID (write *address* ID) is a real AXI4 field and must stay
    # connected. A naive "endswith('WID')" string filter would also catch
    # "RECAWID" here -- guard against that regression.
    assert "o_RECAWID" in result
    assert result["o_RECAWID"] is rec.aw.id
    assert "o_RECARID" in result
    assert set(result) == set(ps8.connect_interface(rec, True)) - {"o_RECWID"}


def test_connect_s_axi_drops_wid_only():
    rec = Interface()
    result = ps8.connect_s_axi(rec)
    assert "i_RECWID" not in result
    assert "i_RECAWID" in result
    assert result["i_RECAWID"] is rec.aw.id
    assert "i_RECARID" in result
    assert set(result) == set(ps8.connect_interface(rec, False)) - {"i_RECWID"}


def test_connect_m_axi_does_not_truncate_size():
    # unlike PS7 (AXI3, 2-bit ARSIZE/AWSIZE), PS8's ports are full AXI4 with
    # 3-bit AR/AWSIZE on every port -- no truncation should be applied.
    rec = Interface()
    assert len(ps8.connect_m_axi(rec)["o_RECAWSIZE"]) == 3
    assert len(ps8.connect_m_axi(rec)["o_RECARSIZE"]) == 3


def test_connect_s_axi_does_not_truncate_size():
    rec = Interface()
    assert len(ps8.connect_s_axi(rec)["i_RECAWSIZE"]) == 3
    assert len(ps8.connect_s_axi(rec)["i_RECARSIZE"]) == 3


def test_connect_m_axi_preserves_wide_addr():
    # PS8's own GP AXI ports are wider than the generic Interface() default
    # (e.g. 40-bit addr_width on M_AXI_HPM*_FPD/LPD) -- confirm addr width
    # passes through untouched, since ps8.py (unlike ps7.py) has no
    # truncation logic at all to interfere with it.
    rec = Interface(addr_width=40, id_width=16)
    assert len(ps8.connect_m_axi(rec)["o_RECAWADDR"]) == 40


def test_ps8_elaborates():
    # smoke test: building the Instance("PS8", ...) kwargs must not raise
    # (e.g. from a duplicate key across the merged connect_interface() dicts)
    from migen.fhdl.verilog import convert

    dut = ps8.PS8()
    convert(dut)
