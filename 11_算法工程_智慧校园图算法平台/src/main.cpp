#include "smartcampus/CampusData.h"
#include "smartcampus/GraphAlgorithms.h"
#include "smartcampus/ReportWriter.h"

#include <cstdlib>
#include <exception>
#include <fstream>
#include <iostream>
#include <string>

using namespace smartcampus;

namespace {

void printLocations(const Graph& graph) {
    std::cout << "\n校园地点列表\n";
    for (const auto& id : graph.ids()) {
        const auto& loc = graph.location(id);
        std::cout << "  " << loc.id << " | " << loc.name << " | " << loc.category << '\n';
    }
}

void printPath(const Graph& graph, const PathResult& path) {
    if (!path.reachable) {
        std::cout << "没有找到可达路线。\n";
        return;
    }
    std::cout << "路线长度：" << path.distance << "，搜索访问地点数：" << path.visitedNodes << "\n";
    for (std::size_t i = 0; i < path.nodes.size(); ++i) {
        if (i != 0) {
            std::cout << " -> ";
        }
        std::cout << graph.location(path.nodes[i]).name;
    }
    std::cout << "\n";
}

void printMst(const Graph& graph, const MstResult& mst) {
    std::cout << "校园道路最小连通改造成本：" << mst.totalWeight << "\n";
    for (const auto& edge : mst.edges) {
        std::cout << "  " << edge.name << ": " << graph.location(edge.from).name
                  << " <-> " << graph.location(edge.to).name << " (" << edge.weight << ")\n";
    }
}

void printRouteSummary(const Graph& graph, const PathResult& path) {
    if (!path.reachable || path.nodes.empty()) {
        std::cout << "最近路线：暂无\n";
        return;
    }
    std::cout << "最近路线：";
    for (std::size_t i = 0; i < path.nodes.size(); ++i) {
        if (i != 0) {
            std::cout << " -> ";
        }
        std::cout << graph.location(path.nodes[i]).name;
    }
    std::cout << "，总权值：" << path.distance << "\n";
}

void printCampusMapPanel(const Graph& graph, const PathResult& lastPath) {
    std::cout << "\n==================== 校园地图与功能菜单 ====================\n";
    std::cout << "地点编号：\n";
    for (const auto& id : graph.ids()) {
        const auto& loc = graph.location(id);
        std::cout << "  " << loc.id << "." << loc.name;
        if (id == "4" || id == "8" || id == "12") {
            std::cout << "\n";
        } else {
            std::cout << "    ";
        }
    }
    std::cout << "\n道路拓扑图（括号内为道路权值，权值越小代表距离或通行成本越低）：\n";
    std::cout << "  11校园医务室 --5-- 2行政楼 --6-- 3中心图书馆 --4-- 4人工智能实验楼 --6-- 9月湖景区 --5-- 12创新创业中心\n";
    std::cout << "        |              |              |                     |                    |                  |\n";
    std::cout << "        8              5              3                     7                    6                  6\n";
    std::cout << "        |              |              |                     |                    |                  |\n";
    std::cout << "  3中心图书馆     1学校正门 --9-- 5第一教学楼 --9-- 7学生食堂 --5-- 8学生宿舍 --7-- 10田径运动场\n";
    std::cout << "                                      |              |       |\n";
    std::cout << "                                      7              4       6\n";
    std::cout << "                                      |              |       |\n";
    std::cout << "                                  6综合体育馆 --------       9月湖景区\n";
    printRouteSummary(graph, lastPath);
    std::cout << "============================================================\n";
}

std::string ask(const std::string& prompt) {
    std::cout << prompt;
    std::string value;
    std::cin >> value;
    return value;
}

bool fileExists(const std::string& path) {
    std::ifstream file(path);
    return file.good();
}

void openCampusMapPng() {
    const std::string pngPath = "output\\campus_map.png";
    if (!fileExists(pngPath)) {
        std::cout << "未找到校园地图图片：" << pngPath << "\n";
        std::cout << "请先确认提交包中包含 output/campus_map.png，或运行 scripts\\generate_campus_map_png.py 重新生成。\n";
        return;
    }
    std::cout << "正在打开校园地图图片：" << pngPath << "\n";
    const int code = std::system("start \"\" \"output\\campus_map.png\"");
    if (code != 0) {
        std::cout << "图片打开失败，请手动打开 output\\campus_map.png。\n";
    }
}

}  // namespace

