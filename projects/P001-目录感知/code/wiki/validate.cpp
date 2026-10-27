#include "directory/index.hpp"
#include "oracle.hpp"
#include <algorithm>
#include <array>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace directory;
namespace {
void require(bool value,const std::string& message) { if(!value) throw std::runtime_error(message); }
bool below(const std::string& path,const std::string& anchor) { return path.size()>=anchor.size() && path.substr(0,anchor.size())==anchor; }
std::size_t depth(const std::string& p) { return std::count(p.begin(),p.end(),'/')-1; }
std::string leaf(const std::string& p) { auto end=p.size()-1;return p.substr(p.rfind('/',end-1)+1); }
std::uint64_t digest(const std::set<Id>& ids) {
    std::uint64_t value=14695981039346656037ull;
    for(auto id:ids) for(unsigned j=0;j<4;++j) { value^=(id>>(8*j))&255;value*=1099511628211ull; }
    return value;
}
int outcome(const std::function<void()>& f) {
    try { f();return 0; } catch(const Error& e) { return static_cast<int>(e.code)+1; }
}
}
int main(int argc,char** argv) {
    try {
        require(argc==3,"usage: directory_wiki_validate sample-bindings.tsv answers.tsv");
        std::ifstream input(argv[1],std::ios::binary);
        require(input.good(),"input open failed");
        Oracle oracle;
        std::array<std::unique_ptr<Index>,3> indexes{make_index(Strategy::pe_online),make_index(Strategy::pe_offline),make_index(Strategy::trie_hi)};
        std::set<std::string> terminals;
        std::set<Id> ids;
        std::string line;
        std::size_t count=0;
        while(std::getline(input,line)) {
            if(!line.empty() && line.back()=='\r') line.pop_back();
            auto tab=line.find('\t');require(tab!=std::string::npos,"bad TSV");
            auto number=std::stoull(line.substr(0,tab));require(number<=std::numeric_limits<Id>::max(),"ID overflow");
            auto id=static_cast<Id>(number);auto path=line.substr(tab+1);
            require(ids.insert(id).second,"duplicate ID");terminals.insert(path);
            oracle.mkdir(path);oracle.insert(id,path);
            for(auto& index:indexes) {index->mkdir(path);index->insert(id,path);}
            ++count;
        }
        require(input.eof() && count==10000,"wrong input row count");
        for(const auto& path:{"/__wiki_check__/","/__wiki_empty__/"}) {
            require(!oracle.query(path,true).exists,"reserved test directory collides");
            oracle.mkdir(path);for(auto& index:indexes) index->mkdir(path);
        }
        std::string source=*terminals.begin(),target;
        for(auto it=terminals.rbegin();it!=terminals.rend();++it) {
            if(!below(*it,source) && !below(source,*it)) {target=*it;break;}
        }
        require(!target.empty(),"no unrelated terminal pair");
        std::string moved="/__wiki_check__/"+leaf(source);
        std::ofstream answers(argv[2],std::ios::binary);require(answers.good(),"answers open failed");
        std::uint64_t scopes=0;
        auto check=[&](const std::string& stage) {
            auto all_dirs=oracle.directories();auto bindings=oracle.bindings();
            std::map<std::size_t,std::vector<std::string>> levels;
            for(const auto& p:all_dirs) levels[depth(p)].push_back(p);
            std::set<std::string> queries{"/","/__wiki_check__/","/__wiki_empty__/","/__wiki_missing__/",source,target,moved};
            for(auto& level:levels) {
                auto& p=level.second;std::sort(p.begin(),p.end());auto n=std::min<std::size_t>(8,p.size());
                for(std::size_t j=0;j<n;++j) queries.insert(p[n==1?0:j*(p.size()-1)/(n-1)]);
            }
            for(auto& index:indexes) {
                require(index->validate().empty(),stage+" invariant "+index->name());
                require(index->directories()==all_dirs,stage+" tree "+index->name());
                require(index->bindings()==bindings,stage+" catalog "+index->name());
                for(const auto& p:queries) for(bool recursive:{false,true}) {
                    auto expected=oracle.query(p,recursive);auto actual=index->query(p,recursive);
                    auto values=actual.ids.values();std::set<Id> found(values.begin(),values.end());
                    require(actual.exists==expected.exists && found==expected.ids,stage+" scope "+index->name()+" "+p);
                    answers<<stage<<'\t'<<index->name()<<'\t'<<p<<'\t'<<recursive<<'\t'<<actual.exists<<'\t'<<found.size()<<'\t'<<digest(found)<<'\n';
                    ++scopes;
                }
            }
            std::cout<<stage<<" directories="<<all_dirs.size()<<" queries="<<queries.size()<<" scopes_total="<<scopes<<std::endl;
        };
        auto apply=[&](const std::string& stage,auto action,bool reject) {
            auto before_dirs=oracle.directories();auto before_bindings=oracle.bindings();
            auto expected=outcome([&]{action(oracle);});require((expected!=0)==reject,stage+" oracle unexpected outcome");
            if(reject) require(oracle.directories()==before_dirs && oracle.bindings()==before_bindings,stage+" oracle rejection mutated");
            for(auto& index:indexes) {
                auto old_dirs=index->directories();auto old_bindings=index->bindings();
                auto actual=outcome([&]{action(*index);});require(actual==expected,stage+" outcome mismatch");
                if(reject) require(index->directories()==old_dirs && index->bindings()==old_bindings,stage+" rejection mutated");
            }
            check(stage);
        };
        check("initial");
        apply("move",[&](auto& x){x.move(source,"/__wiki_check__/");},false);
        apply("merge",[&](auto& x){x.merge(moved,target);},false);
        apply("reject",[&](auto& x){x.move(target,target);},true);
        answers.flush();require(answers.good(),"answers write failed");
        std::cout<<"PASS records="<<count<<" scope_checks="<<scopes<<" source="<<source<<" target="<<target<<std::endl;
        return 0;
    } catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<std::endl;return 1;}
}
