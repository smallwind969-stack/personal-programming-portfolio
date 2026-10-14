#include "smartcampus/GraphAlgorithms.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <queue>
#include <set>
#include <stack>
#include <stdexcept>

namespace smartcampus {
namespace {

constexpr int INF = std::numeric_limits<int>::max() / 4;

double euclidean(const Location& a, const Location& b) {
    const double dx = a.x - b.x;
    const double dy = a.y - b.y;
    return std::sqrt(dx * dx + dy * dy);
}

std::vector<std::string> rebuildPath(const std::map<std::string, std::string>& previous,
                                     const std::string& start,
                                     const std::string& goal) {
    std::vector<std::string> path;
    std::string current = goal;
    path.push_back(current);
    while (current != start) {
        auto it = previous.find(current);
        if (it == previous.end()) {
            return {};
        }
        current = it->second;
        path.push_back(current);
    }
    std::reverse(path.begin(), path.end());
    return path;
}

class DisjointSet {
public:
    explicit DisjointSet(const std::vector<std::string>& ids) {
        for (const auto& id : ids) {
            parent_[id] = id;
            rank_[id] = 0;
        }
    }

    std::string find(const std::string& id) {
        if (parent_[id] != id) {
            parent_[id] = find(parent_[id]);
        }
        return parent_[id];
    }

    bool unite(const std::string& a, const std::string& b) {
        std::string ra = find(a);
        std::string rb = find(b);
        if (ra == rb) {
            return false;
        }
        if (rank_[ra] < rank_[rb]) {
            std::swap(ra, rb);
        }
        parent_[rb] = ra;
        if (rank_[ra] == rank_[rb]) {
            ++rank_[ra];
        }
        return true;
    }

private:
    std::map<std::string, std::string> parent_;
    std::map<std::string, int> rank_;
};

}  // namespace

PathResult shortestPathDijkstra(const Graph& graph,
                                const std::string& start,
                                const std::string& goal) {
    if (!graph.hasLocation(start) || !graph.hasLocation(goal)) {
        throw std::invalid_argument("Dijkstra endpoint does not exist");
    }

    std::map<std::string, int> distance;
    std::map<std::string, std::string> previous;
    for (const auto& id : graph.ids()) {
        distance[id] = INF;
    }
    distance[start] = 0;

    using Node = std::pair<int, std::string>;
    std::priority_queue<Node, std::vector<Node>, std::greater<Node>> queue;
    queue.push({0, start});
    std::set<std::string> visited;

    while (!queue.empty()) {
        auto [currentDistance, current] = queue.top();
        queue.pop();
        if (visited.count(current)) {
            continue;
        }
        visited.insert(current);
        if (current == goal) {
            break;
        }
        for (const auto& edge : graph.neighbors(current)) {
            const int candidate = currentDistance + edge.weight;
            if (candidate < distance[edge.to]) {
                distance[edge.to] = candidate;
                previous[edge.to] = current;
                queue.push({candidate, edge.to});
            }
        }
    }

    PathResult result;
    result.visitedNodes = static_cast<int>(visited.size());
    if (distance[goal] < INF) {
        result.reachable = true;
        result.distance = distance[goal];
        result.nodes = rebuildPath(previous, start, goal);
        if (start == goal) {
            result.nodes = {start};
        }
    }
    return result;
}

PathResult shortestPathAStar(const Graph& graph,
                             const std::string& start,
                             const std::string& goal) {
    if (!graph.hasLocation(start) || !graph.hasLocation(goal)) {
        throw std::invalid_argument("A* endpoint does not exist");
    }

    std::map<std::string, int> gScore;
    std::map<std::string, std::string> previous;
    for (const auto& id : graph.ids()) {
        gScore[id] = INF;
    }
    gScore[start] = 0;

    using Node = std::pair<double, std::string>;
    std::priority_queue<Node, std::vector<Node>, std::greater<Node>> open;
    open.push({euclidean(graph.location(start), graph.location(goal)), start});
    std::set<std::string> visited;

    while (!open.empty()) {
        auto current = open.top().second;
        open.pop();
        if (visited.count(current)) {
            continue;
        }
        visited.insert(current);
        if (current == goal) {
            break;
        }
        for (const auto& edge : graph.neighbors(current)) {
            const int candidate = gScore[current] + edge.weight;
            if (candidate < gScore[edge.to]) {
                gScore[edge.to] = candidate;
                previous[edge.to] = current;
                const double priority =
                    candidate + euclidean(graph.location(edge.to), graph.location(goal));
                open.push({priority, edge.to});
            }
        }
    }

    PathResult result;
    result.visitedNodes = static_cast<int>(visited.size());
    if (gScore[goal] < INF) {
        result.reachable = true;
        result.distance = gScore[goal];
        result.nodes = rebuildPath(previous, start, goal);
        if (start == goal) {
            result.nodes = {start};
        }
    }
    return result;
}

FloydResult shortestPathsFloydWarshall(const Graph& graph) {
    FloydResult result;
    result.ids_ = graph.ids();
    const int n = static_cast<int>(result.ids_.size());
    result.dist_.assign(n, std::vector<int>(n, INF));
    result.next_.assign(n, std::vector<int>(n, -1));

    for (int i = 0; i < n; ++i) {
        result.index_[result.ids_[i]] = i;
        result.dist_[i][i] = 0;
        result.next_[i][i] = i;
    }
    for (int i = 0; i < n; ++i) {
        for (const auto& edge : graph.neighbors(result.ids_[i])) {
            const int j = result.index_[edge.to];
            if (edge.weight < result.dist_[i][j]) {
                result.dist_[i][j] = edge.weight;
                result.next_[i][j] = j;
            }
        }
    }
    for (int k = 0; k < n; ++k) {
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                if (result.dist_[i][k] + result.dist_[k][j] < result.dist_[i][j]) {
                    result.dist_[i][j] = result.dist_[i][k] + result.dist_[k][j];
                    result.next_[i][j] = result.next_[i][k];
                }
            }
        }
    }
    return result;
}

