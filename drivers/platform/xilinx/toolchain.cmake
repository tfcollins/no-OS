# Toolchain file for Xilinx (AMD) targets.
#
# The CPU architecture is selected by the board preset via XILINX_ARCH
# (e.g. "cortexa53" for Zynq UltraScale+/ZCU102). This picks the GNU
# cross-compiler that ships with Vitis. The compilers, plus xsct used for
# BSP generation, are located through the Vitis install pointed to by the
# XILINX_VITIS environment variable (falling back to PATH).

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Default to the ZynqMP application processor when a board preset does not
# specify one.
if(NOT DEFINED XILINX_ARCH)
	set(XILINX_ARCH "cortexa53")
endif()

# Map architecture -> GNU prefix, Vitis gnu subdir, and CPU flags.
if(XILINX_ARCH MATCHES "cortexa53|cortexa72")
	# ZynqMP (A53) and Versal (A72) are 64-bit.
	set(CROSS_PREFIX "aarch64-none-elf")
	set(VITIS_GNU_SUBDIR "gnu/aarch64/lin/aarch64-none/bin")
	set(XILINX_CPU_FLAGS "")
elseif(XILINX_ARCH MATCHES "cortexa9")
	# Zynq-7000.
	set(CROSS_PREFIX "arm-none-eabi")
	set(VITIS_GNU_SUBDIR "gnu/aarch32/lin/gcc-arm-none-eabi/bin")
	set(XILINX_CPU_FLAGS "-mcpu=cortex-a9 -mfpu=vfpv3 -mfloat-abi=hard")
elseif(XILINX_ARCH MATCHES "cortexr5")
	# ZynqMP real-time processing unit.
	set(CROSS_PREFIX "armr5-none-eabi")
	set(VITIS_GNU_SUBDIR "gnu/armr5/lin/gcc-arm-none-eabi/bin")
	set(XILINX_CPU_FLAGS "-mcpu=cortex-r5 -mfloat-abi=hard -mfpu=vfpv3-d16")
elseif(XILINX_ARCH MATCHES "microblaze|sys_mb")
	set(CROSS_PREFIX "microblaze-xilinx-elf")
	set(VITIS_GNU_SUBDIR "gnu/microblaze/lin/bin")
	set(XILINX_CPU_FLAGS "-mlittle-endian -mcpu=v11.0 -mxl-barrel-shift \
-mxl-pattern-compare -mno-xl-soft-div -mno-xl-soft-mul -mxl-multiply-high")
else()
	message(FATAL_ERROR "Unknown XILINX_ARCH '${XILINX_ARCH}'. Expected one of: "
		"cortexa53, cortexa72, cortexa9, cortexr5, microblaze.")
endif()

# Locate the Vitis install that provides the cross toolchain.
if(DEFINED ENV{XILINX_VITIS})
	set(VITIS_PATH "$ENV{XILINX_VITIS}")
elseif(DEFINED ENV{XILINX_SDK})
	set(VITIS_PATH "$ENV{XILINX_SDK}")
endif()

if(DEFINED VITIS_PATH)
	cmake_path(SET CROSS_COMPILER_BIN NORMALIZE "${VITIS_PATH}/${VITIS_GNU_SUBDIR}")
	message(STATUS "Xilinx: using Vitis toolchain at ${CROSS_COMPILER_BIN}")
else()
	message(STATUS "Xilinx: XILINX_VITIS not set; searching PATH for ${CROSS_PREFIX}-gcc")
endif()

find_program(CMAKE_C_COMPILER   ${CROSS_PREFIX}-gcc     HINTS ${CROSS_COMPILER_BIN})
find_program(CMAKE_CXX_COMPILER ${CROSS_PREFIX}-g++     HINTS ${CROSS_COMPILER_BIN})
find_program(CMAKE_ASM_COMPILER ${CROSS_PREFIX}-gcc     HINTS ${CROSS_COMPILER_BIN})
find_program(CMAKE_AR           ${CROSS_PREFIX}-ar      HINTS ${CROSS_COMPILER_BIN})
find_program(CMAKE_OBJCOPY      ${CROSS_PREFIX}-objcopy HINTS ${CROSS_COMPILER_BIN})
find_program(CMAKE_SIZE         ${CROSS_PREFIX}-size    HINTS ${CROSS_COMPILER_BIN})

# The final link needs the BSP-generated linker script (lscript.ld), which
# does not exist yet at configure time. Build a static library during the
# compiler check so CMake does not attempt a full link.
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(CMAKE_EXECUTABLE_SUFFIX_C   ".elf")
set(CMAKE_EXECUTABLE_SUFFIX_CXX ".elf")
set(CMAKE_EXECUTABLE_SUFFIX_ASM ".elf")

# Common flags (mirror tools/scripts/xilinx.mk)
set(CMAKE_C_FLAGS   "${XILINX_CPU_FLAGS} -DXILINX_PLATFORM -ffunction-sections -fdata-sections" CACHE STRING "C flags" FORCE)
set(CMAKE_CXX_FLAGS "${XILINX_CPU_FLAGS} -DXILINX_PLATFORM -ffunction-sections -fdata-sections" CACHE STRING "C++ flags" FORCE)
set(CMAKE_ASM_FLAGS "${XILINX_CPU_FLAGS} -x assembler-with-cpp" CACHE STRING "ASM flags" FORCE)

set(CMAKE_C_FLAGS_DEBUG   "-g3 -O0 -DDEBUG" CACHE STRING "C flags (Debug)" FORCE)
set(CMAKE_C_FLAGS_RELEASE "-O2 -g3 -DNDEBUG" CACHE STRING "C flags (Release)" FORCE)

# Linker: garbage-collect unused sections. The architecture-specific link
# flags and linker script are added by config_xilinx_sdk() once the BSP has
# been generated.
set(CMAKE_EXE_LINKER_FLAGS "${XILINX_CPU_FLAGS} -Wl,--gc-sections" CACHE STRING "Linker flags" FORCE)

# Search for headers/libs only in the toolchain, not on the host.
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
