from functools import lru_cache
from nmigen import Record, Module, Signal
from nmigen.hdl.ast import Value, Operator
import ramda as R
from .misc import DelegateRecordMixin, FragmentMixin, IDataCarrier

__all__ = ["Fraction", "DataCarrierFractionPimped"]


concat_fraction_sigs = R.concat([("last", 1)])
fraction_rec = R.compose(
    Record, concat_fraction_sigs, R.of, tuple, R.prepend("fraction"),
    R.of, R.prop("layout"))


class Fraction(DelegateRecordMixin):
    def __init__(self, data: Record) -> None:
        self.rec = fraction_rec(data)


concat_data_carrier_sigs = R.concat([("fire", 1), ("valid", 1)])
fraction_data_carrier_rec = R.compose(
    Record, concat_data_carrier_sigs,
    R.of, tuple, R.prepend("payload"), R.of, R.prop("layout"), Fraction)


class DataCarrierFractionPimped(IDataCarrier, FragmentMixin,
                                DelegateRecordMixin):
    def __init__(self, data: Record) -> None:
        self.rec = fraction_data_carrier_rec(data)
        self._m = Module()

    @property
    def fire(self):
        return self["fire"]

    @property
    def valid(self):
        return self["valid"]

    @property
    def payload(self):
        return self["payload"]

    @lru_cache(None)
    def first(self) -> Signal:
        first = Signal(reset=True)
        m = self._m
        with m.If(self.fire):
            m.d.sync += first.eq(self.payload.last)
        return first

    def tail(self) -> Operator:
        return ~self.first()

    def is_first(self) -> Operator:
        return self.valid & self.first()

    def is_tail(self) -> Operator:
        return self.valid & self.tail()

    def is_last(self) -> Operator:
        return self.valid & self.last
