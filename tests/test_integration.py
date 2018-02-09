from migen_misc.platforms import zedboard
from migen_misc.integration import SoCCore


def test_soc_core():
    plat = zedboard.Platform(name="soc", toolchain="vivado")
    soc = SoCCore(plat)
    soc.build(build_name="soc", run=False)
