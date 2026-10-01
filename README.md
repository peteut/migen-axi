## Migen AXI

[![Build Status](https://app.travis-ci.com/peteut/migen-axi.svg?branch=master)](https://app.travis-ci.com/peteut/migen-axi)
[![Coverage Status](https://coveralls.io/repos/peteut/migen-axi/badge.svg)](https://coveralls.io/r/peteut/migen-axi)

This repo contains some [Migen][] modules created to support some [MiSoC][] features
on the [Xilinx Zynq SoC][] or the [Xilinx ZynqMP UltraScale+ RFSoC][]. A _Zedboard_ is used for testing, the existing
platform from [Migen][] is used as baseline and extended as necessary.

### Cores

- [x] wrapper for PS7
- [x] wrapper for PS8

### Interconnect

- [x] AXI2CSR
- [x] P2P interconnect
- [ ] InterconnectShared
- [ ] Crossbar
- [x] Writer, _AXI3 Slave + CoreLink DMA-330 DMA Controller Peripheral Request Interface (PRI)_

By now only P2P interconnect is in actual use, where _M_AXI_GP0_ is wired to a
custom AXI3 slave and _M_AXI_GP1_ is wired to an `AXI2CSR` bridge.

### Linux Support

- [ ] Device-tree overlay generator for iomem, irqs, firmware

Device-tree overlay is supported by Linux, currently _.dts_ is crafted manually
but shall be automatically generated.
Overlays with firmware loading has been tested on a 4.9 Linux.
To allow for phandles `DTS_FLAGS+='-@ -H epapr'` may be used.

### Running Tests

```
$ python -m venv .env
$ source .env/bin/activate
$ pip install .[test]
$ python -m pytest tests/
```

### License

Released under the MIT license, see LICENSE file for info.

[Migen]: https://github.com/m-labs/migen
[MiSoC]: https://github.com/m-labs/misoc
[Xilinx Zynq SoC]: https://www.amd.com/en/products/adaptive-socs-and-fpgas/soc/zynq-7000.html
[Xilinx ZynqMP UltraScale+ RFSoC]: https://www.amd.com/en/products/adaptive-socs-and-fpgas/soc/zynq-ultrascale-plus-rfsoc.html
