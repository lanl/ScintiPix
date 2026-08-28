cmake_minimum_required(VERSION 3.28)
project(ScintiPixSim LANGUAGES C CXX)

if(APPLE)
  # Under the Pixi/conda macOS toolchain, CMake's FindThreads try-compile may
  # incorrectly attempt to link pthread symbols as a separate library even
  # though they are provided by libSystem. Seed the expected Darwin result
  # before Geant4's nested find_dependency(Threads) runs.
  set(CMAKE_THREAD_LIBS_INIT "" CACHE STRING "" FORCE)
  set(CMAKE_HAVE_LIBC_PTHREAD 1 CACHE BOOL "" FORCE)
  set(CMAKE_HAVE_THREADS_LIBRARY 1 CACHE BOOL "" FORCE)
  set(CMAKE_USE_PTHREADS_INIT 1 CACHE BOOL "" FORCE)
  set(Threads_FOUND TRUE CACHE BOOL "" FORCE)
  if(NOT TARGET Threads::Threads)
    add_library(Threads::Threads INTERFACE IMPORTED)
  endif()
endif()

find_package(Geant4 REQUIRED ui_all vis_all)
include(${Geant4_USE_FILE})

if(DEFINED ENV{CONDA_PREFIX})
  list(PREPEND CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
endif()

if(DEFINED ENV{CONDA_PREFIX})
  list(PREPEND CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
endif()

# Binary output uses standard C file I/O - no external dependencies needed

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB APP_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cc)
file(GLOB APP_HEADERS CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/include/*.hh)

get_filename_component(SCINTIPIX_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)

# Core simulation sources built once and shared by the executable and the tests.
add_library(scintipix_core STATIC ${APP_SOURCES} ${APP_HEADERS})
target_include_directories(scintipix_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(scintipix_core PUBLIC ${Geant4_LIBRARIES})
target_compile_definitions(scintipix_core PUBLIC SCINTIPIX_REPO_ROOT="${SCINTIPIX_REPO_ROOT}")

add_executable(scintipix ${CMAKE_CURRENT_SOURCE_DIR}/apps/scintipix_main.cc)
target_link_libraries(scintipix PRIVATE scintipix_core)

# Keep executable path stable as ./build/scintipix.
set_target_properties(scintipix PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}
)

if(DEFINED ENV{CONDA_PREFIX})
  # Conda/Pixi toolchains already inject an rpath via linker flags.
  # Skip CMake's build-tree rpath to avoid duplicate -rpath warnings.
  set_target_properties(scintipix PROPERTIES
    SKIP_BUILD_RPATH TRUE
    INSTALL_RPATH "$ENV{CONDA_PREFIX}/lib"
    INSTALL_RPATH_USE_LINK_PATH FALSE
  )
endif()

# Make macro paths stable when running from the build directory.
file(COPY ${CMAKE_CURRENT_SOURCE_DIR}/macros DESTINATION ${PROJECT_BINARY_DIR}/sim)

# C++ unit tests (GoogleTest), run with `pixi run test-sim`.
enable_testing()
find_package(GTest REQUIRED)

add_executable(test_correlated_gamma ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_correlated_gamma.cc)
target_link_libraries(test_correlated_gamma PRIVATE scintipix_core GTest::gtest GTest::gtest_main)
add_test(NAME correlated_gamma COMMAND test_correlated_gamma)
