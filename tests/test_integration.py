from migen_axi.platforms import zcu111, zedboard, zc706
from migen_axi.integration import SoCCore, SoCCoreZynqMP
from migen_axi.cores import ps8


def test_soc_core_zedboard():
    plat = zedboard.Platform()
    soc = SoCCore(plat)
    soc.build(build_name="soc", run=False)


def test_soc_core_zc706():
    plat = zc706.Platform()
    soc = SoCCore(plat)
    soc.build(build_name="soc", run=False)


def test_soc_core_zcu111():
    plat = zcu111.Platform()
    soc = SoCCoreZynqMP(plat)
    soc.add_sram("test_sram", 0x1000)
    soc.build(build_name="soc", run=False)
