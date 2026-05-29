# Xilinx platform SDK integration.
#
# Generates the Xilinx standalone BSP (libxil + xparameters.h, xil_cache.h,
# the linker script, ...) from a hardware design (.xsa) using xsct, then wires
# the generated include/lib paths and the linker script into the build target.
#
# Inputs (typically set from the board preset / defconfig):
#   XSA_PATH or CONFIG_XILINX_XSA_PATH  - path to the .xsa hardware design
#   XILINX_PROC                          - BSP processor instance
#                                          (e.g. psu_cortexa53_0 for ZynqMP)
#   XPS_BOARD                            - board macro (e.g. ZCU102) -> -DXPS_BOARD_<x>
#
# When Vitis (xsct) or the .xsa are unavailable, BSP generation is skipped with
# a warning so that `cmake` configuration still completes (configure-only). The
# actual BSP build and link must then run on a machine with Vitis installed.

function(config_xilinx_sdk BUILD_TARGET)
	# Always-on platform define.
	target_compile_definitions(no-os PUBLIC -DXILINX_PLATFORM)
	if(DEFINED XPS_BOARD AND NOT "${XPS_BOARD}" STREQUAL "")
		target_compile_definitions(no-os PUBLIC -DXPS_BOARD_${XPS_BOARD})
	endif()

	# Resolve the hardware design (.xsa).
	if(DEFINED CONFIG_XILINX_XSA_PATH AND NOT "${CONFIG_XILINX_XSA_PATH}" STREQUAL "")
		set(XSA_FILE "${CONFIG_XILINX_XSA_PATH}")
	elseif(DEFINED XSA_PATH AND NOT "${XSA_PATH}" STREQUAL "")
		set(XSA_FILE "${XSA_PATH}")
	endif()
	if(DEFINED XSA_FILE AND NOT IS_ABSOLUTE "${XSA_FILE}")
		set(XSA_FILE "${CMAKE_SOURCE_DIR}/${XSA_FILE}")
	endif()

	# Processor instance whose BSP we generate (defines the BSP subdir name).
	if(NOT DEFINED XILINX_PROC OR "${XILINX_PROC}" STREQUAL "")
		set(XILINX_PROC "psu_cortexa53_0")
	endif()

	find_program(XSCT_EXECUTABLE xsct HINTS "$ENV{XILINX_VITIS}/bin" "$ENV{XILINX_SDK}/bin")

	set(BSP_DIR "${CMAKE_CURRENT_BINARY_DIR}/xilinx_bsp")
	set(BSP_LIB "${BSP_DIR}/${XILINX_PROC}/lib/libxil.a")
	set(LSCRIPT "${BSP_DIR}/app/src/lscript.ld")
	set(XILINX_UTIL_TCL "${NO_OS_DIR}/tools/scripts/platform/xilinx/util.tcl")

	if(NOT XSCT_EXECUTABLE OR NOT DEFINED XSA_FILE OR NOT EXISTS "${XSA_FILE}")
		message(WARNING
			"Xilinx BSP not generated (configure-only). "
			"xsct='${XSCT_EXECUTABLE}', xsa='${XSA_FILE}'.\n"
			"   To build for hardware: install Vitis, `source settings64.sh` "
			"(sets XILINX_VITIS), and pass -DXSA_PATH=<design.xsa>.")
		return()
	endif()

	# Generate (and compile) the BSP from the .xsa, once.
	if(NOT EXISTS "${BSP_LIB}")
		file(MAKE_DIRECTORY "${BSP_DIR}")
		get_filename_component(XSA_NAME "${XSA_FILE}" NAME)
		configure_file("${XSA_FILE}" "${BSP_DIR}/${XSA_NAME}" COPYONLY)
		message(STATUS "Xilinx: generating BSP from ${XSA_NAME} (proc ${XILINX_PROC})")
		execute_process(
			COMMAND ${XSCT_EXECUTABLE} -nodisp ${XILINX_UTIL_TCL}
				create_project ${BSP_DIR} ${BSP_DIR} ${XSA_NAME}
				${BUILD_TARGET}.elf 0 "Empty Application(C)"
			WORKING_DIRECTORY "${BSP_DIR}"
			RESULT_VARIABLE _xsct_res
		)
		if(NOT _xsct_res EQUAL 0)
			message(FATAL_ERROR "Xilinx BSP generation failed (xsct exit ${_xsct_res})")
		endif()
	endif()

	# Wire the generated BSP into the build.
	target_include_directories(no-os PUBLIC "${BSP_DIR}/${XILINX_PROC}/include")
	target_link_directories(${BUILD_TARGET} PUBLIC "${BSP_DIR}/${XILINX_PROC}/lib")
	# Xilinx standalone libraries (see tools/scripts/xilinx.mk).
	target_link_libraries(${BUILD_TARGET}
		-Wl,--start-group xil gcc c -Wl,--end-group)
	if(EXISTS "${LSCRIPT}")
		target_link_options(${BUILD_TARGET} PRIVATE -T${LSCRIPT})
	endif()
endfunction()
