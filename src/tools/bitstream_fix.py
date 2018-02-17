import click
import numpy as np


@click.command(name="bitstream_fix")
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
def cli(**kwargs):
    """bitstream_fix for Linux fpga_mgr: strip header and swap bytes.

    [INPUT] bitstream file (*.bit)

    [OUTPUT] fixed binary bitstream file (*.bin)

    """
    a = np.fromfile(kwargs["input"], dtype="u1")
    hdr = a.tobytes().split(b"\xba\xfc")[0]
    click.echo("Processing {}".format(
        " ".join(hdr[0x10:].decode("ascii").split())))
    a = a[len(hdr) + 2:]
    aa = a.view(dtype="u4")
    aa.byteswap().tofile(kwargs["output"])
