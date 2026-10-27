#include "directory/index.hpp"
namespace directory {
std::vector<std::string> parse_path(const std::string& path) {
    if (path.empty() || path.front() != '/' || path.back() != '/' || path.find('\0') != std::string::npos)
        throw Error(ErrorCode::invalid_path, "Expected absolute directory path with trailing slash");
    if (path == "/") return {};
    std::vector<std::string> parts;
    std::size_t start = 1;
    while (start < path.size()) {
        auto end = path.find('/', start);
        auto part = path.substr(start, end-start);
        if (part.empty() || part == "." || part == "..")
            throw Error(ErrorCode::invalid_path, "Empty, dot and dot-dot segments are unsupported");
        parts.push_back(part);
        start = end+1;
    }
    return parts;
}
std::string parent_path(const std::string& path) {
    parse_path(path);
    if (path == "/") throw Error(ErrorCode::invalid_path, "Root has no parent");
    return path.substr(0, path.rfind('/', path.size()-2)+1);
}
std::string leaf_segment(const std::string& path) {
    auto parts = parse_path(path);
    if (parts.empty()) throw Error(ErrorCode::invalid_path, "Root has no segment");
    return parts.back();
}
bool at_or_below(const std::string& path, const std::string& anchor) {
    return path.compare(0, anchor.size(), anchor) == 0; // canonical anchors end in '/'
}
std::vector<std::string> ancestor_paths(const std::string& path) {
    auto parts = parse_path(path);
    std::vector<std::string> result{"/"};
    std::string current = "/";
    for (const auto& part : parts) { current += part+"/"; result.push_back(current); }
    return result;
}
} // namespace directory
