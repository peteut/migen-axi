{
    signal: [
        {
            name: "GPMC_FCLK",
            wave: "p..............",
        }, {
            name: "GPMC_CLK",
            wave: "0.p...........0",
        }, {
            name: "A[27:17]",
            wave: "x=............x",
            data: ["A"],
        }, {
            name: "A[16:1]/D[15:0]",
            wave: "x=z...=======..",
            data: ["A", "D0", "D1", "D2", "D3", "D4", "D5", "D7"],
        },{
            name: "BE#[1:0]",
            wave: "10............1",
        }, {
            name: "CS#",
            wave: "10............1",
        }, {
            name: "ADV#",
            wave: "101............",
        }, {
            name: "OE#",
            wave: "1.....0......1.",
        }, {
            name: "DIR",
            wave: "0..............",
        }, {
            name: "WAIT",
            wave: "1..............",
        }
    ],
        config: {
            hscale: 1
        },
        head: {
            text: "GPMC synchronous burst read"
        },
}
