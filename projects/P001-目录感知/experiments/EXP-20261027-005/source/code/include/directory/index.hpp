#pragma once
// Single-parent directory semantics: paper Sections III/IV, PDF pp. 4-7.
#include "directory/bitmap.hpp"
#include <cstdint>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace directory {
using Id = std::uint32_t;

enum class ErrorCode { invalid_path, missing_directory, duplicate_id, invalid_move, invalid_merge, name_conflict };
struct Error : std::runtime_error {
    ErrorCode code;
    Error(ErrorCode c, const std::string& message) : std::runtime_error(message), code(c) {}
};
struct QueryResult { bool exists; Bitmap ids; };
// Work counts are populated only by the separately compiled instrumented core.
struct QueryWork {
    std::size_t path_segments = 0;
    std::size_t directories_visited = 0;
    std::size_t direct_children = 0;
    std::size_t bitmaps_read = 0;
    std::size_t bitmap_copies = 0;
    std::size_t bitmap_unions = 0;
    std::size_t bitmap_differences = 0;
};
// Observable logical counts and portable sizes, not allocator/process memory.
struct IndexStatistics {
    std::size_t directory_count = 0;
    std::size_t catalog_entry_count = 0;
    std::size_t bitmap_count = 0;
    std::size_t roaring_portable_bytes = 0;
};
struct MaintenanceWork {
    std::size_t remapped_path_keys = 0;
    std::size_t relinked_subtrees = 0;
    std::size_t reconciled_nodes = 0;
    std::size_t catalog_entries_scanned = 0;
};
// Validation/debug accessors are NOT used on the scope-resolution path.
class Index {
public:
    virtual ~Index() = default;
    virtual std::string name() const = 0;
    virtual void mkdir(const std::string& path) = 0;
    virtual void insert(Id id, const std::string& parent) = 0;
    virtual QueryResult query(const std::string& path, bool recursive) const = 0;
    virtual void move(const std::string& source, const std::string& new_parent) = 0;
    virtual void merge(const std::string& source, const std::string& target) = 0;
    virtual std::vector<std::string> directories() const = 0;
    virtual std::map<Id, std::string> bindings() const = 0;
    virtual std::vector<std::string> validate() const = 0;
    virtual std::uint64_t identity(const std::string& path) const = 0;
    virtual MaintenanceWork last_maintenance_work() const = 0;
    virtual QueryWork last_query_work() const = 0;
    virtual IndexStatistics statistics() const = 0;
};
enum class Strategy { pe_online, pe_offline, trie_hi };
std::unique_ptr<Index> make_index(Strategy strategy);
std::vector<std::string> parse_path(const std::string& path);
std::string parent_path(const std::string& path);
std::string leaf_segment(const std::string& path);
bool at_or_below(const std::string& path, const std::string& anchor);
std::vector<std::string> ancestor_paths(const std::string& path);
} // namespace directory
