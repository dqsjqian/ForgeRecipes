# Locate an installed package's CMake config directory across shared SDK prefixes.
#
# Where a package's CMake config lands inside its prefix is recipe knowledge:
# library recipes install lib/cmake/<package>, header-only recipes install
# share/cmake/<package>, and nested SDK layouts keep their own root. This
# helper centralizes those layouts so every consumer does not hardcode them.
# On success it sets <OUT> to the config directory, optionally <PREFIX_OUT> to
# the owning prefix, and the <package>_DIR cache entry so a plain
# find_package(<package> CONFIG) resolves without another search.
include_guard(GLOBAL)

function(forgerecipes_locate_package)
    cmake_parse_arguments(LOCATE "" "PACKAGE;OUT;PREFIX_OUT" "PREFIXES" ${ARGN})
    if(NOT LOCATE_PACKAGE OR NOT LOCATE_OUT OR NOT LOCATE_PREFIXES
            OR LOCATE_UNPARSED_ARGUMENTS OR LOCATE_KEYWORDS_MISSING_VALUES)
        message(FATAL_ERROR "forgerecipes_locate_package requires PACKAGE, OUT and PREFIXES")
    endif()
    set(${LOCATE_OUT} "" PARENT_SCOPE)
    if(LOCATE_PREFIX_OUT)
        set(${LOCATE_PREFIX_OUT} "" PARENT_SCOPE)
    endif()
    foreach(_prefix IN LISTS LOCATE_PREFIXES)
        foreach(_relative
                "lib/cmake/${LOCATE_PACKAGE}"
                "share/cmake/${LOCATE_PACKAGE}"
                "${LOCATE_PACKAGE}/lib/cmake/${LOCATE_PACKAGE}")
            set(_directory "${_prefix}/${_relative}")
            if(EXISTS "${_directory}/${LOCATE_PACKAGE}Config.cmake"
                    OR EXISTS "${_directory}/${LOCATE_PACKAGE}-config.cmake")
                set(${LOCATE_OUT} "${_directory}" PARENT_SCOPE)
                if(LOCATE_PREFIX_OUT)
                    set(${LOCATE_PREFIX_OUT} "${_prefix}" PARENT_SCOPE)
                endif()
                set(${LOCATE_PACKAGE}_DIR "${_directory}" CACHE PATH
                    "${LOCATE_PACKAGE} package config directory" FORCE)
                return()
            endif()
        endforeach()
    endforeach()
endfunction()
