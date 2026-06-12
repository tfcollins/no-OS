"""Xilinx SD-Mux loader: write BOOT.BIN to the SD card, boot the board from SD.

Uses the adi-labgrid-plugins / labgrid USB SD-Mux storage driver to route the SD
card to the host, copy BOOT.BIN to the FAT boot partition, route it back to the
DUT, then drive the board's boot strategy. The driver/strategy names come from
the labgrid env YAML. If no storage driver is present, the test skips.
"""

from __future__ import annotations


class SDMuxLoader:
    name = "sdmux"

    # Driver names tried, in order, to find the SD-Mux storage driver.
    _STORAGE_DRIVERS = ("USBStorageDriver", "USBSDMuxDriver", "SDMuxDriver")

    def load(self, artifacts, target, options) -> None:
        import pytest
        # require() before touching the target so a missing artifact is a clear error.
        boot_bin = artifacts.require("boot_bin")

        storage = None
        for name in self._STORAGE_DRIVERS:
            try:
                storage = target.get_driver(name)
                break
            except Exception:
                continue
        if storage is None:
            pytest.skip("sdmux loader needs an SD-Mux storage driver in the labgrid env")

        # Route SD to host and write BOOT.BIN to the boot partition root.
        # labgrid's USBStorageDriver exposes write_files(sources, target_dir).
        storage.write_files([str(boot_bin)], target_dir="/")

        # Hand off to the board's boot strategy (adi-labgrid-plugins FPGA SoC /
        # SD boot). The strategy is configured in the env; "boot" is its DUT-up
        # state. PowerProtocol cycling is handled by the strategy transition.
        try:
            strategy = target.get_strategy()
        except Exception:
            pytest.skip("sdmux loader needs a boot strategy in the labgrid env")
        strategy.transition("boot")
