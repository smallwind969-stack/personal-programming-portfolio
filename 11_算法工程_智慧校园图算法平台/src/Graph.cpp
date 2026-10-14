#include "smartcampus/Graph.h"

#include <algorithm>
#include <cctype>
#include <limits>

namespace smartcampus {
namespace {

bool isIntegerText(const std::string& value) {
    if (value.empty()) {
        return false;
    }
    return std::all_of(value.begin(), value.end(), [](unsigned char ch) {
        return std::isdigit(ch) != 0;
    });
}

bool naturalIdLess(const std::string& left, const std::string& right) {
    const bool leftNumeric = isIntegerText(left);
    const bool rightNumeric = isIntegerText(right);
    if (leftNumeric && rightNumeric) {
        const int leftValue = std::stoi(left);
        const int rightValue = std::stoi(right);
        if (leftValue != rightValue) {
            return leftValue < rightValue;
        }
    }
    if (leftNumeric != rightNumeric) {
        return leftNumeric;
    }
    return left < right;
}

}  // namespace

void Graph::addLocation(const Location& location) {
    if (location.id.empty()) {
        throw std::invalid_argument("location id cannot be empty");
    }
    locations_[location.id] = location;
    adjacency_[location.id];
}

void Graph::addRoad(const std::string& from,
                    const std::string& to,
                    int weight,
                    bool directed,
                    const std::string& name) {
    if (!hasLocation(from) || !hasLocation(to)) {
        throw std::invalid_argument("road endpoint does not exist");
    }
    if (weight <= 0) {
        throw std::invalid_argument("road weight must be positive");
    }
    roads_.push_back({from, to, weight, directed, name});
    adjacency_[from].push_back({to, weight, name});
    if (!directed) {
        adjacency_[to].push_back({from, weight, name});
    }
}

bool Graph::hasLocation(const std::string& id) const {
    return locations_.find(id) != locations_.end();
}

const Location& Graph::location(const std::string& id) const {
    auto it = locations_.find(id);
    if (it == locations_.end()) {
        throw std::out_of_range("unknown location: " + id);
    }
    return it->second;
}

const std::map<std::string, Location>& Graph::locations() const {
    return locations_;
}

const std::vector<Road>& Graph::roads() const {
    return roads_;
}

const std::vector<AdjacentRoad>& Graph::neighbors(const std::string& id) const {
    auto it = adjacency_.find(id);
    if (it == adjacency_.end()) {
        throw std::out_of_range("unknown location: " + id);
    }
    return it->second;
}

std::vector<std::string> Graph::ids() const {
    std::vector<std::string> result;
    for (const auto& item : locations_) {
        result.push_back(item.first);
    }
    std::sort(result.begin(), result.end(), naturalIdLess);
    return result;
}

std::size_t Graph::locationCount() const {
    return locations_.size();
}

int Graph::edgeWeight(const std::string& from, const std::string& to) const {
    for (const auto& edge : neighbors(from)) {
        if (edge.to == to) {
            return edge.weight;
        }
    }
    return std::numeric_limits<int>::max() / 4;
}

}  // namespace smartcampus
