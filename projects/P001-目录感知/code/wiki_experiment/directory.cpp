#include "directory/index.hpp"
#include "directory/diagnostics.hpp"
#include "oracle.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <vector>
using namespace directory;
using Clock=std::chrono::steady_clock;
static void require(bool x,const std::string& message){if(!x)throw std::runtime_error(message);}
struct Query{std::string id,path;bool recursive;};
struct Operation{std::string id,kind,source,target;};
struct Fixture{std::vector<std::pair<Id,std::string>> rows;std::vector<Query> queries;std::vector<Operation> operations;};
static std::uint64_t digest(const std::set<Id>& ids){std::uint64_t h=14695981039346656037ull;for(auto id:ids)for(unsigned j=0;j<4;++j){h^=(id>>(8*j))&255;h*=1099511628211ull;}return h;}
static std::set<Id> values(const QueryResult& r){auto v=r.ids.values();return {v.begin(),v.end()};}
static void apply(Oracle& o,const Operation& op){if(op.kind=="move")o.move(op.source,op.target);else o.merge(op.source,op.target);}
static void apply(Index& o,const Operation& op){if(op.kind=="move")o.move(op.source,op.target);else o.merge(op.source,op.target);}
static void reset(){
#ifdef DIRECTORY_PHASE_DIAGNOSTICS
    diagnostics::phase_reset();
#endif
}
static void timing(std::ofstream& out,unsigned run,const Index& idx,int pass,int warmups,const std::string& kind,const std::string& id,Clock::time_point a,Clock::time_point b){
    auto total=std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count();require(total>=0,"negative clock");
    out<<run<<'\t'<<idx.name()<<'\t'<<pass<<'\t'<<(pass<warmups)<<'\t'<<kind<<'\t'<<id<<'\t'<<total;
    std::array<std::uint64_t,7> phases{};
#ifdef DIRECTORY_PHASE_DIAGNOSTICS
    auto p=diagnostics::phase_report();require(p.valid && p.depth==0,"phase contract");phases=p.ns;
    std::uint64_t sum=0;for(auto x:phases)sum+=x;require(sum<=static_cast<std::uint64_t>(total),"phase sum outside API interval");
#endif
    for(auto x:phases)out<<'\t'<<x;out<<'\n';
}
int main(int argc,char** argv){try{
    require(argc==7,"usage fixture new-output run warmups repeats label");
    std::filesystem::path f=argv[1],out=argv[2];unsigned run=std::stoul(argv[3]);int warmups=std::stoi(argv[4]),repeats=std::stoi(argv[5]);
    require(!std::filesystem::exists(out)&&warmups>=0&&repeats>0,"output/iteration contract");std::filesystem::create_directories(out);
    Fixture fixture;std::ifstream input(f/"bindings.tsv");std::size_t dense;Id id;std::string path;
    while(input>>dense>>id>>path){require(dense==fixture.rows.size(),"dense IDs");fixture.rows.push_back({id,path});}require(input.eof()&&fixture.rows.size()==10000,"bindings");
    std::ifstream qfile(f/"directory-cases.tsv");std::string caseid;int recursive;
    while(qfile>>caseid>>path>>recursive){require(recursive==0||recursive==1,"mode");fixture.queries.push_back({caseid,path,recursive==1});}require(qfile.eof()&&!fixture.queries.empty(),"queries");
    std::ifstream ofile(f/"operations.tsv");Operation op;
    while(ofile>>op.id>>op.kind>>op.source>>op.target){require(op.kind=="move"||op.kind=="merge","operation kind");fixture.operations.push_back(op);}require(ofile.eof()&&fixture.operations.size()==4,"operations");
    Oracle oracle;for(auto& row:fixture.rows)oracle.insert(row.first,row.second);oracle.mkdir("/__wiki_bench__/");
    std::vector<Oracle> states{oracle};for(auto& x:fixture.operations){apply(oracle,x);states.push_back(oracle);}
    std::vector<std::vector<Oracle::Result>> expected;
    for(auto& state:states){std::vector<Oracle::Result> results;for(auto& q:fixture.queries)results.push_back(state.query(q.path,q.recursive));expected.push_back(std::move(results));}
    std::ofstream times(out/"timings.tsv"),answers(out/"answers.tsv"),space(out/"space.tsv"),clock(out/"clock.tsv");
    times<<"run\tstrategy\tpass\twarmup\tkind\tcase\ttotal_ns\tdirectory_misc_ns\tlocate_ns\tbitmap_copy_ns\tbitmap_sets_ns\tancestors_ns\tcatalog_ns\tcleanup_ns\n";
    answers<<"strategy\tstage\tcase\texists\tcount\tdigest\n";
    space<<"run\tstrategy\tpass\tstage\tdirectories\tcatalog_entries\tbitmaps\tportable_bytes\n";
    clock<<"nanoseconds\n";for(int j=0;j<10000;++j){auto a=Clock::now(),b=Clock::now();clock<<std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count()<<'\n';}
    const std::array<Strategy,3> strategies{Strategy::pe_online,Strategy::pe_offline,Strategy::trie_hi};
    std::uint64_t scope_checks=0;
    for(unsigned pos=0;pos<3;++pos){auto strategy=strategies[(pos+run%3)%3];
        for(int pass=0;pass<warmups+repeats;++pass){
            reset();auto a=Clock::now();auto index=make_index(strategy);index->mkdir("/__wiki_bench__/");for(auto& row:fixture.rows)index->insert(row.first,row.second);auto b=Clock::now();timing(times,run,*index,pass,warmups,"build","build",a,b);
            for(std::size_t stage=0;stage<states.size();++stage){
                require(index->validate().empty(),"invariants");require(index->directories()==states[stage].directories(),"namespace");require(index->bindings()==states[stage].bindings(),"catalog");
                auto s=index->statistics();space<<run<<'\t'<<index->name()<<'\t'<<pass<<'\t'<<stage<<'\t'<<s.directory_count<<'\t'<<s.catalog_entry_count<<'\t'<<s.bitmap_count<<'\t'<<s.roaring_portable_bytes<<'\n';
                for(std::size_t i=0;i<fixture.queries.size();++i){auto& q=fixture.queries[i];reset();a=Clock::now();auto result=index->query(q.path,q.recursive);b=Clock::now();
                    if(stage==0)timing(times,run,*index,pass,warmups,"query",q.id,a,b);
                    auto found=values(result);require(result.exists==expected[stage][i].exists&&found==expected[stage][i].ids,"full scope mismatch");++scope_checks;
                    if(pass==0)answers<<index->name()<<'\t'<<stage<<'\t'<<q.id<<'\t'<<result.exists<<'\t'<<found.size()<<'\t'<<digest(found)<<'\n';
                }
                if(stage<fixture.operations.size()){auto& x=fixture.operations[stage];reset();a=Clock::now();apply(*index,x);b=Clock::now();timing(times,run,*index,pass,warmups,x.kind,x.id,a,b);}
            }
        }
        std::cout<<"strategy="<<static_cast<unsigned>(strategy)<<" passed\n"<<std::flush;
    }
    times.flush();answers.flush();space.flush();clock.flush();require(times.good()&&answers.good()&&space.good()&&clock.good(),"write failure");
    std::cout<<"PASS scope_checks="<<scope_checks<<" label="<<argv[6]<<'\n';return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
