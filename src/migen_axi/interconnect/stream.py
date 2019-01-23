from typing import Optional
import ramda as R  # noqa
from nmigen import *  # noqa
from nmigen.hdl.ast import Operator
from .misc import DelegateRecordMixin, FragmentMixin, clone_of, IMasterSlave, \
    IDataCarrier
from .fraction import Fraction

__all__ = ["Stream"]

concat_stream_sigs = R.concat([("valid", 1), ("ready", 1)])
stream_rec = R.compose(
    Record, concat_stream_sigs, R.of, tuple, R.prepend("payload"),
    R.of, R.prop("layout"))


class Stream(IMasterSlave, IDataCarrier, DelegateRecordMixin, FragmentMixin):
    def __init__(self, data: Record):
        self.rec = stream_rec(data)
        self._m = Module()

    @property
    def payload(self):
        return self["payload"]

    @property
    def valid(self):
        return self["valid"]

    def clone(self) -> "Stream":
        return Stream(self.payload)

    def free_run(self) -> "Stream":
        m = self._m
        m.d.comb += self.ready.eq(1)
        return self

    def __lshift__(self, other: "Stream") -> "Stream":
        return self.connnect_from(other)

    def __rshift__(self, other: "Stream") -> "Stream":
        other << self
        return other

    def lt_dash_lt(self, other: "Stream") -> "Stream":
        self << other.stage()
        return other

    def gt_dash_gt(self, other: "Stream") -> "Stream":
        return other.lt_dash_lt(self)

    def is_stall(self) -> Operator:
        return self.valid & ~self.ready

    def is_new(self) -> Operator:
        m = self._m
        is_stall_r = Signal()
        m.d.sync += is_stall_r.eq(self.is_stall())
        return self.valid & ~is_stall_r

    def fire(self) -> Operator:
        return self.valid & self.ready

    def is_free(self) -> Operator:
        return ~self.valid & self.ready

    def connnect_from(self, other) -> "Stream":
        assert self.is_master_interface is False
        self._m.d.comb += [
            self.valid.eq(other.valid),
            other.ready.eq(self.ready),
            self.payload.eq(other.payload)]
        return other

    def stage(self) -> "Stream":
        return self.m2s_pipe()

    def m2s_pipe(self, collapse_bubble: bool = True,
                 flush: Optional[bool] = None) -> "Stream":
        ret = self.clone()
        r_valid = Signal()
        r_data = clone_of(self.payload)
        r_data.name = "m2s_pipe"
        m = self._m
        m.d.comb += self.ready.eq(
            (Const(collapse_bubble) & ~ret.valid) | ret.ready)
        with m.If(self.ready):
            m.d.sync += r_data.eq(self.payload)
        if flush is not None:
            with m.If(flush):
                m.d.sync += r_valid.eq(0)
            with m.Else():
                m.d.sync += r_valid.eq(self.valid)
        else:
            m.d.comb += r_valid.eq(self.valid)
        m.d.comb += [ret.valid.eq(r_valid), ret.payload.eq(self.payload)]
        return ret

    def _s2m_pipe(self) -> Record:
        ret = clone_of(self.payload)
        r_valid = Signal()
        r_bits = clone_of(self.payload)
        m = self._m
        w.d.comb += [
            ret.ready.eq(self.valid | self.r_valid),
            self.ready.eq(~r_valid),
            ret.payload.eq(Mux(r_valid, r_bits, self.payload))]
        with m.If(ret.ready):
            m.d.sync += r_valid.eq(0)
        with m.Else():
            m.d.sync += [
                r_valid.eq(self.valid),
                r_bits.eq(self.payload)]
        return ret

    def s2m_pipe(self, stages_count: int = 1) -> Record:
        if stages_count == 0:
            return self
        else:
            return self._s2m_pipe().s2m_pipe(stages_count - 1)

    def valid_pipe(self) -> "Stream":
        sink = self.clone()
        valid_r = Signal()
        m = self._m
        with m.If(self.valid):
            m.d.sync += valid_r.eq(1)
        with m.Elif(sink.fire()):
            m.d.sync += valid_r.eq(0)
        m.d.comb += [
            sink.valid.eq(valid_r),
            sink.payload.eq(self.payload)]
        return sink

    def half_pipe(self) -> "Stream":
        ret = Stream(clone_of(self.payload))
        ret.name = "half_pipe"
        regs = Record([
            ("valid", 1),
            ("ready", 1),
            ("payload", self.payload.layout)])
        regs.ready.reset = 1
        m = self._m
        with m.If(~regs.valid):
            m.d.sync += [
                regs.valid.eq(self.valid),
                regs.ready.eq(self.ready),
                regs.payload.eq(self.payload)]
        with m.Else():
            m.d.sync += [
                regs.valid.eq(~ret.ready),
                regs.ready.eq(ret.ready)]
        m.d.comb += [
            ret.valid.eq(regs.valid),
            ret.payload.eq(regs.payload),
            self.ready.eq(regs.ready)]
        return ret

    def continue_when(self, cond: Value) -> "Stream":
        next = self.clone()
        m = self._m
        m.d.comb += [
            next.valid.eq(self.valid & cond),
            self.ready.eq(next.ready & cond),
            next.payload.eq(self.payload)]
        return next

    def throw_when(self, cond: Value) -> "Stream":
        m = self._m
        next = self.clone()
        next.slave()
        next << self
        with m.If(cond):
            m.d.comb += [
                next.valid.eq(0),
                self.ready.eq(1)]
        return next

    def halt_when(self, cond: Value) -> "Stream":
        return self.continue_when(~cond)

    def take_when(self, cond: Value) -> "Stream":
        return self.throw_when(~cond)

    def fraction_transaction(self, width: int) -> "Stream":
        raise NotImplementedError()

    def add_fraction_last(self, last: Value) -> "Stream":
        ret = Stream(Fraction(self.payload).rec)
        m = self._m
        m.d.comb += [
            ret.valid.eq(self.valid),
            self.ready.eq(ret.ready),
            ret.payload.last.eq(last),
            ret.payload.fraction.eq(self.payload)]
        return ret
