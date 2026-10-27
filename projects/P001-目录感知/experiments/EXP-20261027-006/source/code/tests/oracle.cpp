#include "oracle.hpp"
using directory::Error;
using directory::ErrorCode;
void Oracle::valid(const std::string& path) {
    if (path.size()==0 || path[0]!='/' || path[path.size()-1]!='/' || path.find(char(0))!=std::string::npos)
        throw Error(ErrorCode::invalid_path,"Oracle: malformed path");
    if (path=="/") return;
    std::string segment;
    for (std::size_t i=1;i<path.size();++i) {
        if (path[i]=='/') {
            if (segment.empty() || segment=="." || segment=="..") throw Error(ErrorCode::invalid_path,"Oracle: malformed segment");
            segment.clear();
        } else segment+=path[i];
    }
}
bool Oracle::inside(const std::string& path,const std::string& anchor) {
    if (anchor=="/") return true;
    return path.size()>=anchor.size() && path.substr(0,anchor.size())==anchor;
}
std::string Oracle::parent(const std::string& path) {
    auto without_final=path.substr(0,path.size()-1);
    return without_final.substr(0,without_final.find_last_of('/')+1);
}
void Oracle::required(const std::string& path) const {
    valid(path);
    if (!dirs_.count(path)) throw Error(ErrorCode::missing_directory,"Oracle: missing directory");
}
void Oracle::mkdir(const std::string& path) {
    valid(path);
    for (std::size_t i=0;i<path.size();++i) if (path[i]=='/') dirs_.insert(path.substr(0,i+1));
}
void Oracle::insert(directory::Id id,const std::string& path) {
    valid(path);
    if (entries_.count(id)) throw Error(ErrorCode::duplicate_id,"Oracle: duplicate ID");
    mkdir(path); entries_.emplace(id,path);
}
Oracle::Result Oracle::query(const std::string& path,bool recursive) const {
    valid(path);
    Result result{dirs_.count(path)!=0,{}};
    if (result.exists) for (const auto& entry:entries_)
        if (recursive ? inside(entry.second,path) : entry.second==path) result.ids.insert(entry.first);
    return result;
}
void Oracle::move(const std::string& source,const std::string& destination) {
    required(source); required(destination);
    if (source=="/" || inside(destination,source)) throw Error(ErrorCode::invalid_move,"Oracle: illegal move");
    if (parent(source)==destination) return;
    auto stem=source.substr(0,source.size()-1);
    auto name=stem.substr(stem.find_last_of('/')+1);
    auto replacement=destination+name+"/";
    if (dirs_.count(replacement)) throw Error(ErrorCode::name_conflict,"Oracle: conflicting name");
    std::set<std::string> rebuilt;
    for (const auto& path:dirs_) rebuilt.insert(inside(path,source) ? replacement+path.substr(source.size()) : path);
    auto entries=entries_;
    for (auto& entry:entries) if (inside(entry.second,source)) entry.second=replacement+entry.second.substr(source.size());
    dirs_.swap(rebuilt); entries_.swap(entries);
}
void Oracle::merge(const std::string& source,const std::string& target) {
    required(source); required(target);
    if (inside(source,target) || inside(target,source)) throw Error(ErrorCode::invalid_merge,"Oracle: overlapping merge");
    std::set<std::string> rebuilt;
    for (const auto& path:dirs_) rebuilt.insert(inside(path,source) ? target+path.substr(source.size()) : path);
    auto entries=entries_;
    for (auto& entry:entries) if (inside(entry.second,source)) entry.second=target+entry.second.substr(source.size());
    dirs_.swap(rebuilt); entries_.swap(entries);
}
