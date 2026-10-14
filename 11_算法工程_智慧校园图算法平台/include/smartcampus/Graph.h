#ifndef SMARTCAMPUS_GRAPH_H
#define SMARTCAMPUS_GRAPH_H

#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace smartcampus {

struct Location {
    std::string id;
    std::string name;
    double x;
    double y;
    std::string category;
};

struct Road {
    std::string from;
    std::string to;
    int weight;
    bool directed;
    std::string name;
};

struct AdjacentRoad {
    std::string to;
    int weight;
    std::string name;
};

class Graph {
public:
    void addLocation(const Location& location);
    void addRoad(const std::string& from,
                 const std::string& to,
                 int weight,
                 bool directed,
                 const std::string& name);

    bool hasLocation(const std::string& id) const;
    const Location& location(const std::string& id) const;
    const std::map<std::string, Location>& locations() const;
    const std::vector<Road>& roads() const;
    const std::vector<AdjacentRoad>& neighbors(const std::string& id) const;
    std::vector<std::string> ids() const;
    std::size_t locationCount() const;
    int edgeWeight(const std::string& from, const std::string& to) const;

private:
    std::map<std::string, Location> locations_;
    std::map<std::string, std::vector<AdjacentRoad>> adjacency_;
    std::vector<Road> roads_;
};

}  // namespace smartcampus

#endif
