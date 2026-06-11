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

find_package(Arrow CONFIG REQUIRED)
find_package(Parquet CONFIG REQUIRED)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB APP_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cc)
file(GLOB APP_HEADERS CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/include/*.hh)

add_executable(scintipix ${CMAKE_CURRENT_SOURCE_DIR}/apps/scintipix_main.cc ${APP_SOURCES} ${APP_HEADERS})

target_include_directories(scintipix PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(scintipix PRIVATE
  ${Geant4_LIBRARIES}
  Arrow::arrow_shared
  Parquet::parquet_shared
)

get_filename_component(SCINTIPIX_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
target_compile_definitions(scintipix PRIVATE
  SCINTIPIX_REPO_ROOT="${SCINTIPIX_REPO_ROOT}"
)

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
