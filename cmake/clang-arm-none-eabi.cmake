set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

if(NOT DEFINED TX_CORE)
    set(TX_CORE "cortex_m55" CACHE STRING "ThreadX Cortex-M port")
endif()

if(TX_CORE STREQUAL "cortex_m4")
    set(TX_CPU "cortex-m4")
elseif(TX_CORE STREQUAL "cortex_m55")
    set(TX_CPU "cortex-m55")
elseif(TX_CORE STREQUAL "cortex_m85")
    set(TX_CPU "cortex-m85")
else()
    message(FATAL_ERROR "TX_CORE must be cortex_m4, cortex_m55, or cortex_m85")
endif()

find_program(LLVM_CLANG NAMES clang clang.exe REQUIRED)
find_program(LLVM_AR NAMES llvm-ar llvm-ar.exe REQUIRED)
find_program(LLVM_RANLIB NAMES llvm-ranlib llvm-ranlib.exe REQUIRED)

set(CMAKE_C_COMPILER "${LLVM_CLANG}" CACHE FILEPATH "Clang C compiler" FORCE)
set(CMAKE_ASM_COMPILER "${LLVM_CLANG}" CACHE FILEPATH "Clang assembler" FORCE)
set(CMAKE_C_COMPILER_TARGET arm-none-eabi)
set(CMAKE_ASM_COMPILER_TARGET arm-none-eabi)
set(CMAKE_AR "${LLVM_AR}" CACHE FILEPATH "LLVM archiver" FORCE)
set(CMAKE_RANLIB "${LLVM_RANLIB}" CACHE FILEPATH "LLVM ranlib" FORCE)

set(THREADX_ARCH "${TX_CORE}" CACHE STRING "ThreadX architecture" FORCE)
set(THREADX_TOOLCHAIN "gnu" CACHE STRING "ThreadX GNU-syntax port" FORCE)

if(DEFINED TX_GENERATION AND TX_GENERATION STREQUAL "5")
    # The WICED ThreadX 5.6 archive is soft-float (its context switch saves
    # r4-r11 only) and was built by GCC with packed enums. Every object in the
    # image must share that ABI.
    set(ARM_CPU_FLAGS "-mcpu=${TX_CPU} -mthumb -mfloat-abi=soft -fshort-enums")
else()
    set(ARM_CPU_FLAGS "-mcpu=${TX_CPU} -mthumb -mfloat-abi=hard")
endif()
set(CMAKE_C_FLAGS_INIT
    "${ARM_CPU_FLAGS} -ffreestanding -fno-builtin -ffunction-sections -fdata-sections")
set(CMAKE_ASM_FLAGS_INIT
    "${ARM_CPU_FLAGS} -x assembler-with-cpp")
set(CMAKE_EXE_LINKER_FLAGS_INIT
    "${ARM_CPU_FLAGS} -nostdlib -fuse-ld=lld -Wl,--gc-sections")
