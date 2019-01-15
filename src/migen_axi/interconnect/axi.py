from types import SimpleNamespace
from enum import Enum
import operator
import math
from toolz.curried import *  # noqa
import ramda as R
from migen import *  # noqa
from migen.genlib import roundrobin
from migen.genlib import coding
from migen.genlib.record import set_layout_parameters
from misoc.interconnect import stream

__all__ = ["Burst", "Alock", "Response",
           "burst_size", "rec_layout",
           "connect_sink_hdshk", "connect_source_hdshk",
           "Interface", "InterconnectPointToPoint", "Incr"]

Burst = Enum("Burst", "fixed incr wrap reserved", start=0)

Alock = Enum("Alock", "normal_access exclusive_access", start=0)

Response = Enum("Response", "okay exokay slverr decerr", start=0)

burst_size = comp(int, math.log2)

_layout = [
    # write address channel signals
    ("aw", [
        ("id", "id_width", DIR_M_TO_S),  # write address ID
        ("addr", "addr_width", DIR_M_TO_S),  # write address
        ("len", 8, DIR_M_TO_S),  # burst length
        ("size", 3, DIR_M_TO_S),  # burst size
        ("burst", 2, DIR_M_TO_S),  # burst type
        ("lock", 2, DIR_M_TO_S),  # lock type
        ("cache", 4, DIR_M_TO_S),  # memory type
        ("prot", 3, DIR_M_TO_S),  # protection type
        ("qos", 4, DIR_M_TO_S),  # QoS
        ("valid", 1, DIR_M_TO_S),  # write address valid
        ("ready", 1, DIR_S_TO_M),  # write address ready
    ]),
    # write data channel signals
    ("w", [
        ("id", "id_width", DIR_M_TO_S),  # write ID tag
        ("data", "data_width", DIR_M_TO_S),  # write data
        ("strb", "wstrb_width", DIR_M_TO_S),  # write strobes
        ("last", 1, DIR_M_TO_S),  # write last
        ("valid", 1, DIR_M_TO_S),  # write valid
        ("ready", 1, DIR_S_TO_M),  # write ready
    ]),
    # write response channel signals
    ("b", [
        ("id", "id_width", DIR_S_TO_M),  # response ID tag
        ("resp", 2, DIR_S_TO_M),  # write response
        ("valid", 1, DIR_S_TO_M),  # write response valid
        ("ready", 1, DIR_M_TO_S),  # response ready
    ]),
    # read address channel signals
    ("ar", [
        ("id", "id_width", DIR_M_TO_S),  # read address ID
        ("addr", "addr_width", DIR_M_TO_S),  # read address
        ("len", 8, DIR_M_TO_S),  # burst length
        ("size", 3, DIR_M_TO_S),  # burst size
        ("burst", 2, DIR_M_TO_S),  # burst type
        ("lock", 2, DIR_M_TO_S),  # lock type
        ("cache", 4, DIR_M_TO_S),  # memory type
        ("prot", 3, DIR_M_TO_S),  # protection type
        ("qos", 4, DIR_M_TO_S),  # QoS
        ("valid", 1, DIR_M_TO_S),  # read address valid
        ("ready", 1, DIR_S_TO_M),  # read address ready
    ]),
    # read data channel signals
    ("r", [
        ("id", "id_width", DIR_S_TO_M),  # read ID tag
        ("data", "data_width", DIR_S_TO_M),  # read data
        ("resp", 2, DIR_S_TO_M),  # read response
        ("last", 1, DIR_S_TO_M),  # read last
        ("valid", 1, DIR_S_TO_M),  # read valid
        ("ready", 1, DIR_M_TO_S),  # read ready
    ]),
]


def read_ready(ch):
    while (yield ch.valid) == 0:
        yield


def read_ack(ch):
    if (yield ch.ready) == 1:
        pass
    else:
        yield ch.ready.eq(1)
        yield
        yield ch.ready.eq(0)


def write_ack(ch):
    yield ch.valid.eq(1)
    yield
    while (yield ch.ready) == 0:
        yield

    yield ch.valid.eq(0)


def connect_sink_hdshk(ch, sink):
    return [
        sink.stb.eq(ch.valid),
        ch.ready.eq(sink.ack),
    ]


def connect_source_hdshk(ch, source):
    return [
        ch.valid.eq(source.stb),
        source.ack.eq(ch.ready),
    ]


def rec_layout(rec, items):
    return pipe(
        rec.layout,
        filter(comp(partial(operator.contains, items), first)), list)


def read_attrs(ch):
    yield from read_ready(ch)
    ns = SimpleNamespace()
    for name, *_ in ch.layout:
        setattr(ns, name, (yield getattr(ch, name)))
    yield from read_ack(ch)
    yield
    return ns


