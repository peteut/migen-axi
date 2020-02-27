from migen_axi.platforms import zedboard, zc706
from migen_axi.integration import SoCCore


def test_soc_core_zedboard():
    plat = zedboard.Platform()
    soc = SoCCore(plat)
    soc.build(build_name="soc", run=False)


def test_soc_core_zc706():
    plat = zc706.Platform()
    soc = SoCCore(plat)
    soc.build(build_name="soc", run=False)
