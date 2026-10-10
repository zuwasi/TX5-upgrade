cmake_minimum_required(VERSION 3.21)
project(threadx_gpio_demo LANGUAGES C ASM)

set(TX_CORE "cortex_m55" CACHE STRING "ThreadX port to build")
set_property(CACHE TX_CORE PROPERTY STRINGS cortex_m4 cortex_m55 cortex_m85)
set(LED_DEMO_MAX_CYCLES "10" CACHE STRING "Stop after this many LED cycles; 0 runs forever")

set(THREADX_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/third_party/threadx")
if(NOT EXISTS "${THREADX_ROOT}/CMakeLists.txt")
    message(FATAL_ERROR
        "ThreadX submodule is missing. Run: git submodule update --init --recursive")
endif()

set(THREADX_ARCH "${TX_CORE}" CACHE STRING "ThreadX architecture" FORCE)
set(THREADX_TOOLCHAIN "gnu" CACHE STRING "ThreadX GNU-syntax port" FORCE)
set(TX_USER_FILE "${CMAKE_CURRENT_SOURCE_DIR}/include/tx_user.h" CACHE FILEPATH
    "Demonstrator kernel configuration" FORCE)

add_subdirectory("${THREADX_ROOT}" "${CMAKE_BINARY_DIR}/threadx")
target_include_directories(threadx SYSTEM PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}/include/freestanding")

add_executable(threadx_gpio_demo
    src/led_demo.c
    src/rtos_selftest.c
    src/qemu_board.c
    src/startup.S
    src/tx_initialize_low_level.c
    src/baremetal_runtime.c)
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
    LED_DEMO_MAX_CYCLES=${LED_DEMO_MAX_CYCLES})
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
            --cpu cortex-m55)
elseif(TX_CORE STREQUAL "cortex_m4")
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(NAME qemu_m4_led_demo
        COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/run_qemu.py"
            --elf "$<TARGET_FILE:threadx_gpio_demo>"
            --machine mps2-an386
            --cpu cortex-m4)
endif()
