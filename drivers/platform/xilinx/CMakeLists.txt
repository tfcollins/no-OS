# Xilinx platform definitions
target_compile_definitions(no-os PUBLIC -DXILINX_PLATFORM)

# Peripheral drivers (added based on Kconfig selection)
no_os_sources_ifdef(CONFIG_UART_XILINX     ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_uart.c)
no_os_sources_ifdef(CONFIG_IRQ_XILINX      ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_irq.c)
no_os_sources_ifdef(CONFIG_TIMER_XILINX    ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_timer.c)
no_os_sources_ifdef(CONFIG_GPIO_XILINX     ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_gpio.c)
no_os_sources_ifdef(CONFIG_GPIO_IRQ_XILINX ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_gpio_irq.c)
no_os_sources_ifdef(CONFIG_SPI_XILINX      ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_spi.c)
no_os_sources_ifdef(CONFIG_SPI_XILINX_PL   ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_spi_pl.c)
no_os_sources_ifdef(CONFIG_I2C_XILINX      ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_i2c.c)
no_os_sources_ifdef(CONFIG_AXI_IO_XILINX   ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_axi_io.c)

# Delay is always included when not using FreeRTOS
if(NOT ${CONFIG_FREERTOS})
	target_sources(no-os PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/xilinx_delay.c)
endif()

target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
