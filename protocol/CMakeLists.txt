cmake_minimum_required(VERSION 3.16)
project(eurobot_protocol VERSION 0.1.0 LANGUAGES CXX)

# Header-only biblioteka: nema sta da se kompajlira, samo include putanje.
add_library(eurobot_protocol INTERFACE)
add_library(eurobot_protocol::eurobot_protocol ALIAS eurobot_protocol)
target_include_directories(eurobot_protocol INTERFACE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(eurobot_protocol INTERFACE cxx_std_17)

# Testovi samo kada se gradi samostalno (ili kroz colcon), ne kada ga koristi drugi projekat.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  include(CTest)
  if(BUILD_TESTING)
    add_executable(test_protocol test/test_protocol.cpp)
    target_link_libraries(test_protocol PRIVATE eurobot_protocol)
    target_compile_options(test_protocol PRIVATE -Wall -Wextra -Wpedantic -Werror)
    add_test(NAME test_protocol COMMAND test_protocol)
  endif()
endif()

# Instalacija, da ROS paketi mogu da urade find_package(eurobot_protocol).
include(CMakePackageConfigHelpers)
install(DIRECTORY include/ DESTINATION include)
install(TARGETS eurobot_protocol EXPORT eurobot_protocolTargets)
install(EXPORT eurobot_protocolTargets
  NAMESPACE eurobot_protocol::
  DESTINATION share/eurobot_protocol/cmake)
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/eurobot_protocolConfig.cmake
  "include(\"\${CMAKE_CURRENT_LIST_DIR}/eurobot_protocolTargets.cmake\")\n")
write_basic_package_version_file(
  ${CMAKE_CURRENT_BINARY_DIR}/eurobot_protocolConfigVersion.cmake
  COMPATIBILITY SameMajorVersion ARCH_INDEPENDENT)
install(FILES
  ${CMAKE_CURRENT_BINARY_DIR}/eurobot_protocolConfig.cmake
  ${CMAKE_CURRENT_BINARY_DIR}/eurobot_protocolConfigVersion.cmake
  DESTINATION share/eurobot_protocol/cmake)
install(FILES package.xml DESTINATION share/eurobot_protocol)
