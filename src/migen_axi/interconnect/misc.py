from abc import ABCMeta, abstractmethod
from typing import Optional
from nmigen import Const, Record, Signal, Fragment
from nmigen.hdl.ast import Operator, Value
import ramda as R

__all__ = ["DelegateRecordMixin", "FragmentMixin", "clone_of",
           "IMasterSlave", "IDataCarrier"]


class DelegateRecordMixin:
    def __getattr__(self, name):
        return self[name]

    def __getitem__(self, name):
        return getattr(self.rec, name)

    def __iter__(self):
        for name, *_ in self.rec.layout:
            yield getattr(self, name)


class FragmentMixin:
    """Mixin for ``get_fragment``.
    """
    def get_fragment(self, platform: Optional = None) -> Fragment:
        return self._m.lower(platform)


clone_of = R.cond([
    (R.is_(Record), R.compose(Record, R.prop("layout"))),
    (R.is_(Const), R.compose(
        R.apply(Const), R.juxt([
            R.invoker(0, "_as_const"), R.prop("value")]))),
    (R.is_(Signal), Signal.like)])


class IMasterSlave(metaclass=ABCMeta):
    def as_master(self) -> None: pass  # noqa

    def as_slave(self) -> None: pass  # noqa

    def master(self):
        self.as_master()
        self.is_master_interface = True

    def slave(self):
        self.as_slave()
        self.is_master_interface = False


class IDataCarrier(metaclass=ABCMeta):
    @property
    @abstractmethod
    def fire(self) -> Operator:
        pass

    @property
    @abstractmethod
    def valid(self) -> Value:
        pass

    @property
    @abstractmethod
    def payload(self) -> Record:
        pass

    def free_run(self) -> "IDataCarrier":
        return self
