#include "smartcampus/Graph.h"
#include "smartcampus/GraphAlgorithms.h"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace smartcampus;

static void assert_true(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

static Graph build_demo_graph() {
    Graph graph;
    graph.addLocation({"1", "学校正门", 0, 0, "入口"});
    graph.addLocation({"2", "中心图书馆", 2, 2, "学习"});
    graph.addLocation({"3", "人工智能实验楼", 5, 2, "科研"});
    graph.addLocation({"4", "综合体育馆", 3, -1, "运动"});
    graph.addLocation({"5", "学生宿舍", 7, 0, "生活"});
    graph.addRoad("1", "2", 3, false, "南区大道");
    graph.addRoad("2", "3", 4, false, "创新步道");
    graph.addRoad("1", "4", 2, false, "枫林路");
    graph.addRoad("4", "5", 12, false, "滨河路");
    graph.addRoad("3", "5", 3, false, "科研路");
    graph.addRoad("2", "4", 2, false, "书香桥");
    return graph;
}

static void dijkstra_finds_weighted_shortest_path() {
    Graph graph = build_demo_graph();
    PathResult path = shortestPathDijkstra(graph, "1", "5");
    assert_true(path.reachable, "宿舍应当能从校门到达");
    assert_true(path.distance == 10, "校门到宿舍的最短距离应为10");
    assert_true(path.nodes == std::vector<std::string>({"1", "2", "3", "5"}),
                "迪杰斯特拉算法应返回预期路线");
}

static void astar_matches_dijkstra_on_campus_coordinates() {
    Graph graph = build_demo_graph();
    PathResult dijkstra = shortestPathDijkstra(graph, "1", "5");
    PathResult astar = shortestPathAStar(graph, "1", "5");
    assert_true(astar.reachable, "启发式寻路算法应找到路线");
    assert_true(astar.distance == dijkstra.distance, "启发式寻路算法和迪杰斯特拉算法的距离应一致");
}

static void kruskal_builds_minimum_renovation_plan() {
    Graph graph = build_demo_graph();
    MstResult mst = minimumSpanningTreeKruskal(graph);
    assert_true(mst.connected, "测试图应当连通");
    assert_true(mst.totalWeight == 11, "最小生成树总权值应为11");
    assert_true(mst.edges.size() == 4, "最小生成树应包含顶点数减一条边");
}

static void traversal_visits_all_reachable_locations() {
    Graph graph = build_demo_graph();
    std::vector<std::string> bfs = breadthFirstSearch(graph, "1");
    std::vector<std::string> dfs = depthFirstSearch(graph, "1");
    assert_true(bfs.size() == graph.locationCount(), "广度优先搜索应访问所有地点");
    assert_true(dfs.size() == graph.locationCount(), "深度优先搜索应访问所有地点");
    assert_true(bfs.front() == "1", "广度优先搜索应从指定地点开始");
    assert_true(dfs.front() == "1", "深度优先搜索应从指定地点开始");
}

static void floyd_supports_multi_source_queries() {
    Graph graph = build_demo_graph();
    FloydResult floyd = shortestPathsFloydWarshall(graph);
    assert_true(floyd.distance("1", "5") == 10, "弗洛伊德算法计算的校门到宿舍距离应为10");
    assert_true(floyd.path("1", "5") == std::vector<std::string>({"1", "2", "3", "5"}),
                "弗洛伊德算法应还原最短路线");
}

static void location_ids_are_sorted_by_numeric_value_when_possible() {
    Graph graph;
    graph.addLocation({"1", "学校正门", 0, 0, "入口"});
    graph.addLocation({"10", "田径运动场", 0, 0, "运动"});
    graph.addLocation({"2", "行政楼", 0, 0, "服务"});
    graph.addLocation({"11", "校园医务室", 0, 0, "服务"});
    assert_true(graph.ids() == std::vector<std::string>({"1", "2", "10", "11"}),
                "数字编号应按数值大小排序，而不是按字符串字典序排序");
}

int main() {
    try {
        dijkstra_finds_weighted_shortest_path();
        astar_matches_dijkstra_on_campus_coordinates();
        kruskal_builds_minimum_renovation_plan();
        traversal_visits_all_reachable_locations();
        floyd_supports_multi_source_queries();
        location_ids_are_sorted_by_numeric_value_when_possible();
    } catch (const std::exception& ex) {
        std::cerr << "[失败] " << ex.what() << '\n';
        return EXIT_FAILURE;
    }
    std::cout << "[通过] 图算法回归测试\n";
    return EXIT_SUCCESS;
}
