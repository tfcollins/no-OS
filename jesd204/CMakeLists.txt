# JESD204 link-layer state-machine framework
no_os_sources_ifdef(CONFIG_JESD204 ${CMAKE_CURRENT_SOURCE_DIR}/jesd204-core.c)
no_os_sources_ifdef(CONFIG_JESD204 ${CMAKE_CURRENT_SOURCE_DIR}/jesd204-fsm.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
