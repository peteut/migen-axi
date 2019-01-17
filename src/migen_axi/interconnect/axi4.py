from .axi import Burst, Alock, Response
import typing
import ramda as R
from migen import *  # noqa
from misoc.interconnect import stream

__all__ = ["Axi4Config", "axi4_aw", "axi4_ar", "axi4_arw",
           "axi4_w", "axi4_b", "axi4_r"]


class Axi4Config(typing.NamedTuple):
    """Configuration for the Axi4 bus
    """
    addr_width: int
    data_width: int
    id_width: int = -1
    use_id: bool = True
    use_region: bool = True
    use_burst: bool = True
    use_lock: bool = True
    use_cache: bool = True
    use_size: bool = True
    use_qos: bool = True
    use_len: bool = True
    use_last: bool = True
    use_resp: bool = True
    use_prot: bool = True
    use_strb: bool = True
    ar_user_width: int = -1
    aw_user_width: int = -1
    r_user_width: int = -1
    w_user_width: int = -1
    b_user_width: int = -1

    @property
    def use_ar_user(self) -> bool:
        return self.ar_user_width >= 0

    @property
    def use_aw_user(self) -> bool:
        return self.aw_user_width >= 0

    @property
    def use_r_user(self) -> bool:
        return self.r_user_width >= 0

    @property
    def use_w_user(self) -> bool:
        return self.w_user_width >= 0

    @property
    def use_b_user(self) -> bool:
        return self.b_user_width >= 0

    @property
    def use_arw_user(self) -> int:
        return self.arw_user_width >= 0  # Shared AR/AW channel

    @property
    def arw_user_width(self) -> int:
        return max(self.ar_user_width, self.aw_user_width)

    @property
    def byte_per_word(self) -> int:
        return self.data_width // 8


m2s, s2m = R.append(DIR_M_TO_S), R.append(DIR_S_TO_M)
if_else_none = R.if_else(R.__, R.__, R.always(None))
filter_nil = R.reject(R.is_nil)
two_ary = R.curry(R.n_ary(2, R.unapply(R.identity)))
namedtuple2map = R.invoker(0, "_asdict")

axi4_ax = R.compose(
    filter_nil,
    R.juxt([
        R.compose(m2s, R.prepend("addr"), R.of, R.path([0, "addr_width"])),
        if_else_none(
            R.path([0, "use_id"]),
            R.compose(m2s, R.prepend("id"), R.of, R.path([0, "id_width"]))),
        if_else_none(
            R.path([0, "use_region"]),
            R.compose(m2s, R.prepend("region"), R.always([4]))),
        if_else_none(
            R.path([0, "use_len"]),
            R.compose(m2s, R.prepend("len"), R.always([8]))),
        if_else_none(
            R.path([0, "use_size"]),
            R.compose(m2s, R.prepend("size"), R.always([3]))),
        if_else_none(
            R.path([0, "use_burst"]),
            R.compose(m2s, R.prepend("burst"), R.always([2]))),
        if_else_none(
            R.path([0, "use_lock"]),
            R.compose(m2s, R.prepend("lock"), R.always([1]))),
        if_else_none(
            R.path([0, "use_cache"]),
            R.compose(m2s, R.prepend("cache"), R.always([4]))),
        if_else_none(
            R.path([0, "use_qos"]),
            R.compose(m2s, R.prepend("qos"), R.always([4]))),
        if_else_none(
            R.compose(R.flip(R.gt)(0), R.nth(1)),
            R.compose(m2s, R.prepend("user"), R.of, R.nth(1))),
        if_else_none(
            R.path([0, "use_prot"]),
            R.compose(m2s, R.prepend("prot"), R.always([3]))),
    ]),
    R.juxt([R.compose(namedtuple2map, R.head), R.nth(1)]),
    two_ary)


@R.curry
def _set_burst(val: int, config: Axi4Config, m: Module, chan: stream.Endpoint):
    assert config.use_burst
    m.comb += chan.burst.eq(val)


set_burst_fixed = _set_burst(Burst.fixed)
set_burst_wrap = _set_burst(Burst.wrap)
set_burst_incr = _set_burst(Burst.incr)


@R.curry
def _set(name: str, config: Axi4Config, m: Module, chan: stream.Endpoint,
         val: int):
    if getattr(config, name):
        m.comb += getattr(chan, name).eq(val)


set_size = _set("size")
set_lock = _set("lock")
set_cache = _set("cache")

axi4_aw = axi4_ax
axi4_ar = axi4_ax
axi4_arw = R.compose(R.append(["write", 1, DIR_M_TO_S]), axi4_ax)

axi4_w = R.compose(
    filter_nil,
    R.juxt([
        R.compose(m2s, R.prepend("data"), R.of, R.path([0, "data_width"])),
        if_else_none(
            R.path([0, "use_strb"]),
            R.compose(m2s, R.prepend("strb"), R.of,
                      R.path([0, "byte_per_word"]))),
        if_else_none(
            R.path([0, "use_w_user"]),
            R.compose(m2s, R.prepend("user"), R.of,
                      R.path([0, "w_user_width"]))),
        if_else_none(
            R.path([0, "use_last"]),
            R.compose(m2s, R.prepend("last"), R.always([1])))]),
    R.juxt([R.compose(namedtuple2map, R.head), R.nth(1)]),
    two_ary)

axi4_b = R.compose(
    filter_nil,
    R.juxt([
        if_else_none(
            R.path([0, "use_id"]),
            R.compose(s2m, R.prepend("id"), R.of, R.path([0, "id_width"]))),
        if_else_none(
            R.path([0, "use_resp"]),
            R.compose(s2m, R.prepend("resp"), R.always([2]))),
        if_else_none(
            R.path([0, "use_b_user"]),
            R.compose(
                s2m, R.prepend("user"), R.of, R.path([0, "b_user_width"])))]),
    R.juxt([R.compose(namedtuple2map, R.head), R.nth(1)]),
    two_ary)

_set_resp = _set("resp")
set_okay = _set_resp(R.__, R.__, R.__, Response.okay)
set_exokay = _set_resp(R.__, R.__, R.__, Response.exokay)
set_slverr = _set_resp(R.__, R.__, R.__, Response.slverr)
set_decerr = _set_resp(R.__, R.__, R.__, Response.decerr)


@R.curry
def _get(name: str, chan: stream.Endpoint):
    return getattr(name, chan)


_get_resp = _get("resp")
is_okay = R.compose(R.equals(Response.okay), _get_resp)
is_exokay = R.compose(R.equals(Response.exokay), _get_resp)
is_slverr = R.compose(R.equals(Response.slverr), _get_resp)
is_decerr = R.compose(R.equals(Response.decerr), _get_resp)


axi4_r = R.compose(
    filter_nil,
    R.juxt([
        R.compose(s2m, R.prepend("data"), R.of, R.path([0, "data_width"])),
        if_else_none(
            R.path([0, "use_id"]),
            R.compose(s2m, R.prepend("id"), R.of, R.path([0, "id_width"]))),
        if_else_none(
            R.path([0, "use_resp"]),
            R.compose(s2m, R.prepend("resp"), R.always([2]))),
        if_else_none(
            R.path([0, "use_last"]),
            R.compose(s2m, R.prepend("last"), R.always([1]))),
        if_else_none(
            R.path([0, "use_r_user"]),
            R.compose(
                s2m, R.prepend("user"), R.of, R.path([0, "r_user_width"]))),
    ]),
    R.juxt([R.compose(namedtuple2map, R.head), R.nth(1)]),
    two_ary)
