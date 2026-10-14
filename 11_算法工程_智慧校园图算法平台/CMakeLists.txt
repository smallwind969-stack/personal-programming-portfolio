cmake_minimum_required(VERSION 3.16)
project(SmartCampusGraphLab LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(smartcampus_core
    src/Graph.cpp
    src/GraphAlgorithms.cpp
    src/CampusData.cpp
    src/ReportWriter.cpp
)
target_include_directories(smartcampus_core PUBLIC include)

add_executable(smartcampus src/main.cpp)
target_link_libraries(smartcampus PRIVATE smartcampus_core)

add_executable(graph_algorithms_test tests/graph_algorithms_test.cpp)
target_link_libraries(graph_algorithms_test PRIVATE smartcampus_core)
