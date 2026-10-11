# SPDX-License-Identifier: MIT
# The ThreadX 5 distribution is linked from outside this repository. Its
# headers and binaries are never copied into the public source tree.
if(NOT TX_CORE STREQUAL "cortex_m4")
    message(FATAL_ERROR "The ThreadX 5 baseline is restricted to Cortex-M4")
endif()
if(NOT IS_DIRECTORY "${TX5_ROOT}")
    message(FATAL_ERROR
        "TX5_ROOT is required: point it at an external WICED SDK 3.1.0 checkout")
endif()
if(NOT EXISTS "${TX5_ADAPTER_FILE}")
    message(FATAL_ERROR "TX5_ADAPTER_FILE does not exist: ${TX5_ADAPTER_FILE}")
endif()
if(NOT TX5_EXPECTED_VERSION MATCHES "^G?5\\.[0-9]+(\\.[0-9]+)*$")
    message(FATAL_ERROR
        "TX5_EXPECTED_VERSION must be the TX5 banner version, for example G5.6.5.2")
endif()

# Resolve symlinks before enforcing the external dependency boundary.
file(REAL_PATH "${CMAKE_SOURCE_DIR}" project_root)
file(REAL_PATH "${TX5_ROOT}" tx5_root_real)
file(RELATIVE_PATH relative_path "${project_root}" "${tx5_root_real}")
if(NOT relative_path MATCHES "^\\.\\./" AND NOT IS_ABSOLUTE "${relative_path}")
    message(FATAL_ERROR
        "TX5_ROOT must be outside this public repository, not inside its source tree")
endif()
include("${TX5_ADAPTER_FILE}")
if(NOT TARGET threadx)
    message(FATAL_ERROR "The TX5 adapter must define target threadx")
endif()
