# SPDX-License-Identifier: MIT
# Links the prebuilt ThreadX 5.6 Cortex-M4 archive from an external WICED SDK
# 3.1.0 checkout. Nothing from the SDK is copied into this repository.
set(TX5_WICED_RTOS "${TX5_ROOT}/WICED/RTOS/ThreadX")
set(TX5_WICED_LIBRARY "${TX5_WICED_RTOS}/ThreadX.ARM_CM4.release.a")
foreach(required IN ITEMS
        "${TX5_WICED_RTOS}/ver5.6/tx_api.h"
        "${TX5_WICED_RTOS}/ver5.6/tx_user.h"
        "${TX5_WICED_RTOS}/ver5.6/Cortex_M3_M4/GCC/tx_port.h"
        "${TX5_WICED_LIBRARY}")
    if(NOT EXISTS "${required}")
        message(FATAL_ERROR "TX5_ROOT is not a WICED SDK 3.1.0 checkout: missing ${required}")
    endif()
endforeach()

add_library(threadx STATIC IMPORTED GLOBAL)
set_target_properties(threadx PROPERTIES
    IMPORTED_LOCATION "${TX5_WICED_LIBRARY}"
    INTERFACE_COMPILE_DEFINITIONS "TX_INCLUDE_USER_DEFINE_FILE"
    INTERFACE_SYSTEM_INCLUDE_DIRECTORIES
        "${TX5_WICED_RTOS}/ver5.6;${TX5_WICED_RTOS}/ver5.6/Cortex_M3_M4/GCC;${CMAKE_CURRENT_SOURCE_DIR}/include/freestanding"
    INTERFACE_INCLUDE_DIRECTORIES
        "${TX5_WICED_RTOS}/ver5.6;${TX5_WICED_RTOS}/ver5.6/Cortex_M3_M4/GCC;${CMAKE_CURRENT_SOURCE_DIR}/include/freestanding")
