# Frequency / clock-generation drivers
no_os_sources_ifdef(CONFIG_FREQUENCY_AD9528 ${CMAKE_CURRENT_SOURCE_DIR}/ad9528/ad9528.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/ad9528)

no_os_sources_ifdef(CONFIG_FREQUENCY_HMC7044 ${CMAKE_CURRENT_SOURCE_DIR}/hmc7044/hmc7044.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/hmc7044)
