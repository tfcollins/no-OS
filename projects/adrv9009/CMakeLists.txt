add_executable(adrv9009)

# Dual-Talise carriers (ZU11EG SOM, FMCOMMS8 on ZCU102) are selected by a bare
# board macro that parameters.h / adrv9009.h / app_clocking.c key on (TALISE_B,
# the carrier clock, the B-side GPIOs). config_xilinx_sdk() also emits
# -DXPS_BOARD_<XPS_BOARD>, but the dual-Talise code wants the unprefixed name.
if(XPS_BOARD STREQUAL "ZU11EG" OR XPS_BOARD STREQUAL "FMCOMMS8_ZCU102")
	target_compile_definitions(no-os PUBLIC ${XPS_BOARD})
endif()

# Talise profile directory (selected via Kconfig)
if(CONFIG_ADRV9009_PROFILE_BW200)
	set(ADRV9009_PROFILE tx_bw200_ir245p76_rx_bw200_or245p76_orx_bw200_or245p76_dc245p76)
elseif(CONFIG_ADRV9009_PROFILE_BW400)
	set(ADRV9009_PROFILE tx_bw400_ir491p52_rx_bw200_or245p76_orx_bw400_or491p52_dc245p76)
else()
	set(ADRV9009_PROFILE tx_bw100_ir122p88_rx_bw100_or122p88_orx_bw100_or122p88_dc122p88)
endif()

# Sources common to every processor.
target_sources(adrv9009 PRIVATE
	${CMAKE_CURRENT_SOURCE_DIR}/src/devices/adi_hal/no_os_hal.c
	${CMAKE_CURRENT_SOURCE_DIR}/profiles/${ADRV9009_PROFILE}/talise_config.c
)

# The Talise integration differs by processor (mirrors the legacy
# arm_src.mk / zu_src.mk split), and the two paths define the same symbols
# (adrv9009_check_sysref_rate, the firmware blobs) so they are mutually
# exclusive:
#   cortexa9 (Zynq-7000 / ZC706): the application provides its own Talise glue
#     (app_talise.c + app_clocking/jesd/transceiver, headless_arm.c).
#   cortexa53/cortexa72 (ZynqMP/Versal, e.g. ZCU102): headless_zu.c drives the
#     reusable no-OS Talise driver wrapper (drivers/.../talise/adrv9009*.c).
# The vendor Talise API (talise/api/*.c) is compiled into the no-os library by
# drivers/rf-transceiver/CMakeLists.txt (CONFIG_RF_TRANSCEIVER_ADRV9009).
set(ADRV9009_TALISE_DIR ${NO_OS_DIR}/drivers/rf-transceiver/talise)
if(XILINX_ARCH STREQUAL "cortexa53" OR XILINX_ARCH STREQUAL "cortexa72")
	target_sources(adrv9009 PRIVATE
		${CMAKE_CURRENT_SOURCE_DIR}/src/app/headless_zu.c
		${ADRV9009_TALISE_DIR}/adrv9009.c
		${ADRV9009_TALISE_DIR}/adrv9009_conv.c
	)
else()
	target_sources(adrv9009 PRIVATE
		${CMAKE_CURRENT_SOURCE_DIR}/src/app/headless_arm.c
		${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_clocking.c
		${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_jesd.c
		${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_transceiver.c
		${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_talise.c
	)
endif()

# These include dirs go on `no-os` (not just the adrv9009 executable) because
# the Talise driver sources compiled into the no-os library include the
# project-provided HAL header (adi_hal.h) and parameters.h — mirroring the
# global include path of the legacy Makefile build. The executable inherits
# them transitively via target_link_libraries(adrv9009 no-os).
target_include_directories(no-os PUBLIC
	${CMAKE_CURRENT_SOURCE_DIR}/src/app
	${CMAKE_CURRENT_SOURCE_DIR}/src/devices/adi_hal
	${CMAKE_CURRENT_SOURCE_DIR}/profiles/${ADRV9009_PROFILE}
)

target_link_libraries(adrv9009 no-os)

config_platform_sdk(adrv9009)
add_flash_target(adrv9009)
post_build_config(adrv9009)
