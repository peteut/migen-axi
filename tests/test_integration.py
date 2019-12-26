from migen_axi.platforms import zedboard
from migen_axi.integration import SoCCore


def test_soc_core():
    plat = zedboard.Platform()
    soc = SoCCore(plat)
    soc.build(build_name="soc", run=False)
