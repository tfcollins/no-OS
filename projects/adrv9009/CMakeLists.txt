add_executable(adrv9009)

# Talise profile directory (selected via Kconfig)
if(CONFIG_ADRV9009_PROFILE_BW200)
	set(ADRV9009_PROFILE tx_bw200_ir245p76_rx_bw200_or245p76_orx_bw200_or245p76_dc245p76)
elseif(CONFIG_ADRV9009_PROFILE_BW400)
	set(ADRV9009_PROFILE tx_bw400_ir491p52_rx_bw200_or245p76_orx_bw400_or491p52_dc245p76)
else()
	set(ADRV9009_PROFILE tx_bw100_ir122p88_rx_bw100_or122p88_orx_bw100_or122p88_dc122p88)
endif()

# Application entry point depends on the processor:
#   cortexa9          -> Zynq-7000 (ZC706)            -> headless_arm.c
#   cortexa53/cortexa72 -> Zynq UltraScale+ / Versal  -> headless_zu.c
if(XILINX_ARCH STREQUAL "cortexa53" OR XILINX_ARCH STREQUAL "cortexa72")
	set(ADRV9009_MAIN ${CMAKE_CURRENT_SOURCE_DIR}/src/app/headless_zu.c)
else()
	set(ADRV9009_MAIN ${CMAKE_CURRENT_SOURCE_DIR}/src/app/headless_arm.c)
endif()

target_sources(adrv9009 PRIVATE
	${ADRV9009_MAIN}
	${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_clocking.c
	${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_jesd.c
	${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_transceiver.c
	${CMAKE_CURRENT_SOURCE_DIR}/src/app/app_talise.c
	${CMAKE_CURRENT_SOURCE_DIR}/src/devices/adi_hal/no_os_hal.c
	${CMAKE_CURRENT_SOURCE_DIR}/profiles/${ADRV9009_PROFILE}/talise_config.c
)

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
