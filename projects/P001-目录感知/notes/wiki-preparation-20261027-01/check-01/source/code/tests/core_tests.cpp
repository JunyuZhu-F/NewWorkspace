#include "directory/index.hpp"
#include "oracle.hpp"
#include <algorithm>
#include <array>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <random>
#include <set>
#include <sstream>
#include <string>

using namespace directory;
static std::uint64_t assertions=0, operations=0, scope_checks=0;
static std::string context;
static void require(bool condition,const std::string& message) {
    ++assertions;
    if (!condition) throw std::runtime_error(context+": "+message);
}
static std::set<Id> ids(const Bitmap& bitmap) {
    auto values=bitmap.values(); return {values.begin(),values.end()};
}
static int outcome(const std::function<void()>& function) {
    try { function(); return 0; }
    catch (const Error& error) { return static_cast<int>(error.code)+1; }
}
struct Harness {
    Oracle oracle;
    std::array<std::unique_ptr<Index>,3> indexes{
        make_index(Strategy::pe_online),make_index(Strategy::pe_offline),make_index(Strategy::trie_hi)};
    void check() {
        auto expected_dirs=oracle.directories();
        for (const auto& index:indexes) {
            auto errors=index->validate();
            require(errors.empty(),index->name()+" validation: "+(errors.empty()?"":errors.front()));
            require(index->directories()==expected_dirs,index->name()+" directory namespace mismatch");
            require(index->bindings()==oracle.bindings(),index->name()+" catalog mismatch");
            for (const auto& path:expected_dirs) for (bool recursive:{false,true}) {
                auto expected=oracle.query(path,recursive);
                auto actual=index->query(path,recursive);
                ++scope_checks;
                require(actual.exists==expected.exists && ids(actual.ids)==expected.ids,index->name()+" scope mismatch at "+path);
            }
            auto absent=index->query("/__missing__/",true);
            require(!absent.exists && absent.ids.cardinality()==0,index->name()+" nonexistent directory query");
        }
    }
    template<class Function> void apply(const std::string& label,Function function,bool validate=true) {
        context=label;
        auto old_dirs=oracle.directories(); auto old_bindings=oracle.bindings();
        auto expected=outcome([&]{function(oracle);});
        if (expected) require(oracle.directories()==old_dirs && oracle.bindings()==old_bindings,"Oracle rejected mutation changed state");
        for (auto& index:indexes) {
            auto before_dirs=index->directories(); auto before_bindings=index->bindings();
            int actual=outcome([&]{function(*index);});
            require(actual==expected,index->name()+" success/error-code disagreement");
            if (actual) require(index->directories()==before_dirs && index->bindings()==before_bindings,index->name()+" rejected mutation changed state");
        }
        ++operations;
        if (validate) check();
    }
    void expect(const std::string& path,bool recursive,std::set<Id> expected,bool exists=true) {
        auto independent=oracle.query(path,recursive);
        require(independent.exists==exists && independent.ids==expected,"Oracle disagrees with manual expected IDs");
        for (const auto& index:indexes) {
            auto actual=index->query(path,recursive);
            require(actual.exists==exists && ids(actual.ids)==expected,index->name()+" manual expected IDs mismatch: "+path);
        }
    }
};
static void figure(Harness& h) {
    const std::array<std::pair<Id,std::string>,9> entries{{
        {1,"/HR/"},{2,"/HR/Policies/"},{3,"/Finance/"},{4,"/Legal/"},{5,"/Dept_A/"},
        {6,"/Dept_B/"},{7,"/Archive/HR/"},{8,"/Dept_A/OKR/"},{9,"/Dept_B/OKR/"}}};
    for (const auto& item:entries) h.apply("figure insert",[&](auto& index){index.insert(item.first,item.second);});
    h.expect("/",false,{}); h.expect("/",true,{1,2,3,4,5,6,7,8,9});
    h.expect("/HR/",false,{1}); h.expect("/HR/",true,{1,2});
    h.expect("/HR/Policies/",true,{2}); h.expect("/Finance/",false,{3});
    h.expect("/Legal/",false,{4}); h.expect("/Dept_A/",false,{5}); h.expect("/Dept_A/",true,{5,8});
    h.expect("/Dept_B/",false,{6}); h.expect("/Dept_B/",true,{6,9});
    h.expect("/Dept_A/OKR/",false,{8}); h.expect("/Dept_B/OKR/",false,{9});
    h.expect("/Archive/",false,{}); h.expect("/Archive/",true,{7}); h.expect("/Archive/HR/",false,{7});
}
static void fixed_tests() {
    {
        Harness h; figure(h);
        auto root_id=h.indexes[2]->identity("/Dept_A/"); auto child_id=h.indexes[2]->identity("/Dept_A/OKR/");
        h.apply("figure MOVE",[](auto& index){index.move("/Dept_A/","/Dept_B/");});
        h.expect("/Dept_A/",true,{},false); h.expect("/Dept_B/",true,{5,6,8,9});
        h.expect("/Dept_B/Dept_A/",false,{5}); h.expect("/Dept_B/Dept_A/OKR/",false,{8});
        h.expect("/Dept_B/OKR/",false,{9}); h.expect("/",true,{1,2,3,4,5,6,7,8,9});
        require(h.indexes[2]->identity("/Dept_B/Dept_A/")==root_id,"Trie MOVE root identity");
        require(h.indexes[2]->identity("/Dept_B/Dept_A/OKR/")==child_id,"Trie MOVE descendant identity");
        require(h.indexes[2]->last_maintenance_work().remapped_path_keys==0,"Trie MOVE must not remap descendant path keys");
        require(h.indexes[2]->last_maintenance_work().relinked_subtrees==1,"Trie MOVE one relink");
        for (int i=0;i<2;++i) require(h.indexes[i]->last_maintenance_work().remapped_path_keys==2,"PE MOVE remaps two source keys");
    }
    {
        Harness h; figure(h);
        auto target_id=h.indexes[2]->identity("/Dept_B/OKR/");
        h.apply("figure MERGE",[](auto& index){index.merge("/Dept_A/","/Dept_B/");});
        h.expect("/Dept_A/",true,{},false); h.expect("/Dept_B/",false,{5,6});
        h.expect("/Dept_B/OKR/",false,{8,9}); h.expect("/Dept_B/",true,{5,6,8,9});
        require(h.indexes[2]->identity("/Dept_B/OKR/")==target_id,"conflict target identity preserved");
        require(h.indexes[2]->last_maintenance_work().reconciled_nodes==2,"Trie reconciles root and conflicting OKR only");
    }
    {
        Harness h;
        for (auto [id,path]:std::vector<std::pair<Id,std::string>>{{0,"/"},{1,"/s/"},{2,"/d/"},{3,"/s/solo/deep/"},{4,"/s/c/x/"},{5,"/d/c/x/"},{6,"/s/c/"},{7,"/d/c/"}})
            h.apply("nested insert",[&](auto& index){index.insert(id,path);});
        h.apply("empty subtree",[](auto& index){index.mkdir("/s/empty/deeper/");});
        auto identity=h.indexes[2]->identity("/s/solo/deep/");
        h.apply("nested MERGE",[](auto& index){index.merge("/s/","/d/");});
        h.expect("/d/",false,{1,2}); h.expect("/d/c/",false,{6,7});
        h.expect("/d/c/x/",false,{4,5}); h.expect("/d/solo/deep/",false,{3});
        h.expect("/d/empty/deeper/",true,{}); h.expect("/",false,{0});
        require(h.indexes[2]->identity("/d/solo/deep/")==identity,"nonconflicting subtree retains descendant identity");
    }
    {
        Harness h;
        for (auto [id,path]:std::vector<std::pair<Id,std::string>>{{0,"/"},{65535,"/a/"},{65536,"/a/b/"},{std::numeric_limits<Id>::max(),"/ab/"},{123,"/A/"},{124,u8"/\u76ee\u5f55/"}})
            h.apply("boundary ID/path insert",[&](auto& index){index.insert(id,path);});
        h.expect("/a/",true,{65535,65536}); h.expect("/ab/",true,{std::numeric_limits<Id>::max()});
        h.expect("/a/",false,{65535}); h.expect("/A/",false,{123});
        h.expect(u8"/\u76ee\u5f55/",false,{124});
        h.apply("empty directory",[](auto& index){index.mkdir("/empty/sub/");});
        h.expect("/empty/sub/",false,{}); h.expect("/absent/",false,{},false);
        std::vector<std::string> invalid{"","a/","/a","//","/a//b/","/./","/a/../",std::string("/a/\0x/",6)};
        for (const auto& path:invalid) {
            h.apply("invalid mkdir",[&](auto& index){index.mkdir(path);});
            h.apply("invalid insert",[&](auto& index){index.insert(1000,path);});
            int expected=outcome([&]{h.oracle.query(path,true);});
            require(expected==static_cast<int>(ErrorCode::invalid_path)+1,"Oracle must reject malformed query");
            for (const auto& index:h.indexes) require(outcome([&]{index->query(path,true);})==expected,"query validation mismatch");
        }
        h.apply("duplicate insert must not create path",[](auto& index){index.insert(0,"/new/not-created/");});
        h.expect("/new/",true,{},false);
        h.apply("root MOVE reject",[](auto& index){index.move("/","/a/");});
        h.apply("cycle MOVE reject",[](auto& index){index.move("/a/","/a/b/");});
        h.apply("self MOVE reject",[](auto& index){index.move("/a/","/a/");});
        h.apply("missing source reject",[](auto& index){index.move("/none/","/a/");});
        h.apply("missing destination reject",[](auto& index){index.move("/a/","/none/");});
        h.apply("same parent no-op",[](auto& index){index.move("/a/","/");});
        h.apply("overlap MERGE reject",[](auto& index){index.merge("/a/","/a/b/");});
        h.apply("ancestor MERGE reject",[](auto& index){index.merge("/a/b/","/a/");});
        h.apply("self MERGE reject",[](auto& index){index.merge("/a/","/a/");});
        h.apply("root MERGE reject",[](auto& index){index.merge("/","/a/");});
        h.apply("collision target mkdir",[](auto& index){index.mkdir("/destination/a/");});
        h.apply("name conflict MOVE reject",[](auto& index){index.move("/a/","/destination/");});
        // Copies returned from a query must remain independent of later changes.
        std::vector<Bitmap> snapshots;
        for (const auto& index:h.indexes) snapshots.push_back(index->query("/",true).ids);
        auto old=h.oracle.query("/",true).ids;
        h.apply("insert after query snapshot",[](auto& index){index.insert(777,"/a/");});
        for (const auto& snapshot:snapshots) require(ids(snapshot)==old,"query bitmap changed after mutation");
        h.apply("empty source MERGE",[](auto& index){index.merge("/empty/","/destination/");});
    }
    {
        Harness h;
        for (auto [id,path]:std::vector<std::pair<Id,std::string>>{{1,"/base/a/"},{2,"/base/a/x/"},{3,"/base/b/"}})
            h.apply("shared ancestor insert",[&](auto& index){index.insert(id,path);});
        h.apply("shared ancestor MOVE",[](auto& index){index.move("/base/a/","/base/b/");});
        h.expect("/base/",true,{1,2,3}); h.expect("/base/b/a/",true,{1,2});
        h.apply("shared ancestor MERGE",[](auto& index){index.merge("/base/b/a/","/base/b/a/x/");}); // rejected
        h.apply("empty target mkdir",[](auto& index){index.mkdir("/base/target/");});
        h.apply("shared ancestor legal MERGE",[](auto& index){index.merge("/base/b/a/","/base/target/");});
        h.expect("/base/",true,{1,2,3}); h.expect("/base/target/",true,{1,2});
    }
}
static void bitmap_test() {
    Bitmap a; for (Id id:{0u,65535u,65536u,std::numeric_limits<Id>::max()}) a.add(id);
    require(a.cardinality()==4,"Roaring boundary IDs");
    Bitmap b=a; b.remove(65535); require(a.contains(65535) && !b.contains(65535),"bitmap copy ownership");
    Bitmap c; c.add(42); c|=b; require(c.cardinality()==4,"bitmap union");
    c-=b; require(ids(c)==std::set<Id>{42},"bitmap difference");
    a|=a; require(a.cardinality()==4,"bitmap self union");
    a-=a; require(a.cardinality()==0,"bitmap self difference");
    Bitmap moved=std::move(b); require(moved.cardinality()==3 && b.cardinality()==0,"bitmap move ownership");
    b.add(99); require(b.contains(99) && !moved.contains(99),"moved-from bitmap reuse");
    Bitmap empty_copy=b; b=std::move(b); require(b==empty_copy,"bitmap self move assignment");
}
static void random_test(std::uint32_t seed,unsigned steps) {
    Harness h; std::mt19937 rng(seed); Id next_id=0;
    for (unsigned step=0;step<steps;++step) {
        auto dirs=h.oracle.directories(); auto pick=[&](){return dirs[rng()%dirs.size()];};
        auto kind=rng()%5;
        auto label="seed="+std::to_string(seed)+" step="+std::to_string(step);
        if (kind==0) {
            auto path=pick(); if (dirs.size()<64) path+="n"+std::to_string(rng()%8)+"/";
            h.apply(label+" mkdir "+path,[&](auto& index){index.mkdir(path);});
        } else if (kind==1) {
            auto path=pick(); if (dirs.size()<64 && rng()%3==0) path+="n"+std::to_string(rng()%8)+"/";
            Id id=next_id<256 ? next_id++ : rng()%256;
            if (next_id>1 && rng()%5==0) id=rng()%next_id;
            h.apply(label+" insert",[&](auto& index){index.insert(id,path);});
        } else if (kind==2) {
            auto s=pick(),d=pick();
            h.apply(label+" MOVE "+s+" -> "+d,[&](auto& index){index.move(s,d);});
        } else if (kind==3) {
            auto s=pick(),d=pick();
            h.apply(label+" MERGE "+s+" -> "+d,[&](auto& index){index.merge(s,d);});
        } else { context=label+" query"; h.check(); }
    }
}
static void pilot_test(const std::string& filename) {
    Harness h; std::ifstream input(filename); require(input.good(),"open time-pilot TSV");
    std::string line; std::size_t count=0;
    while (std::getline(input,line)) {
        if (!line.empty() && line.back()=='\r') line.pop_back();
        auto tab=line.find('\t'); require(tab!=std::string::npos,"pilot TSV delimiter");
        auto value=std::stoull(line.substr(0,tab)); require(value<=std::numeric_limits<Id>::max(),"pilot ID range");
        auto path=line.substr(tab+1); auto id=static_cast<Id>(value);
        h.oracle.insert(id,path); for (auto& index:h.indexes) index->insert(id,path); ++count;
    }
    require(count==10000,"fixed time-pilot size"); context="time-pilot initial";h.check();
    h.apply("time pilot MOVE",[](auto& index){index.move("/1992/1/","/1991/");});
    h.apply("time pilot MERGE",[](auto& index){index.merge("/1992/7/","/1991/7/");});
    h.apply("time pilot collision rejection",[](auto& index){index.move("/1992/8/","/1991/");});
}
int main(int argc,char** argv) {
    try {
        if (argc<2) throw std::runtime_error("usage: bitmap | fixed | random seed steps | pilot bindings.tsv");
        std::string mode=argv[1]; context=mode;
        if (mode=="bitmap") bitmap_test();
        else if (mode=="fixed") fixed_tests();
        else if (mode=="random" && argc==4) random_test(static_cast<std::uint32_t>(std::stoul(argv[2])),static_cast<unsigned>(std::stoul(argv[3])));
        else if (mode=="pilot" && argc==3) pilot_test(argv[2]);
        else throw std::runtime_error("invalid test arguments");
        std::cout<<"{\"status\":\"pass\",\"mode\":\""<<mode<<"\",\"logical_mutations\":"<<operations<<",\"scope_comparisons\":"<<scope_checks<<",\"checks\":"<<assertions<<"}\n";
        return 0;
    } catch (const std::exception& error) { std::cerr<<"FAIL: "<<error.what()<<"\n"; return 1; }
}
