cmake_minimum_required(VERSION 3.21)
project(threadx_gpio_demo LANGUAGES C ASM)

set(TX_CORE "cortex_m55" CACHE STRING "ThreadX port to build")
set_property(CACHE TX_CORE PROPERTY STRINGS cortex_m4 cortex_m55 cortex_m85)
set(LED_DEMO_MAX_CYCLES "10" CACHE STRING "Stop after this many LED cycles; 0 runs forever")
set(TX_GENERATION "6" CACHE STRING "ThreadX generation: 5 (external licensed) or 6 (MIT)")
set_property(CACHE TX_GENERATION PROPERTY STRINGS 5 6)
set(TX5_ROOT "$ENV{TX5_ROOT}" CACHE PATH "External ThreadX 5 distribution (WICED SDK 3.1.0 checkout)")
if("$ENV{TX5_ADAPTER_FILE}" STREQUAL "")
    set(tx5_adapter_default "${CMAKE_CURRENT_SOURCE_DIR}/cmake/tx5-wiced-adapter.cmake")
else()
    set(tx5_adapter_default "$ENV{TX5_ADAPTER_FILE}")
endif()
set(TX5_ADAPTER_FILE "${tx5_adapter_default}" CACHE FILEPATH
    "CMake adapter defining the ThreadX 5 target")
set(TX5_EXPECTED_VERSION "G5.6.5.2" CACHE STRING "Exact version string in the TX5 runtime banner")
if(TX_GENERATION STREQUAL "5")
    # Exception handler names exported by the WICED Cortex-M3/M4 TX5.6 port.
    set(pendsv_default "__tx_PendSVHandler")
    set(svc_default "__tx_SVCallHandler")
else()
    set(pendsv_default "PendSV_Handler")
    set(svc_default "fault_handler")
endif()
set(DEMO_PENDSV_SYMBOL "${pendsv_default}" CACHE STRING "PendSV symbol exported by the selected port")
set(DEMO_SVC_SYMBOL "${svc_default}" CACHE STRING "SVCall symbol used by the selected port")

if(TX_GENERATION STREQUAL "5")
    include(cmake/external-threadx5.cmake)
    set(DEMO_EXPECTED_VERSION "${TX5_EXPECTED_VERSION}")
elseif(TX_GENERATION STREQUAL "6")
    set(THREADX_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/third_party/threadx")
    if(NOT EXISTS "${THREADX_ROOT}/CMakeLists.txt")
        message(FATAL_ERROR
            "ThreadX submodule is missing. Run: git submodule update --init --recursive")
    endif()
    set(THREADX_ARCH "${TX_CORE}" CACHE STRING "ThreadX architecture" FORCE)
    set(THREADX_TOOLCHAIN "gnu" CACHE STRING "ThreadX GNU-syntax port" FORCE)
    set(TX_USER_FILE "${CMAKE_CURRENT_SOURCE_DIR}/config/tx6/tx_user.h" CACHE FILEPATH
        "Demonstrator kernel configuration" FORCE)
    add_subdirectory("${THREADX_ROOT}" "${CMAKE_BINARY_DIR}/threadx")
    target_include_directories(threadx SYSTEM PUBLIC
        "${CMAKE_CURRENT_SOURCE_DIR}/include/freestanding")
    set(DEMO_EXPECTED_VERSION "6.5.2.202603")
else()
    message(FATAL_ERROR "TX_GENERATION must be 5 or 6")
endif()

foreach(symbol IN ITEMS DEMO_PENDSV_SYMBOL DEMO_SVC_SYMBOL)
    if(NOT "${${symbol}}" MATCHES "^[A-Za-z_][A-Za-z0-9_]*$")
        message(FATAL_ERROR "${symbol} must name one assembly/C symbol")
    endif()
endforeach()

add_executable(threadx_gpio_demo
    src/led_demo.c
    src/rtos_selftest.c
    src/qemu_board.c
    src/startup.S
    src/tx_initialize_low_level.c
    src/baremetal_runtime.c)
if(TX_GENERATION STREQUAL "5")
    target_sources(threadx_gpio_demo PRIVATE src/tx5_wiced_port.c)
    target_compile_definitions(threadx_gpio_demo PRIVATE DEMO_TX5=1)
endif()
if(TX_CORE STREQUAL "cortex_m4")
    target_compile_definitions(threadx_gpio_demo PRIVATE DEMO_M4=1
        DEMO_CLOCK_HZ=25000000 DEMO_CORE_NAME="cortex-m4")
else()
    target_compile_definitions(threadx_gpio_demo PRIVATE
        DEMO_CLOCK_HZ=32000000)
    if(TX_CORE STREQUAL "cortex_m85")
        target_compile_definitions(threadx_gpio_demo PRIVATE DEMO_CORE_NAME="cortex-m85")
    else()
        target_compile_definitions(threadx_gpio_demo PRIVATE DEMO_CORE_NAME="cortex-m55")
    endif()
endif()

target_include_directories(threadx_gpio_demo PRIVATE include)
target_link_libraries(threadx_gpio_demo PRIVATE threadx)
target_compile_options(threadx_gpio_demo PRIVATE
    $<$<COMPILE_LANGUAGE:C>:-Wall;-Wextra;-Werror>)
target_compile_definitions(threadx_gpio_demo PRIVATE
    LED_DEMO_MAX_CYCLES=${LED_DEMO_MAX_CYCLES}
    DEMO_PENDSV_HANDLER=${DEMO_PENDSV_SYMBOL}
    DEMO_SVC_HANDLER=${DEMO_SVC_SYMBOL})
target_link_options(threadx_gpio_demo PRIVATE
    "-T${CMAKE_CURRENT_SOURCE_DIR}/boards/qemu.ld"
    "-Wl,-e,reset_handler"
    "-Wl,-Map=${CMAKE_BINARY_DIR}/threadx_gpio_demo.map")
set_property(TARGET threadx_gpio_demo APPEND PROPERTY LINK_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/boards/qemu.ld")
set_target_properties(threadx_gpio_demo PROPERTIES
    OUTPUT_NAME "threadx_gpio_demo"
    SUFFIX ".elf")

enable_testing()
if(TX_CORE STREQUAL "cortex_m55")
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(NAME qemu_m55_led_demo
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/run_qemu.py"
            --elf "$<TARGET_FILE:threadx_gpio_demo>"
            --machine mps3-an547
            --cpu cortex-m55
            --expected-version "${DEMO_EXPECTED_VERSION}")
elseif(TX_CORE STREQUAL "cortex_m4")
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(NAME qemu_m4_led_demo
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/run_qemu.py"
            --elf "$<TARGET_FILE:threadx_gpio_demo>"
            --machine mps2-an386
            --cpu cortex-m4
            --expected-version "${DEMO_EXPECTED_VERSION}")
endif()
