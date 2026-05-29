# IIO_SUPPORT gates the IIO code paths in projects/drivers; define it only when
# IIO is actually enabled (mirrors the old Makefile, where -DIIO_SUPPORT was set
# only for IIOD=y builds). Defining it unconditionally pulls the IIO path into
# non-IIO firmware (e.g. adrv9009 headless), which then fails to link.
if(CONFIG_IIO)
  target_compile_definitions(no-os PUBLIC -DIIO_SUPPORT)
endif()

no_os_sources_ifdef(CONFIG_IIO ${CMAKE_CURRENT_SOURCE_DIR}/iio_trigger.c)
no_os_sources_ifdef(CONFIG_IIO ${CMAKE_CURRENT_SOURCE_DIR}/iio.c)
no_os_sources_ifdef(CONFIG_IIO ${CMAKE_CURRENT_SOURCE_DIR}/iiod.c)
no_os_sources_ifdef(CONFIG_IIO ${CMAKE_CURRENT_SOURCE_DIR}/iio_app/iio_app.c)

target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/iio_app)