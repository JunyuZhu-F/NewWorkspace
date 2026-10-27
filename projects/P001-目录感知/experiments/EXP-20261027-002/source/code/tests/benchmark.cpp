#include "directory/index.hpp"
#include "oracle.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#endif

namespace {
using directory::Bitmap; using directory::Id; using directory::Index; using directory::Strategy;
using Clock=std::chrono::steady_clock;
constexpr std::uint64_t LIMIT_BYTES=2ull*1024*1024*1024;
struct Binding { Id id; std::string path; };
struct ExpectedQuery { std::string path; bool recursive; std::size_t count; std::string digest; };
struct Operation { std::string kind,a,b; bool accepted; };
struct Fixture {
    std::string name; std::vector<Binding> rows; std::vector<ExpectedQuery> queries;
    std::vector<Operation> operations; std::vector<std::string> paths;
};
struct ProcessMemory { std::uint64_t working=0,private_bytes=0,peak=0,available=0; bool available_api=false; };
void require(bool ok,const std::string& message) { if(!ok) throw std::runtime_error(message); }
std::string escape(const std::string& s) {
    std::ostringstream out; out<<'"';
    for(unsigned char c:s) {
        if(c=='"'||c=='\\') out<<'\\'<<char(c);
        else if(c=='\n') out<<"\\n"; else if(c=='\r') out<<"\\r"; else if(c=='\t') out<<"\\t";
        else if(c<0x20) out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;
        else out<<char(c);
    }
    out<<'"'; return out.str();
}
std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> result; std::size_t start=0;
    while(true) { auto end=line.find('\t',start); result.push_back(line.substr(start,end-start)); if(end==std::string::npos) break; start=end+1; }
    return result;
}
std::vector<std::string> lines(const std::string& path) {
    std::ifstream in(path,std::ios::binary); require(in.good(),"Cannot open fixture: "+path);
    std::vector<std::string> result; std::string line;
    while(std::getline(in,line)) { if(!line.empty()&&line.back()=='\r') line.pop_back(); if(!line.empty()) result.push_back(line); }
    require(in.eof(),"Failed reading fixture: "+path); return result;
}
Fixture load_fixture(const std::string& dir,const std::string& name,const std::string& base) {
    Fixture f; f.name=name;
    for(const auto& line:lines(dir+"/"+base+"-bindings.tsv")) {
        auto p=split(line); require(p.size()==2,"Invalid binding row"); f.rows.push_back({static_cast<Id>(std::stoul(p[0])),p[1]});
    }
    std::set<std::string> paths;
    for(const auto& line:lines(dir+"/"+base+"-queries.tsv")) {
        auto p=split(line); require(p.size()==4,"Invalid query row");
        f.queries.push_back({p[0],p[1]=="1",static_cast<std::size_t>(std::stoull(p[2])),p[3]}); paths.insert(p[0]);
    }
    f.paths.assign(paths.begin(),paths.end());
    std::sort(f.paths.begin(),f.paths.end(),[](const auto& a,const auto& b){ if(a=="/") return true; if(b=="/") return false; return a<b; });
    for(const auto& line:lines(dir+"/"+name+"-operations.tsv")) {
        auto p=split(line); require(p.size()==4,"Invalid operation row"); f.operations.push_back({p[0],p[1],p[2],p[3]=="1"});
    }
    require(!f.rows.empty()&&!f.queries.empty()&&!f.operations.empty(),"Incomplete fixture"); return f;
}
Strategy strategy(const std::string& name) {
    if(name=="pe_online") return Strategy::pe_online; if(name=="pe_offline") return Strategy::pe_offline; if(name=="trie_hi") return Strategy::trie_hi;
    throw std::invalid_argument("Unknown strategy: "+name);
}
std::string digest(const std::vector<std::uint32_t>& ids) {
    std::uint64_t value=0xcbf29ce484222325ull;
    for(auto id:ids) for(int i=0;i<4;++i) { value^=(id>>(8*i))&0xffu; value*=0x100000001b3ull; }
    std::ostringstream out; out<<std::hex<<std::setw(16)<<std::setfill('0')<<value; return out.str();
}
std::set<Id> ids(const Bitmap& bitmap) { auto v=bitmap.values(); return {v.begin(),v.end()}; }
void compare_result(const Index& index,const Oracle& oracle,const std::string& path,bool recursive) {
    auto actual=index.query(path,recursive); auto expected=oracle.query(path,recursive);
    require(actual.exists==expected.exists,"Existence mismatch: "+path);
    require(ids(actual.ids)==expected.ids,"ID set mismatch: "+path);
}
void check_state(const Index& index,const Oracle& oracle,const Fixture& f,bool initial) {
    require(index.validate().empty(),"Index invariant failed"); require(index.bindings()==oracle.bindings(),"Catalog/binding mismatch");
    auto actual_dirs=index.directories(); auto expected_dirs=oracle.directories();
    std::sort(actual_dirs.begin(),actual_dirs.end()); std::sort(expected_dirs.begin(),expected_dirs.end());
    require(actual_dirs==expected_dirs,"Directory topology mismatch");
    for(const auto& path:expected_dirs) for(bool recursive:{true,false}) {
        compare_result(index,oracle,path,recursive);
        if(initial) {
            auto it=std::find_if(f.queries.begin(),f.queries.end(),[&](const auto& q){return q.path==path&&q.recursive==recursive;});
            require(it!=f.queries.end(),"Frozen query expectation missing");
            auto result=index.query(path,recursive); auto values=result.ids.values();
            require(values.size()==it->count&&digest(values)==it->digest,"Frozen query cardinality/digest mismatch");
        }
    }
    auto stats=index.statistics();
    require(stats.directory_count==expected_dirs.size(),"Directory statistics mismatch");
    require(stats.catalog_entry_count==oracle.bindings().size(),"Catalog statistics mismatch");
    require(stats.bitmap_count==expected_dirs.size(),"Bitmap statistics mismatch");
}
Oracle make_oracle(const Fixture& f) { Oracle oracle; for(const auto& row:f.rows) oracle.insert(row.id,row.path); return oracle; }
std::unique_ptr<Index> build_index(Strategy s,const Fixture& f) {
    auto index=directory::make_index(s); for(const auto& row:f.rows) index->insert(row.id,row.path); return index;
}
void check_counters(const Index& index,bool instrumented,std::size_t directory_count) {
    const auto w=index.last_query_work(); bool zero=!w.path_segments&&!w.directories_visited&&!w.direct_children&&!w.bitmaps_read&&!w.bitmap_copies&&!w.bitmap_unions&&!w.bitmap_differences;
    if(instrumented && index.name()=="PE-ONLINE") require(w.path_segments==0&&w.directories_visited==directory_count&&w.bitmaps_read==directory_count&&w.bitmap_copies==0&&w.bitmap_unions==directory_count,"Instrumented online recursive-root counters invalid");
    else if(instrumented) require(w.path_segments==0&&w.directories_visited==1&&w.bitmaps_read==1&&w.bitmap_copies==1,"Instrumented recursive-root counters invalid");
    else require(zero,"Default core must not expose diagnostic counters");
}
void apply_checked(Index& index,Oracle& oracle,const Fixture& f,const Operation& op) {
    auto before_bindings=index.bindings(); auto before_dirs=index.directories();
    if(op.accepted) {
        if(op.kind=="move") { index.move(op.a,op.b); oracle.move(op.a,op.b); }
        else { require(op.kind=="merge","Unknown operation"); index.merge(op.a,op.b); oracle.merge(op.a,op.b); }
    } else {
        bool rejected=false; try { if(op.kind=="move") index.move(op.a,op.b); else index.merge(op.a,op.b); } catch(const directory::Error&) { rejected=true; }
        require(rejected,"Expected rejected operation was accepted"); require(index.bindings()==before_bindings&&index.directories()==before_dirs,"Rejected operation changed state");
    }
    check_state(index,oracle,f,false);
    if(f.name=="time-dsm"||f.name=="time") {
        if(op.a=="/1992/1/") { require(oracle.query("/1991/",true).ids.size()==499&&oracle.query("/1992/",true).ids.size()==3068,"Time MOVE anchor mismatch"); }
        if(op.kind=="merge"&&op.a=="/1992/7/") { require(oracle.query("/1991/7/",true).ids.size()==298&&oracle.query("/1991/",true).ids.size()==795&&oracle.query("/1992/",true).ids.size()==2772&&index.directories().size()==33,"Time MERGE anchor mismatch"); }
    }
}
void self_test(const std::string& dir,bool instrumented) {
    for(auto s:{Strategy::pe_online,Strategy::pe_offline,Strategy::trie_hi}) {
        for(const auto& name:{"figure2","time"}) {
            auto f=load_fixture(dir,name,name); auto oracle=make_oracle(f); auto index=build_index(s,f); check_state(*index,oracle,f,true);
            auto root=index->query("/",true); require(root.ids.cardinality()==f.rows.size(),"Root cardinality mismatch"); check_counters(*index,instrumented,f.paths.size());
            auto local=index->query("/",false); const auto w=index->last_query_work();
            const auto children=static_cast<std::size_t>(std::count_if(f.paths.begin(),f.paths.end(),[](const auto& path){return path!="/"&&std::count(path.begin(),path.end(),'/')==2;}));
            if(instrumented&&index->name()=="PE-ONLINE") require(w.directories_visited==1&&w.bitmaps_read==1&&w.bitmap_copies==1&&w.bitmap_unions==0&&w.bitmap_differences==0,"Online local counters invalid");
            if(instrumented&&index->name()!="PE-ONLINE") require(w.directories_visited==children+1&&w.bitmaps_read==children+1&&w.bitmap_copies==1&&w.bitmap_unions==children&&w.bitmap_differences==1,"Subtree-difference local counters invalid");
            require(index->statistics().roaring_portable_bytes>0,"Portable bitmap size missing");
        }
        for(const auto& name:{"figure2-move","figure2-merge","time-dsm"}) {
            auto f=load_fixture(dir,name,std::string(name)=="time-dsm"?"time":"figure2"); auto oracle=make_oracle(f); auto index=build_index(s,f);
            for(const auto& op:f.operations) apply_checked(*index,oracle,f,op);
        }
    }
}
ProcessMemory memory() {
    ProcessMemory result;
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS_EX counters{}; counters.cb=sizeof(counters);
    if(GetProcessMemoryInfo(GetCurrentProcess(),reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&counters),sizeof(counters))) {
        result.working=counters.WorkingSetSize; result.private_bytes=counters.PrivateUsage; result.peak=counters.PeakWorkingSetSize; result.available_api=true;
    }
    MEMORYSTATUSEX status{}; status.dwLength=sizeof(status);
    if(GlobalMemoryStatusEx(&status)) result.available=status.ullAvailPhys;