int FloydResult::distance(const std::string& from, const std::string& to) const {
    auto a = index_.find(from);
    auto b = index_.find(to);
    if (a == index_.end() || b == index_.end()) {
        throw std::invalid_argument("Floyd endpoint does not exist");
    }
    return dist_[a->second][b->second];
}

std::vector<std::string> FloydResult::path(const std::string& from, const std::string& to) const {
    auto a = index_.find(from);
    auto b = index_.find(to);
    if (a == index_.end() || b == index_.end()) {
        throw std::invalid_argument("Floyd endpoint does not exist");
    }
    int i = a->second;
    const int j = b->second;
    if (next_[i][j] == -1) {
        return {};
    }
    std::vector<std::string> route{ids_[i]};
    while (i != j) {
        i = next_[i][j];
        route.push_back(ids_[i]);
    }
    return route;
}

MstResult minimumSpanningTreeKruskal(const Graph& graph) {
    std::vector<Road> edges = graph.roads();
    std::sort(edges.begin(), edges.end(), [](const Road& a, const Road& b) {
        if (a.weight != b.weight) {
            return a.weight < b.weight;
        }
        return a.name < b.name;
    });

    DisjointSet sets(graph.ids());
    MstResult result;
    for (const auto& edge : edges) {
        if (sets.unite(edge.from, edge.to)) {
            result.totalWeight += edge.weight;
            result.edges.push_back({edge.from, edge.to, edge.weight, edge.name});
        }
    }
    result.connected = graph.locationCount() == 0 ||
                       result.edges.size() + 1 == graph.locationCount();
    return result;
}

MstResult minimumSpanningTreePrim(const Graph& graph, const std::string& start) {
    if (!graph.hasLocation(start)) {
        throw std::invalid_argument("Prim start does not exist");
    }
    struct Candidate {
        int weight;
        std::string from;
        std::string to;
        std::string name;
        bool operator>(const Candidate& other) const {
            return weight > other.weight;
        }
    };

    MstResult result;
    std::set<std::string> used;
    std::priority_queue<Candidate, std::vector<Candidate>, std::greater<Candidate>> queue;
    used.insert(start);
    for (const auto& edge : graph.neighbors(start)) {
        queue.push({edge.weight, start, edge.to, edge.name});
    }

    while (!queue.empty() && used.size() < graph.locationCount()) {
        Candidate current = queue.top();
        queue.pop();
        if (used.count(current.to)) {
            continue;
        }
        used.insert(current.to);
        result.totalWeight += current.weight;
        result.edges.push_back({current.from, current.to, current.weight, current.name});
        for (const auto& edge : graph.neighbors(current.to)) {
            if (!used.count(edge.to)) {
                queue.push({edge.weight, current.to, edge.to, edge.name});
            }
        }
    }
    result.connected = used.size() == graph.locationCount();
    return result;
}

std::vector<std::string> breadthFirstSearch(const Graph& graph, const std::string& start) {
    if (!graph.hasLocation(start)) {
        throw std::invalid_argument("BFS start does not exist");
    }
    std::vector<std::string> order;
    std::set<std::string> visited{start};
    std::queue<std::string> queue;
    queue.push(start);
    while (!queue.empty()) {
        std::string current = queue.front();
        queue.pop();
        order.push_back(current);
        for (const auto& edge : graph.neighbors(current)) {
            if (!visited.count(edge.to)) {
                visited.insert(edge.to);
                queue.push(edge.to);
            }
        }
    }
    return order;
}

std::vector<std::string> depthFirstSearch(const Graph& graph, const std::string& start) {
    if (!graph.hasLocation(start)) {
        throw std::invalid_argument("DFS start does not exist");
    }
    std::vector<std::string> order;
    std::set<std::string> visited;
    std::stack<std::string> stack;
    stack.push(start);
    while (!stack.empty()) {
        std::string current = stack.top();
        stack.pop();
        if (visited.count(current)) {
            continue;
        }
        visited.insert(current);
        order.push_back(current);
        const auto& neighbors = graph.neighbors(current);
        for (auto it = neighbors.rbegin(); it != neighbors.rend(); ++it) {
            if (!visited.count(it->to)) {
                stack.push(it->to);
            }
        }
    }
    return order;
}

bool isConnected(const Graph& graph) {
    if (graph.locationCount() == 0) {
        return true;
    }
    return breadthFirstSearch(graph, graph.ids().front()).size() == graph.locationCount();
}

}  // namespace smartcampus
