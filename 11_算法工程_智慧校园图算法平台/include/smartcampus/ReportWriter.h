#ifndef SMARTCAMPUS_REPORT_WRITER_H
#define SMARTCAMPUS_REPORT_WRITER_H

#include "smartcampus/Graph.h"
#include "smartcampus/GraphAlgorithms.h"

#include <string>

namespace smartcampus {

void writeRouteReport(const Graph& graph,
                      const PathResult& path,
                      const MstResult& mst,
                      const std::string& outputPath);
void writeCampusSvg(const Graph& graph,
                    const PathResult& highlightedPath,
                    const MstResult& mst,
                    const std::string& outputPath);

}  // namespace smartcampus

#endif
