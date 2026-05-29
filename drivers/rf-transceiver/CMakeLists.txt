# Talise (ADRV9009/ADRV9008) transceiver API
if(CONFIG_RF_TRANSCEIVER_TALISE)
	set(TALISE_API ${CMAKE_CURRENT_SOURCE_DIR}/talise/api)
	target_sources(no-os PRIVATE
		${TALISE_API}/talise_agc.c
		${TALISE_API}/talise_arm.c
		${TALISE_API}/talise.c
		${TALISE_API}/talise_cals.c
		${TALISE_API}/talise_error.c
		${TALISE_API}/talise_gpio.c
		${TALISE_API}/talise_hal.c
		${TALISE_API}/talise_jesd204.c
		${TALISE_API}/talise_radioctrl.c
		${TALISE_API}/talise_rx.c
		${TALISE_API}/talise_tx.c
		${TALISE_API}/talise_user.c
	)
	target_include_directories(no-os PUBLIC
		${CMAKE_CURRENT_SOURCE_DIR}/talise
		${TALISE_API}
		${CMAKE_CURRENT_SOURCE_DIR}/talise/firmware
	)
endif()
