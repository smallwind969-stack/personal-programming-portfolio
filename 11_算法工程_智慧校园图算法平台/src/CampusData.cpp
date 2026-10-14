#include "smartcampus/CampusData.h"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace smartcampus {
namespace {

std::vector<std::string> splitCsvLine(const std::string& line) {
    std::vector<std::string> cells;
    std::string cell;
    std::stringstream ss(line);
    while (std::getline(ss, cell, ',')) {
        cells.push_back(cell);
    }
    return cells;
}

}  // namespace

Graph loadCampusGraph(const std::string& locationFile, const std::string& roadFile) {
    Graph graph;
    std::ifstream locations(locationFile);
    if (!locations) {
        throw std::runtime_error("cannot open location file: " + locationFile);
    }
    std::string line;
    std::getline(locations, line);
    while (std::getline(locations, line)) {
        if (line.empty()) {
            continue;
        }
        auto cells = splitCsvLine(line);
        if (cells.size() != 5) {
            throw std::runtime_error("invalid location row: " + line);
        }
        graph.addLocation({cells[0], cells[1], std::stod(cells[2]), std::stod(cells[3]), cells[4]});
    }

    std::ifstream roads(roadFile);
    if (!roads) {
        throw std::runtime_error("cannot open road file: " + roadFile);
    }
    std::getline(roads, line);
    while (std::getline(roads, line)) {
        if (line.empty()) {
            continue;
        }
        auto cells = splitCsvLine(line);
        if (cells.size() != 5) {
            throw std::runtime_error("invalid road row: " + line);
        }
        graph.addRoad(cells[0], cells[1], std::stoi(cells[2]), cells[3] == "1", cells[4]);
    }
    return graph;
}

Graph buildDefaultCampusGraph() {
    Graph graph;
    graph.addLocation({"1", "学校正门", 40, 330, "入口"});
    graph.addLocation({"2", "行政楼", 150, 280, "服务"});
    graph.addLocation({"3", "中心图书馆", 270, 220, "学习"});
    graph.addLocation({"4", "人工智能实验楼", 390, 210, "科研"});
    graph.addLocation({"5", "第一教学楼", 250, 360, "教学"});
    graph.addLocation({"6", "综合体育馆", 420, 360, "运动"});
    graph.addLocation({"7", "学生食堂", 540, 300, "生活"});
    graph.addLocation({"8", "学生宿舍", 650, 210, "生活"});
    graph.addLocation({"9", "月湖景区", 500, 120, "景观"});
    graph.addLocation({"10", "田径运动场", 710, 380, "运动"});
    graph.addLocation({"11", "校园医务室", 120, 130, "服务"});
    graph.addLocation({"12", "创新创业中心", 610, 90, "科研"});

    graph.addRoad("1", "2", 5, false, "迎新大道");
    graph.addRoad("1", "5", 9, false, "学子大道");
    graph.addRoad("2", "3", 6, false, "求知路");
    graph.addRoad("2", "11", 5, false, "便民路");
    graph.addRoad("11", "3", 8, false, "健康步道");
    graph.addRoad("3", "4", 4, false, "知识桥");
    graph.addRoad("3", "5", 3, false, "书香步道");
    graph.addRoad("5", "6", 7, false, "课间环路");
    graph.addRoad("4", "9", 6, false, "科研小径");
    graph.addRoad("4", "7", 7, false, "创新步道");
    graph.addRoad("9", "12", 5, false, "月湖栈道");
    graph.addRoad("12", "8", 6, false, "创业路");
    graph.addRoad("7", "8", 5, false, "生活路");
    graph.addRoad("7", "6", 4, false, "运动步道");
    graph.addRoad("6", "10", 8, false, "竞技大道");
    graph.addRoad("8", "10", 7, false, "宿舍环路");
    graph.addRoad("9", "7", 6, false, "湖畔路");
    graph.addRoad("5", "7", 9, false, "午餐捷径");
    return graph;
}

}  // namespace smartcampus
