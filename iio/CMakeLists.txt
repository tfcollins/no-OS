# IIO_SUPPORT gates the IIO code paths in application/driver sources. Define it
# only when IIO is actually enabled (matches the Makefile build's IIOD=y), so
# non-IIO firmware (e.g. the adrv9009 "demo" build) doesn't reference IIO
# symbols that aren't compiled.
if(CONFIG_IIO)
    target_compile_definitions(no-os PUBLIC -DIIO_SUPPORT)
endif()

no_os_sources_ifdef(CONFIG_IIO ${CMAKE_CURRENT_SOURCE_DIR}/iio_trigger.c)
no_os_sources_ifdef(CONFIG_IIO ${CMAKE_CURRENT_SOURCE_DIR}/iio.c)
no_os_sources_ifdef(CONFIG_IIO ${CMAKE_CURRENT_SOURCE_DIR}/iiod.c)
no_os_sources_ifdef(CONFIG_IIO ${CMAKE_CURRENT_SOURCE_DIR}/iio_app/iio_app.c)

target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_include_directories(no-os PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/iio_app)