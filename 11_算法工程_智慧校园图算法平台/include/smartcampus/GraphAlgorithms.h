#ifndef SMARTCAMPUS_GRAPH_ALGORITHMS_H
#define SMARTCAMPUS_GRAPH_ALGORITHMS_H

#include "smartcampus/Graph.h"

#include <map>
#include <string>
#include <vector>

namespace smartcampus {

struct PathResult {
    bool reachable = false;
    int distance = 0;
    std::vector<std::string> nodes;
    int visitedNodes = 0;
};

struct MstEdge {
    std::string from;
    std::string to;
    int weight;
    std::string name;
};

struct MstResult {
    bool connected = false;
    int totalWeight = 0;
    std::vector<MstEdge> edges;
};

class FloydResult {
public:
    int distance(const std::string& from, const std::string& to) const;
    std::vector<std::string> path(const std::string& from, const std::string& to) const;

private:
    friend FloydResult shortestPathsFloydWarshall(const Graph& graph);
    std::vector<std::string> ids_;
    std::map<std::string, int> index_;
    std::vector<std::vector<int>> dist_;
    std::vector<std::vector<int>> next_;
};

PathResult shortestPathDijkstra(const Graph& graph,
                                const std::string& start,
                                const std::string& goal);
PathResult shortestPathAStar(const Graph& graph,
                             const std::string& start,
                             const std::string& goal);
FloydResult shortestPathsFloydWarshall(const Graph& graph);
MstResult minimumSpanningTreeKruskal(const Graph& graph);
MstResult minimumSpanningTreePrim(const Graph& graph, const std::string& start);
std::vector<std::string> breadthFirstSearch(const Graph& graph, const std::string& start);
std::vector<std::string> depthFirstSearch(const Graph& graph, const std::string& start);
bool isConnected(const Graph& graph);

}  // namespace smartcampus

#endif