int main() {
    try {
        Graph graph;
        try {
            graph = loadCampusGraph("data/locations.csv", "data/roads.csv");
        } catch (const std::exception&) {
            graph = buildDefaultCampusGraph();
        }

        PathResult lastPath = shortestPathDijkstra(graph, "1", "8");
        MstResult lastMst = minimumSpanningTreeKruskal(graph);

        while (true) {
            printCampusMapPanel(graph, lastPath);
            std::cout << "智慧校园图算法实验平台\n";
            std::cout << "1. 查看全部校园地点\n";
            std::cout << "2. 迪杰斯特拉最短路线查询\n";
            std::cout << "3. 启发式应急路线查询\n";
            std::cout << "4. 弗洛伊德多源路线查询\n";
            std::cout << "5. 广度优先和深度优先遍历\n";
            std::cout << "6. 克鲁斯卡尔最小道路改造方案\n";
            std::cout << "7. 导出地图和路线报告\n";
            std::cout << "8. 打开校园地图图片\n";
            std::cout << "0. 退出系统\n";
            std::cout << "请选择功能：";

            int choice = -1;
            if (!(std::cin >> choice)) {
                std::cout << "输入非法，系统退出。\n";
                return 0;
            }
            if (choice == 0) {
                break;
            }
            if (choice == 1) {
                printLocations(graph);
            } else if (choice == 2) {
                const std::string from = ask("起点编号：");
                const std::string to = ask("终点编号：");
                lastPath = shortestPathDijkstra(graph, from, to);
                printPath(graph, lastPath);
            } else if (choice == 3) {
                const std::string from = ask("起点编号：");
                const std::string to = ask("终点编号：");
                lastPath = shortestPathAStar(graph, from, to);
                printPath(graph, lastPath);
            } else if (choice == 4) {
                const std::string from = ask("起点编号：");
                const std::string to = ask("终点编号：");
                FloydResult floyd = shortestPathsFloydWarshall(graph);
                PathResult path;
                path.reachable = floyd.distance(from, to) < 100000000;
                path.distance = floyd.distance(from, to);
                path.nodes = floyd.path(from, to);
                lastPath = path;
                printPath(graph, path);
            } else if (choice == 5) {
                const std::string from = ask("起点编号：");
                auto bfs = breadthFirstSearch(graph, from);
                auto dfs = depthFirstSearch(graph, from);
                std::cout << "广度优先遍历：";
                for (const auto& id : bfs) {
                    std::cout << ' ' << id;
                }
                std::cout << "\n深度优先遍历：";
                for (const auto& id : dfs) {
                    std::cout << ' ' << id;
                }
                std::cout << "\n";
            } else if (choice == 6) {
                lastMst = minimumSpanningTreeKruskal(graph);
                printMst(graph, lastMst);
            } else if (choice == 7) {
                writeRouteReport(graph, lastPath, lastMst, "output/route_report.md");
                writeCampusSvg(graph, lastPath, lastMst, "output/campus_map.svg");
                std::cout << "已导出 output/route_report.md 和 output/campus_map.svg\n";
            } else if (choice == 8) {
                openCampusMapPng();
            } else {
                std::cout << "未知功能选项。\n";
            }
        }
    } catch (const std::exception& ex) {
        std::cerr << "系统错误：" << ex.what() << '\n';
        return 1;
    }
    return 0;
}
