## Migen AXI

[![Build Status](https://app.travis-ci.com/peteut/migen-axi.svg?branch=master)](
https://app.travis-ci.com/peteut/migen-axi)
[![Coverage Status](https://coveralls.io/repos/peteut/migen-axi/badge.svg)](
https://coveralls.io/r/peteut/migen-axi)

This repo contains some [Migen][] modules created to support some [MiSoC][] features
on the [Xilinx Zynq SoC][]. A *Zedboard* is used for testing, the existing
platform from [Migen][] is used as baseline and extended as necessary.

### Cores

- [x] wrapper for PS7

### Interconnect

- [x] AXI2CSR
- [x] P2P interconnect
- [ ] InterconnectShared
- [ ] Crossbar
- [x] Writer, *AXI3 Slave + CoreLink DMA-330 DMA Controller Peripheral Request Interface (PRI)*

By now only P2P interconnect is in actual use, where *M_AXI_GP0* is wired to a
custom AXI3 slave and *M_AXI_GP1* is wired to a `AXI2CSR` bridge.

### Linux Support

- [ ] Device-tree overlay generator for iomem, irqs, firmware

Device-tree overlay is supported by Linux, currently *.dts* is crafted manually
but shall be automatically generated.
Overlays with firmware loading has been tested on a 4.9 Linux.
To allow for phandles `DTS_FLAGS+='-@ -H epapr'` may be used.

### License

Released under the MIT license, see LICENSE file for info.

[Migen]: https://github.com/m-labs/migen
[MiSoC]: https://github.com/m-labs/misoc
[Xilinx Zynq SoC]: https://www.xilinx.com/products/silicon-devices/soc/zynq-7000.html

