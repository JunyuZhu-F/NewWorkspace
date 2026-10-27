#include "directory/index.hpp"
#include "directory/diagnostics.hpp"
#include <algorithm>
#include <functional>
#include <set>
#include <unordered_map>
#include <utility>

namespace directory {
namespace {
struct Token { std::uint64_t uid; explicit Token(std::uint64_t id) : uid(id) {} };
// Common bookkeeping only. Scope queries never inspect this catalog.
class Catalog {
    std::map<Id, Token*> entries_ DIR_CATALOG_INIT;
public:
    DIR_CATALOG_CONTROL
    bool contains(Id id) const { DIR_CATALOG_SCOPE return entries_.find(id)!=entries_.end(); }
    void bind(Id id, Token* directory) { DIR_CATALOG_SCOPE
        if (!entries_.emplace(id,directory).second) throw Error(ErrorCode::duplicate_id,"Duplicate payload ID");
    }
    void rebind(Token* source, Token* target, MaintenanceWork& work) { DIR_CATALOG_SCOPE
        // Deliberately simple common catalog; scans are reported separately.
        for (auto& entry : entries_) {
            ++work.catalog_entries_scanned;
            if (entry.second==source) entry.second=target;
        }
    }
    const auto& entries() const { return entries_; }
    std::size_t size() const { return entries_.size(); }
};
struct FlatNode : Token {
    std::string path;
    Bitmap posting;
    FlatNode(std::uint64_t id, std::string p) : Token(id), path(std::move(p)) {}
};
class FlatIndex final : public Index {
    bool offline_;
    std::uint64_t next_uid_=1;
    std::map<std::string,std::unique_ptr<FlatNode>> nodes_;
    // Auxiliary directory index: path keys, subtree-prefix enumeration and direct-child lookup.
    std::map<std::string,std::set<std::string>> children_;
    Catalog catalog_;
    MaintenanceWork work_;
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
    mutable QueryWork query_work_;
#endif
    FlatNode& required(const std::string& path) const {
        DIR_PHASE(locate)
        parse_path(path);
        auto it=DIR_VALUE(locate, nodes_.find(path));
        if (it==nodes_.end()) throw Error(ErrorCode::missing_directory,"Directory missing: "+path);
        return *it->second;
    }
    std::vector<std::string> subtree(const std::string& path) const {
        std::vector<std::string> result;
        for (auto it=nodes_.lower_bound(path); it!=nodes_.end() && at_or_below(it->first,path); ++it)
            result.push_back(it->first);
        return result;
    }
    void update_ancestors(const std::string& old_root,const std::string& new_root,const Bitmap& ids) {
        DIR_CORE(ancestors)
        auto old_list=ancestor_paths(old_root), new_list=ancestor_paths(new_root);
        old_list.pop_back(); new_list.pop_back();
        std::set<std::string> old_set(old_list.begin(),old_list.end()),new_set(new_list.begin(),new_list.end());
        for (const auto& p:old_set) if (!new_set.count(p)) nodes_.at(p)->posting-=ids;
        for (const auto& p:new_set) if (!old_set.count(p)) nodes_.at(p)->posting|=ids;
    }
    struct Detached { std::string old_path; std::unique_ptr<FlatNode> node; };
    std::vector<Detached> detach_subtree(const std::string& source) {
        auto paths=subtree(source);
        children_.at(parent_path(source)).erase(source);
        std::vector<Detached> result;
        for (const auto& p:paths) {
            auto it=nodes_.find(p);
            result.push_back({p,std::move(it->second)});
            nodes_.erase(it);
            children_.erase(p);
        }
        return result;
    }
public:
    explicit FlatIndex(bool offline) : offline_(offline) {
        nodes_.emplace("/",std::make_unique<FlatNode>(next_uid_++,"/"));
        children_.emplace("/",std::set<std::string>{});
    }
    std::string name() const override { return offline_ ? "PE-OFFLINE" : "PE-ONLINE"; }
    void mkdir(const std::string& path) override {
        DIR_CORE(directory)
        auto ancestors=ancestor_paths(path); // validate everything before mutation
        for (const auto& p:ancestors) if (!nodes_.count(p)) {
            auto node=std::make_unique<FlatNode>(next_uid_++,p);
            nodes_.emplace(p,std::move(node));
            children_.emplace(p,std::set<std::string>{});
            children_.at(parent_path(p)).insert(p);
        }
    }
    void insert(Id id,const std::string& path) override {
        DIR_CORE(directory)
        parse_path(path);
        if (catalog_.contains(id)) throw Error(ErrorCode::duplicate_id,"Duplicate payload ID");
        mkdir(path);
        catalog_.bind(id,nodes_.at(path).get());
        if (offline_) for (const auto& p:ancestor_paths(path)) nodes_.at(p)->posting.add(id);
        else nodes_.at(path)->posting.add(id);
    }
    QueryResult query(const std::string& path,bool recursive) const override {
        DIR_CORE(directory)
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
        query_work_={};
        query_work_.path_segments=parse_path(path).size();
#else
        parse_path(path);
#endif
        auto it=DIR_VALUE(locate, nodes_.find(path));
        if (it==nodes_.end()) return {false,Bitmap{}};
        if (offline_) {
            Bitmap result=it->second->posting;
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
            query_work_.directories_visited=1;
            query_work_.direct_children=children_.at(path).size();
            query_work_.bitmaps_read=1;
            query_work_.bitmap_copies=1;
#endif
            if (!recursive) {
                Bitmap descendants;
                for (const auto& child:children_.at(path)) descendants|=nodes_.at(child)->posting;
                result-=descendants;
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
                query_work_.directories_visited+=query_work_.direct_children;
                query_work_.bitmaps_read+=query_work_.direct_children;
                query_work_.bitmap_unions=query_work_.direct_children;
                query_work_.bitmap_differences=1;
#endif
            }
            return {true,std::move(result)};
        }
        if (!recursive) {
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
            query_work_.directories_visited=1;
            query_work_.direct_children=children_.at(path).size();
            query_work_.bitmaps_read=1;
            query_work_.bitmap_copies=1;
#endif
            return {true,it->second->posting};
        }
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
        const auto paths=subtree(path);
        query_work_.directories_visited=paths.size();
        query_work_.direct_children=children_.at(path).size();
        query_work_.bitmaps_read=paths.size();
        query_work_.bitmap_unions=paths.size();
        Bitmap result;
        for (const auto& p:paths) result|=nodes_.at(p)->posting;
#else
        Bitmap result;
        for (const auto& p:subtree(path)) result|=nodes_.at(p)->posting;
#endif
        return {true,std::move(result)};
    }
    void move(const std::string& source,const std::string& destination) override {
        DIR_CORE(directory)
        work_={};
        auto& source_node=required(source); required(destination);
        if (source=="/" || at_or_below(destination,source))
            throw Error(ErrorCode::invalid_move,"Move would relocate root or form a cycle");
        if (parent_path(source)==destination) { work_={}; return; }
        auto new_root=destination+leaf_segment(source)+"/";
        if (nodes_.count(new_root)) throw Error(ErrorCode::name_conflict,"Move destination name exists");
        Bitmap ids;
        if (offline_) ids=source_node.posting;
        work_={};
        auto detached=detach_subtree(source);
        std::vector<std::string> new_paths;
        for (auto& item:detached) {
            auto p=new_root+item.old_path.substr(source.size());
            item.node->path=p;
            nodes_.emplace(p,std::move(item.node));
            children_.emplace(p,std::set<std::string>{});
            new_paths.push_back(p);
            ++work_.remapped_path_keys;
        }
        for (const auto& p:new_paths) children_.at(parent_path(p)).insert(p);
        if (offline_) update_ancestors(source,new_root,ids);
    }
    void merge(const std::string& source,const std::string& target) override {
        DIR_CORE(directory)
        work_={};
        auto& source_node=required(source); required(target);
        if (at_or_below(source,target) || at_or_below(target,source))
            throw Error(ErrorCode::invalid_merge,"Merge roots must be disjoint");
        Bitmap ids;
        if (offline_) ids=source_node.posting;
        work_={};
        auto detached=detach_subtree(source);
        for (auto& item:detached) {
            auto p=target+item.old_path.substr(source.size());
            auto existing=nodes_.find(p);
            if (existing!=nodes_.end()) {
                existing->second->posting|=item.node->posting;
                catalog_.rebind(item.node.get(),existing->second.get(),work_);
            } else {
                item.node->path=p;
                nodes_.emplace(p,std::move(item.node));
                children_.emplace(p,std::set<std::string>{});
            }
            children_.at(parent_path(p)).insert(p);
            ++work_.remapped_path_keys;
            ++work_.reconciled_nodes;
        }
        // Target root was already unioned above; only its proper ancestors are updated here.
        if (offline_) update_ancestors(source,target,ids);
    }
    std::vector<std::string> directories() const override {
        std::vector<std::string> result;
        for (const auto& item:nodes_) result.push_back(item.first);
        return result;
    }
    std::map<Id,std::string> bindings() const override {
        std::map<Id,std::string> result;
        for (const auto& entry:catalog_.entries()) result.emplace(entry.first,static_cast<FlatNode*>(entry.second)->path);
        return result;
    }
    std::uint64_t identity(const std::string& p) const override { return required(p).uid; }
    MaintenanceWork last_maintenance_work() const override { return work_; }
    QueryWork last_query_work() const override {
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
        return query_work_;
#else
        return {};
#endif
    }
    IndexStatistics statistics() const override {
        IndexStatistics result;
        result.directory_count=nodes_.size();
        result.catalog_entry_count=catalog_.size();
        result.bitmap_count=nodes_.size();
        for (const auto& item:nodes_) result.roaring_portable_bytes+=item.second->posting.portable_size();
        return result;
    }
    std::vector<std::string> validate() const override {
        std::vector<std::string> errors;
        if (!nodes_.count("/") || nodes_.size()!=children_.size()) errors.push_back("directory/auxiliary size or root mismatch");
        std::set<Token*> active;
        std::map<std::string,Bitmap> expected;
        std::map<std::string,std::set<std::string>> expected_children;
        for (const auto& item:nodes_) {
            active.insert(item.second.get()); expected[item.first]; expected_children[item.first];
            if (item.second->path!=item.first) errors.push_back("path key mismatch");
            if (item.first!="/") expected_children[parent_path(item.first)].insert(item.first);
        }
        if (expected_children!=children_) errors.push_back("auxiliary child index mismatch");
        for (const auto& entry:catalog_.entries()) {
            if (!active.count(entry.second)) { errors.push_back("dangling catalog directory"); continue; }
            auto* node=static_cast<FlatNode*>(entry.second);
            if (offline_) for (const auto& p:ancestor_paths(node->path)) expected[p].add(entry.first);
            else expected[node->path].add(entry.first);
        }
        for (const auto& item:nodes_) if (item.second->posting!=expected.at(item.first))
            errors.push_back("posting invariant failed: "+item.first);
        return errors;
    }
};

struct TrieNode : Token {
    std::string segment;
    TrieNode* parent;
    std::unordered_map<std::string,std::unique_ptr<TrieNode>> children;
    Bitmap inclusive;
    TrieNode(std::uint64_t id,std::string name,TrieNode* p) : Token(id),segment(std::move(name)),parent(p) {}
};
class TrieIndex final : public Index {
    std::uint64_t next_uid_=1;
    std::unique_ptr<TrieNode> root_=std::make_unique<TrieNode>(next_uid_++,"",nullptr);
    Catalog catalog_;
    MaintenanceWork work_;
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
    mutable QueryWork query_work_;
#endif
    TrieNode* locate(const std::string& path) const {
        DIR_PHASE(locate)
        auto segments=parse_path(path);
        auto* current=root_.get();
        for (const auto& segment:segments) {
            auto it=current->children.find(segment);
            if (it==current->children.end()) return nullptr;
            current=it->second.get();
        }
        return current;
    }
    TrieNode& required(const std::string& path) const {
        auto* node=locate(path);
        if (!node) throw Error(ErrorCode::missing_directory,"Directory missing: "+path);
        return *node;
    }
    static std::string path_of(const TrieNode* node) {
        std::vector<std::string> segments;
        for (auto* p=node;p->parent;p=p->parent) segments.push_back(p->segment);
        std::string result="/";
        for (auto it=segments.rbegin();it!=segments.rend();++it) result+=*it+"/";
        return result;
    }
    static std::set<TrieNode*> proper_ancestors(TrieNode* node) {
        std::set<TrieNode*> result;
        for (auto* p=node->parent;p;p=p->parent) result.insert(p);
        return result;
    }
    static void update_ancestors(const std::set<TrieNode*>& old_set,const std::set<TrieNode*>& new_set,const Bitmap& ids) {
        DIR_CORE(ancestors)
        for (auto* p:old_set) if (!new_set.count(p)) p->inclusive-=ids;
        for (auto* p:new_set) if (!old_set.count(p)) p->inclusive|=ids;
    }
    void reconcile(std::unique_ptr<TrieNode> source,TrieNode& target) {
        ++work_.reconciled_nodes;
        target.inclusive|=source->inclusive;
        catalog_.rebind(source.get(),&target,work_); // direct bindings only; descendants retain node identity
        for (auto& child:source->children) {
            auto it=target.children.find(child.first);
            if (it==target.children.end()) {
                child.second->parent=&target;
                target.children.emplace(child.first,std::move(child.second));
                ++work_.relinked_subtrees;
            } else reconcile(std::move(child.second),*it->second);
        }
    }
public:
    std::string name() const override { return "TrieHI"; }
    void mkdir(const std::string& path) override {
        DIR_CORE(directory)
        auto segments=parse_path(path);
        auto* node=root_.get();
        for (const auto& segment:segments) {
            auto it=node->children.find(segment);
            if (it==node->children.end()) {
                auto child=std::make_unique<TrieNode>(next_uid_++,segment,node);
                it=node->children.emplace(segment,std::move(child)).first;
            }
            node=it->second.get();
        }
    }
    void insert(Id id,const std::string& path) override {
        DIR_CORE(directory)
        parse_path(path);
        if (catalog_.contains(id)) throw Error(ErrorCode::duplicate_id,"Duplicate payload ID");
        mkdir(path);
        auto* node=locate(path);
        catalog_.bind(id,node);
        for (auto* p=node;p;p=p->parent) p->inclusive.add(id);
    }
    QueryResult query(const std::string& path,bool recursive) const override {
        DIR_CORE(directory)
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
        query_work_={};
        query_work_.path_segments=parse_path(path).size();
#endif
        auto* node=locate(path);
        if (!node) return {false,Bitmap{}};
        Bitmap result=node->inclusive;
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
        query_work_.directories_visited=1;
        query_work_.direct_children=node->children.size();
        query_work_.bitmaps_read=1;
        query_work_.bitmap_copies=1;
#endif
        if (!recursive) {
            Bitmap descendants;
            for (const auto& child:node->children) descendants|=child.second->inclusive;
            result-=descendants;
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
            query_work_.directories_visited+=query_work_.direct_children;
            query_work_.bitmaps_read+=query_work_.direct_children;
            query_work_.bitmap_unions=query_work_.direct_children;
            query_work_.bitmap_differences=1;
#endif
        }
        return {true,std::move(result)};
    }
    void move(const std::string& source,const std::string& destination) override {
        DIR_CORE(directory)
        work_={};
        auto& s=required(source); auto& d=required(destination);
        if (&s==root_.get() || at_or_below(destination,source))
            throw Error(ErrorCode::invalid_move,"Move would relocate root or form a cycle");
        if (s.parent==&d) { work_={}; return; }
        if (d.children.count(s.segment)) throw Error(ErrorCode::name_conflict,"Move destination name exists");
        auto old_anc=proper_ancestors(&s), new_anc=proper_ancestors(&d);
        new_anc.insert(&d);
        Bitmap ids=s.inclusive;
        work_={};
        auto handle=s.parent->children.extract(s.segment);
        auto moved=std::move(handle.mapped());
        moved->parent=&d;
        const auto name=moved->segment;
        d.children.emplace(name,std::move(moved));
        ++work_.relinked_subtrees;
        update_ancestors(old_anc,new_anc,ids);
    }
    void merge(const std::string& source,const std::string& target) override {
        DIR_CORE(directory)
        work_={};
        auto& s=required(source); auto& d=required(target);
        if (at_or_below(source,target) || at_or_below(target,source))
            throw Error(ErrorCode::invalid_merge,"Merge roots must be disjoint");
        auto old_anc=proper_ancestors(&s),new_anc=proper_ancestors(&d);
        Bitmap ids=s.inclusive;
        work_={};
        auto handle=s.parent->children.extract(s.segment);
        reconcile(std::move(handle.mapped()),d);
        update_ancestors(old_anc,new_anc,ids);
    }
    std::vector<std::string> directories() const override {
        std::vector<std::string> result;
        std::function<void(const TrieNode*)> visit=[&](const TrieNode* node) {
            result.push_back(path_of(node));
            for (const auto& child:node->children) visit(child.second.get());
        };
        visit(root_.get()); std::sort(result.begin(),result.end()); return result;
    }
    std::map<Id,std::string> bindings() const override {
        std::map<Id,std::string> result;
        for (const auto& entry:catalog_.entries()) result.emplace(entry.first,path_of(static_cast<TrieNode*>(entry.second)));
        return result;
    }
    std::uint64_t identity(const std::string& path) const override { return required(path).uid; }
    MaintenanceWork last_maintenance_work() const override { return work_; }
    QueryWork last_query_work() const override {
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
        return query_work_;
#else
        return {};
#endif
    }
    IndexStatistics statistics() const override {
        IndexStatistics result;
        result.catalog_entry_count=catalog_.size();
        std::function<void(const TrieNode*)> visit=[&](const TrieNode* node) {
            ++result.directory_count;
            ++result.bitmap_count;
            result.roaring_portable_bytes+=node->inclusive.portable_size();
            for (const auto& child:node->children) visit(child.second.get());
        };
        visit(root_.get());
        return result;
    }
    std::vector<std::string> validate() const override {
        std::vector<std::string> errors;
        std::set<Token*> active;
        std::vector<TrieNode*> nodes;
        std::function<void(TrieNode*)> visit=[&](TrieNode* node) {
            if (!active.insert(node).second) { errors.push_back("cycle or duplicate node"); return; }
            nodes.push_back(node);
            for (const auto& child:node->children) {
                if (!child.second || child.second->parent!=node || child.second->segment!=child.first)
                    errors.push_back("parent/child binding mismatch");
                else visit(child.second.get());
            }
        };
        if (root_->parent || !root_->segment.empty()) errors.push_back("invalid root");
        visit(root_.get());
        std::map<TrieNode*,Bitmap> expected;
        for (auto* node:nodes) expected[node];
        for (const auto& entry:catalog_.entries()) {
            if (!active.count(entry.second)) { errors.push_back("dangling catalog directory"); continue; }
            for (auto* p=static_cast<TrieNode*>(entry.second);p;p=p->parent) expected[p].add(entry.first);
        }
        for (auto* node:nodes) if (node->inclusive!=expected.at(node)) errors.push_back("inclusive invariant failed");
        return errors;
    }
};
} // namespace
std::unique_ptr<Index> make_index(Strategy strategy) {
    DIR_CORE(directory)
    switch (strategy) {
        case Strategy::pe_online: return std::make_unique<FlatIndex>(false);
        case Strategy::pe_offline: return std::make_unique<FlatIndex>(true);
        case Strategy::trie_hi: return std::make_unique<TrieIndex>();
    }
    throw std::invalid_argument("Unknown strategy");
}
} // namespace directory