class Interface(Record):
    def __init__(self, data_width=32, addr_width=32, id_width=12, name=None):
        self.addr_width = addr_width
        self.data_width = data_width
        self.id_width = id_width
        super().__init__(
            set_layout_parameters(
                _layout, data_width=data_width, addr_width=addr_width,
                wstrb_width=data_width // 8, id_width=id_width), name=name)

    @staticmethod
    def like(other, name=None):
        return pipe(
            other,
            operator.attrgetter("data_width", "addr_width", "id_width"),
            R.apply(partial(Interface, name=name)))

    def write_aw(self, id_, addr, len_, size, burst,
                 lock=Alock.normal_access.value, cache=0,
                 prot=0, qos=0):
        yield self.aw.id.eq(id_)
        yield self.aw.addr.eq(addr)
        yield self.aw.len.eq(len_)
        yield self.aw.size.eq(size)
        yield self.aw.burst.eq(burst)
        yield self.aw.lock.eq(lock)
        yield self.aw.cache.eq(cache)
        yield self.aw.prot.eq(prot)
        yield self.aw.prot.eq(qos)
        yield from write_ack(self.aw)

    def read_aw(self):
        return read_attrs(self.aw)

    def write_w(self, id_, data, strb=None, last=1):
        yield self.w.id.eq(id_)
        yield self.w.data.eq(data)
        yield self.w.strb.eq(
            2**len(self.w.strb) - 1 if strb is None else strb)
        yield self.w.last.eq(last)
        yield from write_ack(self.w)

    def read_w(self):
        return read_attrs(self.w)

    def read_b(self):
        return read_attrs(self.b)

    def write_b(self, id_, resp=Response.okay.value):
        yield self.b.id.eq(id_)
        yield self.b.resp.eq(resp)
        yield from write_ack(self.b)

    def write_ar(self, id_, addr, len_, size, burst,
                 lock=Alock.normal_access.value, cache=0,
                 prot=0, qos=0):
        yield self.ar.id.eq(id_)
        yield self.ar.addr.eq(addr)
        yield self.ar.len.eq(len_)
        yield self.ar.size.eq(size)
        yield self.ar.burst.eq(burst)
        yield self.ar.lock.eq(lock)
        yield self.ar.cache.eq(cache)
        yield self.ar.prot.eq(prot)
        yield self.ar.prot.eq(qos)
        yield from write_ack(self.ar)

    def read_ar(self):
        return read_attrs(self.ar)

    def write_r(self, id_, data, resp=Response.okay.value, last=0):
        yield self.r.id.eq(id_)
        yield self.r.data.eq(data)
        yield self.r.resp.eq(resp)
        yield self.r.last.eq(last)
        yield from write_ack(self.r)

    def read_r(self):
        return read_attrs(self.r)


class InterconnectPointToPoint(Module):
    def __init__(self, master, slave):
        self.comb += master.connect(slave)


class Incr(Module):
    ""
    def __init__(self, a_chan, data_width=32):
        self.addr = Signal.like(a_chan.addr)
        assert len(a_chan.addr) >= 12

        ###

        byte_per_word = data_width // 8

        max_size = bits_for(byte_per_word)
        valid_size_width = bits_for(max_size) + 1
        valid_size = a_chan.size[:valid_size_width]

        high_cat = a_chan.addr[12:] if len(a_chan.addr) > 12 else C(0)
        base = Signal(12)
        size_value = Signal(byte_per_word)
        base_incr = Signal.like(base)
        align_msk = Signal(12)
        self.comb += [s.eq(i < valid_size) for i, s
                      in enumerate(align_msk[:max_size - 1])]
        wrap_case_len = Signal(max=3)
        # 3 is the maximum of wrap_case_len
        wrap_case_max = max_size + 3
        wrap_case_width = bits_for(wrap_case_max + 1)
        wrap_case = Signal(wrap_case_width)
        wrap_a = Array(Signal(12) for _ in range(wrap_case_max))

        self.comb += [
            base.eq(a_chan.addr[:12] & ~align_msk),
            # size_value
            Case(
                valid_size,
                {i: size_value.eq(1 << i)
                 for i in range(max_size)}),
            base_incr.eq(base + size_value),
            # wrap_cap_case_len
            If(a_chan.len[3], wrap_case_len.eq(3))
            .Elif(a_chan.len[2], wrap_case_len.eq(2))
            .Elif(a_chan.len[1], wrap_case_len.eq(1))
            .Else(wrap_case_len.eq(0)),
            wrap_case.eq(valid_size[:wrap_case_width] + wrap_case_len),
            Case(
                a_chan.burst,
                {
                    Burst.fixed.value: self.addr.eq(a_chan.addr),
                    Burst.wrap.value: [
                        Case(
                            wrap_case,
                            {i: wrap_a[i].eq(
                                Cat(base_incr[:i + 1], base[1 + i:]))
                                for i in range(wrap_case_max)}),
                        self.addr.eq(Cat(wrap_a[wrap_case], high_cat))],
                    "default": self.addr.eq(Cat(base_incr, high_cat))})]


class AddressDecoder(Module):
    # slaves is a list of pairs:
    # 0) function that takes the address signal and returns a FHDL expression
    #    that evaluates to 1 when the slave is selected and 0 otherwise.
    # 1) axi.a[rw] reference.
    # register adds flip-flops after the address comparators. Improves timing,
    # but breaks Wishbone combinatorial feedback.
    def __init__(self, master, slaves, register=False):
        ns = len(slaves)
        slave_sel = Signal(ns)
        self.slave_sel_r = Signal(ns)

        ###

        # decode slave addresses
        self.comb += [slave_sel[i].eq(fn(master.addr))
                      for i, (fn, _) in enumerate(slaves)]
        if register:
            self.sync += self.slave_sel_r.eq(slave_sel)
        else:
            self.comb += self.slave_sel_r.eq(slave_sel)

        # connect master->slaves signals
        for _, slave in slaves:
            for dest, source in [(getattr(slave, name),
                                  getattr(master, name)) for
                                 name, _, direction in master.layout
                                 if direction == DIR_M_TO_S and
                                 name != "valid"]:
                self.comb += dest.eq(source)

        # combine valid w/ slave selection signals
        self.comb += [slave.valid.eq(master.valid & slave_sel[i])
                      for i, (_, slave) in enumerate(slaves)]

        # generate master ready
        self.comb += master.ready.eq(
            reduce(operator.or_, [
                slave.ready & slave_sel[i]
                for i, (_, slave) in enumerate(slaves)]))


_transaction_layout = [("sel", "n")]


class TransactionArbiter(Module):
    # slaves is a list of pairs:
    # 0) function that takes the address signal and returns a FHDL expression
    #    that evaluates to 1 when the slave is selected and 0 otherwise.
    # 1) axi.a[rw] reference.
    def __init__(self, masters, slaves, npending=8, register=False):
        r_transactionFIFO = partial(
            stream.SyncFIFO,
            set_layout_parameters(_transaction_layout, n=len(slaves)),
            npending)
        w_transactionFIFO = partial(
            stream.SyncFIFO,
            set_layout_parameters(_transaction_layout, n=len(masters)),
            npending)
        self.r_transaction = [r_transactionFIFO() for _ in masters]
        self.w_transaction = [w_transactionFIFO() for _ in slaves]

        ###

        self.submodules += self.r_transaction
        self.submodules += self.w_transaction
        target = Interface()
        self.submodules.ar_rr = roundrobin.RoundRobin(len(masters))
        self.submodules.aw_rr = roundrobin.RoundRobin(len(masters))
        self.submodules.ar_dec = AddressDecoder(
            target.ar, [(fn, slave.ar) for (fn, slave) in slaves], register)
        self.submodules.aw_dec = AddressDecoder(
            target.aw, [(fn, slave.aw) for (fn, slave) in slaves], register)

        # mux master->slave signals
        for name in [name for name, _, direction in target.ar.layout
                     if direction == DIR_M_TO_S]:
            choices = Array(getattr(m.ar, name) for m in masters)
            self.comb += getattr(target.ar, name).eq(choices[self.ar_rr.grant])
        for name in [name for name, _, direction in target.aw.layout
                     if direction == DIR_M_TO_S]:
            choices = Array(getattr(m.aw, name) for m in masters)
            self.comb += getattr(target.aw, name).eq(choices[self.aw_rr.grant])

        # connect slave->master signal
        self.comb += [
            master.ar.ready.eq(
                target.ar.ready &
                # FIFO writable?
                fifo.sink.ack &
                (self.ar_rr.grant == i)) for i, (master, fifo) in
            enumerate(zip(masters, self.r_transaction))]
        w_transaction_ack = Signal()
        self.comb += w_transaction_ack.eq(
            reduce(
                operator.or_,
                Cat(*[fifo.sink.ack for fifo in self.w_transaction]) &
                self.aw_dec.slave_sel_r))
        self.comb += [
            master.aw.ready.eq(
                target.aw.ready &
                # FIFO writable?
                w_transaction_ack &
                (self.aw_rr.grant == i)) for i, master in enumerate(masters)]

        # connect bus requests to round-robin selector
        ar_reqs = [
            master.ar.valid & ~master.ar.ready for master in masters]
        aw_reqs = [
            master.aw.valid & ~master.aw.ready for master in masters]
        self.comb += [
            self.ar_rr.request.eq(Cat(*ar_reqs)),
            self.aw_rr.request.eq(Cat(*aw_reqs)),
        ]

        # connect transaction sinks
        aw_acked = Signal()
        self.comb += [
            Cat(*[fifo.sink.stb for fifo in self.r_transaction]).eq(
                Cat(*[ar.valid & ar.ready for
                      ar in [master.ar for master in masters]])),
            aw_acked.eq(target.aw.valid & target.aw.ready),
            Cat(*[fifo.sink.stb for fifo in self.w_transaction]).eq(
                Replicate(aw_acked, len(slaves)) & self.aw_dec.slave_sel_r)
        ]
        self.comb += [
            fifo.sink.sel.eq(self.ar_dec.slave_sel_r) for
            fifo in self.r_transaction]
        self.submodules.decoder = coding.Decoder(len(masters))
        self.comb += self.decoder.i.eq(self.aw_rr.grant)
        self.comb += [
            fifo.sink.sel.eq(self.decoder.o) for
            fifo in self.w_transaction]
