cmake_minimum_required(VERSION 3.27)
project(noos_hil_tests C CXX)

# CMake CTest configuration for Hardware-in-the-Loop (HIL) tests

enable_testing()

find_program(PYTEST_EXECUTABLE pytest)
if(NOT PYTEST_EXECUTABLE)
    if(NOT Python3_EXECUTABLE)
        find_package(Python3 COMPONENTS Interpreter REQUIRED)
    endif()
    set(PYTEST_CMD ${Python3_EXECUTABLE} -m pytest)
else()
    set(PYTEST_CMD ${PYTEST_EXECUTABLE})
endif()

# ==============================================================================
# Small C Native Unit Tests
# ==============================================================================
set(NO_OS_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../..")

add_executable(ad9361_util_test
    ${CMAKE_CURRENT_SOURCE_DIR}/unit_tests/test_ad9361_util.c
    ${NO_OS_ROOT}/drivers/rf-transceiver/ad9361/ad9361_util.c
)

target_include_directories(ad9361_util_test PRIVATE
    ${NO_OS_ROOT}/drivers/rf-transceiver/ad9361
    ${NO_OS_ROOT}/projects/ad9361/src
    ${NO_OS_ROOT}/include
)

add_test(
    NAME hil_small_ad9361_util
    COMMAND ad9361_util_test
)

# ==============================================================================
# Small Granular PyTest Tests
# ==============================================================================
add_test(
    NAME hil_small_builder
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/unit_tests/test_builder.py -p no:libiio -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_test(
    NAME hil_small_loaders
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/unit_tests/test_loaders.py -p no:libiio -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_test(
    NAME hil_small_reporting
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/unit_tests/test_reporting.py -p no:libiio -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_test(
    NAME hil_small_jtag_loader
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/unit_tests/test_jtag_loader.py -p no:libiio -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_test(
    NAME hil_small_ad9361_boot
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_ad9361.py -k test_boot_console_ad9361 -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_test(
    NAME hil_small_ad9361_iio
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_ad9361.py -k test_iio_ad9361 -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_test(
    NAME hil_small_ad9361_pyadi
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_ad9361.py -k test_pyadi_ad9361 -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

# ==============================================================================
# Grouped Suite Tests
# ==============================================================================
add_test(
    NAME hil_unit_tests
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/unit_tests -p no:libiio -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_test(
    NAME hil_ad9361_all
    COMMAND ${PYTEST_CMD} ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_ad9361.py -v
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
