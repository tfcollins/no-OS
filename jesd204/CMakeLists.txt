# JESD204 link-bringup framework (jesd204-core + FSM). Used by the AXI JESD204
# link-layer drivers (drivers/axi_core/jesd204), so compile it whenever those
# are enabled. The public header is include/jesd204.h (already on the no-os
# include path); jesd204-priv.h lives here.
no_os_sources_ifdef(CONFIG_AXI_CORE_JESD204
    ${CMAKE_CURRENT_SOURCE_DIR}/jesd204-core.c
    ${CMAKE_CURRENT_SOURCE_DIR}/jesd204-fsm.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
