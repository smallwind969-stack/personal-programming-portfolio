#ifndef SMARTCAMPUS_CAMPUS_DATA_H
#define SMARTCAMPUS_CAMPUS_DATA_H

#include "smartcampus/Graph.h"

#include <string>

namespace smartcampus {

Graph loadCampusGraph(const std::string& locationFile, const std::string& roadFile);
Graph buildDefaultCampusGraph();

}  // namespace smartcampus

#endif
