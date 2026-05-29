# AXI ADC / DAC / DMA cores
no_os_sources_ifdef(CONFIG_AXI_ADC_CORE ${CMAKE_CURRENT_SOURCE_DIR}/axi_adc_core/axi_adc_core.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/axi_adc_core)

no_os_sources_ifdef(CONFIG_AXI_DAC_CORE ${CMAKE_CURRENT_SOURCE_DIR}/axi_dac_core/axi_dac_core.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/axi_dac_core)

no_os_sources_ifdef(CONFIG_AXI_DMAC ${CMAKE_CURRENT_SOURCE_DIR}/axi_dmac/axi_dmac.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/axi_dmac)

# JESD204 AXI link layer (clk + rx/tx)
no_os_sources_ifdef(CONFIG_AXI_JESD204 ${CMAKE_CURRENT_SOURCE_DIR}/jesd204/axi_jesd204_rx.c)
no_os_sources_ifdef(CONFIG_AXI_JESD204 ${CMAKE_CURRENT_SOURCE_DIR}/jesd204/axi_jesd204_tx.c)
no_os_sources_ifdef(CONFIG_AXI_JESD204 ${CMAKE_CURRENT_SOURCE_DIR}/jesd204/jesd204_clk.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/jesd204)

# Xilinx-specific transceiver + clock generator
if(CONFIG_XILINX)
	no_os_sources_ifdef(CONFIG_AXI_JESD204 ${CMAKE_CURRENT_SOURCE_DIR}/jesd204/xilinx_transceiver.c)
	no_os_sources_ifdef(CONFIG_AXI_JESD204 ${CMAKE_CURRENT_SOURCE_DIR}/jesd204/axi_adxcvr.c)
	no_os_sources_ifdef(CONFIG_CLK_AXI_CLKGEN ${CMAKE_CURRENT_SOURCE_DIR}/clk_axi_clkgen/clk_axi_clkgen.c)
	target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/clk_axi_clkgen)
endif()

# IIO bridges (enabled via CONFIG_IIO_AXI_* when CONFIG_IIO=y)
no_os_sources_ifdef(CONFIG_IIO_AXI_ADC ${CMAKE_CURRENT_SOURCE_DIR}/iio_axi_adc/iio_axi_adc.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/iio_axi_adc)

no_os_sources_ifdef(CONFIG_IIO_AXI_DAC ${CMAKE_CURRENT_SOURCE_DIR}/iio_axi_dac/iio_axi_dac.c)
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/iio_axi_dac)