#endif
    return result;
}
void check_resources() { auto m=memory(); require(!m.available_api||(m.private_bytes<LIMIT_BYTES&&m.available>=LIMIT_BYTES),"Resource stop limit reached"); }
std::uint64_t epoch_ms() { return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count()); }
void append(const std::string& path,const std::string& line) { std::ofstream out(path,std::ios::app|std::ios::binary); require(out.good(),"Cannot open output: "+path); out<<line<<'\n'; out.flush(); require(out.good(),"Cannot write output: "+path); }
struct Context {
    std::string experiment,code_hash,input_hash,strategy_name,input,subload,output; int run=0; bool instrumented=false;
    std::string common() const {
        return "\"protocol\":\"PROTO-01-20261026\",\"experiment\":"+escape(experiment)+",\"timestamp_epoch_ms\":"+std::to_string(epoch_ms())+
          ",\"strategy\":"+escape(strategy_name)+",\"input\":"+escape(input)+",\"subload\":"+escape(subload)+",\"source_hash\":"+escape(code_hash)+",\"input_hash\":"+escape(input_hash)+
          ",\"run\":"+std::to_string(run)+",\"instrumented\":"+(instrumented?"true":"false");
    }
};
std::string work_json(const directory::MaintenanceWork& w) {
    return "\"remapped_path_keys\":"+std::to_string(w.remapped_path_keys)+",\"relinked_subtrees\":"+std::to_string(w.relinked_subtrees)+",\"reconciled_nodes\":"+std::to_string(w.reconciled_nodes)+",\"catalog_entries_scanned\":"+std::to_string(w.catalog_entries_scanned);
}
std::string query_work_json(const directory::QueryWork& w,bool enabled) {
    if(!enabled) return "\"work_counters_status\":\"not_collected_in_default_core\"";
    return "\"work_counters_status\":\"collected\",\"path_segments\":"+std::to_string(w.path_segments)+",\"directories_visited\":"+std::to_string(w.directories_visited)+",\"work_direct_children\":"+std::to_string(w.direct_children)+",\"bitmaps_read\":"+std::to_string(w.bitmaps_read)+",\"bitmap_copies\":"+std::to_string(w.bitmap_copies)+",\"bitmap_unions\":"+std::to_string(w.bitmap_unions)+",\"bitmap_differences\":"+std::to_string(w.bitmap_differences);
}
void timing_overhead(const Context& c) {
    std::vector<std::uint64_t> values; values.reserve(10000);
    for(int i=0;i<10000;++i) { auto a=Clock::now(); auto b=Clock::now(); values.push_back(static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count())); }
    std::sort(values.begin(),values.end()); auto q=[&](double p){return values[std::max<std::size_t>(1,static_cast<std::size_t>(std::ceil(p*values.size())))-1];};
    double mean=std::accumulate(values.begin(),values.end(),0.0)/values.size();
    double resolution=static_cast<double>(Clock::period::num)*1e9/Clock::period::den;
    append(c.output+"/raw/timing.jsonl","{"+c.common()+",\"clock_is_steady\":"+(Clock::is_steady?"true":"false")+",\"clock_resolution_ns\":"+std::to_string(resolution)+",\"empty_interval_n\":10000,\"empty_interval_mean_ns\":"+std::to_string(mean)+",\"empty_interval_p90_ns\":"+std::to_string(q(.9))+",\"empty_interval_p95_ns\":"+std::to_string(q(.95))+",\"empty_interval_p99_ns\":"+std::to_string(q(.99))+",\"empty_interval_p999_ns\":"+std::to_string(q(.999))+"}");
}
void space(const Context& c,const Index& index,int iteration,bool warmup) {
    auto s=index.statistics(); auto m=memory();
    append(c.output+"/raw/space.jsonl","{"+c.common()+",\"iteration\":"+std::to_string(iteration)+",\"warmup\":"+(warmup?"true":"false")+
      ",\"directory_count\":"+std::to_string(s.directory_count)+",\"catalog_entry_count\":"+std::to_string(s.catalog_entry_count)+",\"bitmap_count\":"+std::to_string(s.bitmap_count)+",\"roaring_portable_bytes\":"+std::to_string(s.roaring_portable_bytes)+
      ",\"vector_bytes\":0,\"vector_loaded\":false,\"memory_api\":\"GetProcessMemoryInfo/GlobalMemoryStatusEx\",\"working_set_bytes\":"+std::to_string(m.working)+",\"private_bytes\":"+std::to_string(m.private_bytes)+",\"peak_working_set_bytes\":"+std::to_string(m.peak)+",\"system_available_physical_bytes\":"+std::to_string(m.available)+"}");
}
std::size_t depth(const std::string& path) { return path=="/"?0:static_cast<std::size_t>(std::count(path.begin(),path.end(),'/')-1); }
bool inside(const std::string& path,const std::string& root) { return root=="/"||path.compare(0,root.size(),root)==0; }
std::string parent(std::string path) { path.pop_back(); return path.substr(0,path.rfind('/')+1); }
std::size_t direct_children(const Oracle& oracle,const std::string& path) { std::size_t n=0; for(const auto& p:oracle.directories()) if(p!=path&&inside(p,path)&&parent(p)==path) ++n; return n; }
std::size_t conflict_count(const Oracle& oracle,const Operation& op) {
    if(op.kind=="move") { auto stem=op.a.substr(0,op.a.size()-1); auto name=stem.substr(stem.rfind('/')+1); auto dest=op.b+name+"/"; auto dirs=oracle.directories(); return std::find(dirs.begin(),dirs.end(),dest)!=dirs.end()?1:0; }
    std::size_t n=0; auto dirs=oracle.directories(); std::set<std::string> existing(dirs.begin(),dirs.end());
    for(const auto& p:dirs) if(inside(p,op.a)&&existing.count(op.b+p.substr(op.a.size()))) ++n; return n;
}
void run(const Context& c,const Fixture& f,Strategy s) {
    auto process_start=Clock::now(); timing_overhead(c); std::size_t correctness_checks=0;
    if(c.subload=="build") {
        for(int iteration=0;iteration<23;++iteration) {
            check_resources(); auto begin=Clock::now(); auto index=directory::make_index(s); for(const auto& row:f.rows) index->insert(row.id,row.path); auto end=Clock::now();
            auto oracle=make_oracle(f); check_state(*index,oracle,f,true); ++correctness_checks;
            append(c.output+"/raw/build.jsonl","{"+c.common()+",\"iteration\":"+std::to_string(iteration)+",\"warmup\":"+(iteration<3?"true":"false")+",\"entry_count\":"+std::to_string(f.rows.size())+",\"input_order_sha256\":"+escape(c.input_hash)+",\"directory_count\":"+std::to_string(index->directories().size())+",\"build_ns\":"+std::to_string(std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count())+"}");
            space(c,*index,iteration,iteration<3);
        }
    } else if(c.subload=="dsq") {
        auto oracle=make_oracle(f); auto index=build_index(s,f); check_state(*index,oracle,f,true); ++correctness_checks;
        std::map<std::pair<std::string,bool>,std::set<Id>> independent;
        for(const auto& q:f.queries) independent[{q.path,q.recursive}]=oracle.query(q.path,q.recursive).ids;
        for(int iteration=0;iteration<23;++iteration) {
            check_resources();
            for(const auto& expected:f.queries) {
                auto begin=Clock::now(); directory::QueryResult result=index->query(expected.path,expected.recursive); auto end=Clock::now();
                auto values=result.ids.values(); require(values.size()==expected.count&&digest(values)==expected.digest,"Measured query digest mismatch");
                require(ids(result.ids)==independent.at({expected.path,expected.recursive}),"Measured query oracle mismatch"); ++correctness_checks;
                append(c.output+"/raw/dsq.jsonl","{"+c.common()+",\"iteration\":"+std::to_string(iteration)+",\"sweep\":"+std::to_string(iteration)+",\"warmup\":"+(iteration<3?"true":"false")+",\"path\":"+escape(expected.path)+",\"recursive\":"+(expected.recursive?"true":"false")+",\"depth\":"+std::to_string(depth(expected.path))+",\"direct_children\":"+std::to_string(direct_children(oracle,expected.path))+",\"candidate_count\":"+std::to_string(values.size())+",\"result_digest\":"+escape(digest(values))+",\"total_ns\":"+std::to_string(std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count())+",\"stage_timing_status\":\"not_collected\","+query_work_json(index->last_query_work(),c.instrumented)+"}");
            }
        }
    } else {
        for(int iteration=0;iteration<23;++iteration) {
            check_resources(); auto oracle=make_oracle(f); auto index=build_index(s,f); check_state(*index,oracle,f,true); ++correctness_checks;
            for(const auto& op:f.operations) {
                auto source_dirs=oracle.directories(); std::size_t source_subtree_dirs=0; for(const auto& p:source_dirs) if(inside(p,op.a)) ++source_subtree_dirs;
                auto source_entries=oracle.query(op.a,true).ids.size(); auto target_entries=oracle.query(op.b,true).ids.size(); auto conflicts=conflict_count(oracle,op);
                auto begin=Clock::now(); bool accepted=false;
                try { if(op.kind=="move") index->move(op.a,op.b); else index->merge(op.a,op.b); accepted=true; }
                catch(const directory::Error&) { accepted=false; }
                auto end=Clock::now(); require(accepted==op.accepted,"Operation acceptance mismatch");
                if(accepted) { if(op.kind=="move") oracle.move(op.a,op.b); else oracle.merge(op.a,op.b); }
                else require(index->bindings()==oracle.bindings()&&index->directories()==oracle.directories(),"Rejected operation changed state");
                check_state(*index,oracle,f,false); ++correctness_checks;
                if(f.name=="time-dsm") {
                    if(op.a=="/1992/1/") require(oracle.query("/1991/",true).ids.size()==499&&oracle.query("/1992/",true).ids.size()==3068,"Time MOVE anchor mismatch");
                    if(op.kind=="merge") require(oracle.query("/1991/7/",true).ids.size()==298&&oracle.query("/1991/",true).ids.size()==795&&oracle.query("/1992/",true).ids.size()==2772&&index->directories().size()==33,"Time MERGE anchor mismatch");
                }
                append(c.output+"/raw/dsm.jsonl","{"+c.common()+",\"iteration\":"+std::to_string(iteration)+",\"warmup\":"+(iteration<3?"true":"false")+",\"operation\":"+escape(op.kind)+",\"source\":"+escape(op.a)+",\"target_or_new_parent\":"+escape(op.b)+",\"accepted\":"+(accepted?"true":"false")+",\"source_depth\":"+std::to_string(depth(op.a))+",\"target_depth\":"+std::to_string(depth(op.b))+",\"source_subtree_directory_count\":"+std::to_string(source_subtree_dirs)+",\"source_subtree_entry_count\":"+std::to_string(source_entries)+",\"target_entry_count\":"+std::to_string(target_entries)+",\"conflict_node_count\":"+std::to_string(conflicts)+",\"total_ns\":"+std::to_string(std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count())+",\"catalog_cost_status\":\"included_in_total_not_separately_timed\",\"stage_timing_status\":\"not_collected\","+work_json(index->last_maintenance_work())+"}");
            }
        }
    }
    append(c.output+"/raw/process.jsonl","{"+c.common()+",\"status\":\"passed\",\"process_wall_ns\":"+std::to_string(std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-process_start).count())+",\"correctness_checks\":"+std::to_string(correctness_checks)+"}");
}
} // namespace
int main(int argc,char** argv) {
    try {
        require(argc>=3,"Usage: benchmark self-test FIXTURE_DIR | benchmark run --fixture-dir DIR --input figure2|time --subload build|dsq|move|merge|dsm --strategy NAME --output DIR --experiment ID --run N --code-hash HASH");
        std::string mode=argv[1];
#ifdef DIRECTORY_ENABLE_WORK_COUNTERS
        constexpr bool instrumented=true;
#else
        constexpr bool instrumented=false;
#endif
        if(mode=="self-test") { self_test(argv[2],instrumented); std::cout<<"DIR-01 self-test passed; instrumented="<<instrumented<<"\n"; return 0; }
        require(mode=="run","Unknown mode"); std::map<std::string,std::string> args;
        for(int i=2;i<argc;i+=2) { require(i+1<argc,"Missing option value"); args[argv[i]]=argv[i+1]; }
        for(const auto& key:{"--fixture-dir","--input","--subload","--strategy","--output","--experiment","--run","--code-hash","--input-hash"}) require(args.count(key),"Missing option: "+std::string(key));
        Context c{args["--experiment"],args["--code-hash"],args["--input-hash"],args["--strategy"],args["--input"],args["--subload"],args["--output"],std::stoi(args["--run"]),instrumented};
        require(c.run>=0&&c.run<5,"Run must be 0..4"); require(c.input=="figure2"||c.input=="time","Unknown input");
        std::string fixture_name=c.input+"-"+c.subload;
        if(c.input=="figure2"&&(c.subload=="move"||c.subload=="merge")) fixture_name="figure2-"+c.subload;
        else if(c.input=="time"&&c.subload=="dsm") fixture_name="time-dsm";
        else require(c.subload=="build"||c.subload=="dsq","Invalid input/subload combination");
        auto f=load_fixture(args["--fixture-dir"],fixture_name,c.input); run(c,f,strategy(c.strategy_name)); return 0;
    } catch(const std::exception& e) { std::cerr<<"DIR-01 benchmark failed: "<<e.what()<<'\n'; return 1; }
}
