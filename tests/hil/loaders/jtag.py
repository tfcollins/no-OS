"""Xilinx bare-metal JTAG loader (load() implemented in Task 6)."""


class JTAGLoader:
    name = "jtag"

    def load(self, artifacts, target, options) -> None:
        raise NotImplementedError
