#pragma once
#include "directory/index.hpp"
#include <map>
#include <set>
#include <string>
#include <vector>

// Intentionally independent: no production path helper, bitmap posting or trie.
class Oracle {
    std::set<std::string> dirs_{"/"};
    std::map<directory::Id,std::string> entries_;
    static void valid(const std::string& path);
    static bool inside(const std::string& path,const std::string& parent);
    static std::string parent(const std::string& path);
    void required(const std::string& path) const;
public:
    struct Result { bool exists; std::set<directory::Id> ids; };
    void mkdir(const std::string& path);
    void insert(directory::Id id,const std::string& path);
    Result query(const std::string& path,bool recursive) const;
    void move(const std::string& source,const std::string& destination);
    void merge(const std::string& source,const std::string& target);
    std::vector<std::string> directories() const { return {dirs_.begin(),dirs_.end()}; }
    const auto& bindings() const { return entries_; }
};
