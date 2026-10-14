#include "smartcampus/ReportWriter.h"

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <set>
#include <sstream>
#include <stdexcept>

namespace smartcampus {
namespace {

std::string labelFor(const Graph& graph, const std::string& id) {
    return graph.location(id).name;
}

bool containsRoadSegment(const PathResult& path, const std::string& a, const std::string& b) {
    for (std::size_t i = 1; i < path.nodes.size(); ++i) {
        if ((path.nodes[i - 1] == a && path.nodes[i] == b) ||
            (path.nodes[i - 1] == b && path.nodes[i] == a)) {
            return true;
        }
    }
    return false;
}

bool containsMstEdge(const MstResult& mst, const std::string& a, const std::string& b) {
    for (const auto& edge : mst.edges) {
        if ((edge.from == a && edge.to == b) || (edge.from == b && edge.to == a)) {
            return true;
        }
    }
    return false;
}

}  // namespace

void writeRouteReport(const Graph& graph,
                      const PathResult& path,
                      const MstResult& mst,
                      const std::string& outputPath) {
    std::ofstream out(outputPath);
    if (!out) {
        throw std::runtime_error("cannot write report: " + outputPath);
    }

    out << "# 智慧校园路线分析报告\n\n";
    out << "## 校园图规模\n\n";
    out << "- 地点数量：" << graph.locationCount() << "\n";
    out << "- 道路数量：" << graph.roads().size() << "\n";
    out << "- 是否连通：" << (mst.connected ? "是" : "否") << "\n\n";

    out << "## 推荐路线\n\n";
    if (!path.reachable) {
        out << "没有可达路线。\n\n";
    } else {
        out << "- 路线长度：" << path.distance << "\n";
        out << "- 搜索访问地点数：" << path.visitedNodes << "\n";
        out << "- 路线：";
        for (std::size_t i = 0; i < path.nodes.size(); ++i) {
            if (i != 0) {
                out << " -> ";
            }
            out << labelFor(graph, path.nodes[i]);
        }
        out << "\n\n";
    }

    out << "## 最小道路改造网络\n\n";
    out << "| 道路 | 起点 | 终点 | 成本 |\n";
    out << "| --- | --- | --- | ---: |\n";
    for (const auto& edge : mst.edges) {
        out << "| " << edge.name << " | " << labelFor(graph, edge.from) << " | "
            << labelFor(graph, edge.to) << " | " << edge.weight << " |\n";
    }
    out << "\n总成本：" << mst.totalWeight << "\n";
}

void writeCampusSvg(const Graph& graph,
                    const PathResult& highlightedPath,
                    const MstResult& mst,
                    const std::string& outputPath) {
    std::ofstream out(outputPath);
    if (!out) {
        throw std::runtime_error("cannot write svg: " + outputPath);
    }
    out << "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"820\" height=\"460\" viewBox=\"0 0 820 460\">\n";
    out << "<rect width=\"820\" height=\"460\" fill=\"#f7f8f3\"/>\n";
    out << "<text x=\"24\" y=\"34\" font-family=\"Microsoft YaHei, Arial\" font-size=\"22\" font-weight=\"700\" fill=\"#243447\">智慧校园图算法实验平台</text>\n";
    out << "<text x=\"24\" y=\"58\" font-family=\"Microsoft YaHei, Arial\" font-size=\"12\" fill=\"#546476\">蓝色表示最短路线，绿色表示最小道路改造网络</text>\n";

    for (const auto& road : graph.roads()) {
        const auto& a = graph.location(road.from);
        const auto& b = graph.location(road.to);
        const bool route = containsRoadSegment(highlightedPath, road.from, road.to);
        const bool mstEdge = containsMstEdge(mst, road.from, road.to);
        const char* color = route ? "#006dff" : (mstEdge ? "#1f9d55" : "#b8c0c8");
        const int width = route ? 6 : (mstEdge ? 4 : 2);
        out << "<line x1=\"" << a.x << "\" y1=\"" << a.y << "\" x2=\"" << b.x
            << "\" y2=\"" << b.y << "\" stroke=\"" << color << "\" stroke-width=\""
            << width << "\" stroke-linecap=\"round\" opacity=\"0.9\"/>\n";
        out << "<text x=\"" << (a.x + b.x) / 2 << "\" y=\"" << (a.y + b.y) / 2 - 4
            << "\" font-family=\"Microsoft YaHei, Arial\" font-size=\"10\" fill=\"#46515c\">" << road.weight
            << "</text>\n";
    }

    std::set<std::string> routeNodes(highlightedPath.nodes.begin(), highlightedPath.nodes.end());
    for (const auto& item : graph.locations()) {
        const auto& loc = item.second;
        const bool route = routeNodes.count(loc.id) > 0;
        out << "<circle cx=\"" << loc.x << "\" cy=\"" << loc.y << "\" r=\""
            << (route ? 12 : 9) << "\" fill=\"" << (route ? "#006dff" : "#ffffff")
            << "\" stroke=\"#243447\" stroke-width=\"2\"/>\n";
        out << "<text x=\"" << loc.x + 12 << "\" y=\"" << loc.y - 12
            << "\" font-family=\"Microsoft YaHei, Arial\" font-size=\"12\" font-weight=\"600\" fill=\"#243447\">"
            << loc.name << "</text>\n";
        out << "<text x=\"" << loc.x + 12 << "\" y=\"" << loc.y + 4
            << "\" font-family=\"Microsoft YaHei, Arial\" font-size=\"10\" fill=\"#687684\">" << loc.id
            << "</text>\n";
    }
    out << "</svg>\n";
}

}  // namespace smartcampus
