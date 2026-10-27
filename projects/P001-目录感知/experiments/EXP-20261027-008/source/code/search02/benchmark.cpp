// SEARCH-02 wrapper only: the frozen SEARCH-01 backend/contract are generated verbatim.
#include "search01_backend.inc"
#include <chrono>
using Clock=std::chrono::steady_clock;
static_assert(Clock::is_steady,"monotonic timing required");
static long long ns(Clock::time_point a,Clock::time_point b) { return std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count(); }
struct Case { std::string id,path;std::size_t qrow,k;bool recursive; };
struct Response {
    bool exists;
    std::vector<Id> candidates;
    std::vector<Hit> hits;
    long long directory_ns,materialize_ns,ranking_ns,total_ns;
};
static std::vector<Id> to_dense(const std::vector<Id>& ids,const std::vector<Id>& global) {
    std::vector<Id> result;result.reserve(ids.size());
    for (const auto id:ids) {
        const auto it=std::lower_bound(global.begin(),global.end(),id);
        require(it!=global.end() && *it==id,"global ID not in sample");
        result.push_back(static_cast<Id>(it-global.begin()));
    }
    return result;
}
static Response execute(const directory::Index& index,const Backend& backend,const Matrix& queries,const std::vector<Id>& global,const Case& c,std::size_t probes) {
    const auto t0=Clock::now();
    const auto scope=index.query(c.path,c.recursive);
    const auto t1=Clock::now();
    auto ids=scope.ids.values();const auto dense=to_dense(ids,global);
    const auto t2=Clock::now();
    auto hits=backend.search(queries.row(c.qrow),dense,c.k,probes);
    for(auto& hit:hits) { require(hit.id<global.size(),"dense result out of range");hit.id=global[hit.id]; }
    const auto t3=Clock::now();
    return {scope.exists,std::move(ids),std::move(hits),ns(t0,t1),ns(t1,t2),ns(t2,t3),ns(t0,t3)};
}
static void same(const Response& a,const Response& b) {
    require(a.exists==b.exists && a.candidates==b.candidates && a.hits.size()==b.hits.size(),"scope/result count changed");
    for(std::size_t i=0;i<a.hits.size();++i) require(a.hits[i].id==b.hits[i].id && a.hits[i].distance==b.hits[i].distance,"repeat result changed");
    require(b.total_ns>=0 && b.directory_ns>=0 && b.materialize_ns>=0 && b.ranking_ns>=0 && b.total_ns==b.directory_ns+b.materialize_ns+b.ranking_ns,"timer accounting mismatch");
}
static void contracts() {
    self_test();
    require(to_dense({7,1000000},{7,42,1000000})==std::vector<Id>({0,2}),"global/dense mapping");
    bool rejected=false;try{to_dense({8},{7,42,1000000});}catch(const std::runtime_error&){rejected=true;}
    require(rejected,"unknown global ID accepted");
    Matrix m{3,2,{0,0,1,0,-1,0}},q{1,2,{0,0}};Backend b(m,2,42,8);
    auto idx=directory::make_index(directory::Strategy::trie_hi);
    for(const Id id:{7u,42u,1000000u})idx->insert(id,"/a/");
    const auto r=execute(*idx,b,q,{7,42,1000000},{"c","/a/",0,100,true},0);same(r,r);
    require(r.hits.size()==3 && r.hits[0].id==7 && r.hits[1].id==42 && r.hits[2].id==1000000,"mapped ranking/tie");
    std::cout<<"{\"status\":\"passed\",\"suite\":\"search02_contract\"}\n";
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string(argv[1])=="self-test"){contracts();return 0;}
        require(argc==7,"usage: directory_search02 fixture new-output run warmups repetitions label");
        const std::filesystem::path fixture=argv[1],out=argv[2];
        const unsigned run=static_cast<unsigned>(std::stoul(argv[3]));
        const std::size_t warmups=std::stoull(argv[4]),repeats=std::stoull(argv[5]);
        const std::string label=argv[6];require(label=="admission"||label=="formal","invalid run label");
        require(!std::filesystem::exists(out),"output exists");std::filesystem::create_directories(out);
        const auto start=Clock::now();
        const auto corpus=load_vectors(fixture/"corpus.fvecs"),queries=load_vectors(fixture/"queries.fvecs");
        require(corpus.n==10000 && corpus.d==1024 && queries.n==501 && queries.d==1024,"unexpected shape");
        Backend backend(corpus,16,42,8);backend.save(out/"model.json");
        std::vector<Id> global;std::vector<std::string> paths;
        std::ifstream bindings(fixture/"bindings.tsv");require(bool(bindings),"open bindings");
        Id dense,id;std::string path;
        while(bindings>>dense>>id>>path){require(dense==global.size(),"dense binding mismatch");global.push_back(id);paths.push_back(path);}
        require(bindings.eof() && global.size()==corpus.n && std::is_sorted(global.begin(),global.end()) && std::adjacent_find(global.begin(),global.end())==global.end(),"bad global IDs");
        std::vector<Case> cases;std::ifstream input(fixture/"cases.tsv");require(bool(input),"open cases");
        std::string caseid;std::size_t qrow,k;int recursive;
        while(input>>caseid>>qrow>>path>>recursive>>k){require(recursive==0||recursive==1,"bad mode");cases.push_back({caseid,path,qrow,k,recursive==1});}
        require(input.eof() && cases.size()==1002,"bad cases");
        const auto setup=ns(start,Clock::now());
        std::ofstream calibration(out/"clock.csv");calibration<<"nanoseconds\n";
        for(int i=0;i<10000;++i){const auto a=Clock::now();const auto z=Clock::now();calibration<<ns(a,z)<<'\n';}
        std::vector<std::pair<std::size_t,std::size_t>> order;
        for(std::size_t i=0;i<cases.size();++i)for(const std::size_t probes:{0u,1u,4u,16u})order.emplace_back(i,probes);
        std::mt19937 rng(20261027+run);std::shuffle(order.begin(),order.end(),rng);
        std::ofstream ordering(out/"order.tsv");for(const auto& item:order)ordering<<cases[item.first].id<<'\t'<<item.second<<'\n';
        std::ofstream results(out/"answers.jsonl"),scopes(out/"scopes.tsv"),timing(out/"timings.csv"),build(out/"setup.csv");
        require(bool(results)&&bool(scopes)&&bool(timing)&&bool(build),"open output");results<<std::setprecision(17);
        timing<<"run,strategy,case,probes,repeat,directory_ns,materialize_ns,ranking_ns,total_ns\n";
        build<<"strategy,index_build_validate_ns,common_load_train_ns\n";
        std::size_t rows=0;
        const std::array<directory::Strategy,3> strategies{directory::Strategy::pe_online,directory::Strategy::pe_offline,directory::Strategy::trie_hi};
        for(std::size_t position=0;position<3;++position){
            const auto before=Clock::now();auto idx=directory::make_index(strategies[(position+run%3)%3]);
            for(std::size_t i=0;i<global.size();++i)idx->insert(global[i],paths[i]);
            require(idx->validate().empty(),"index invariant");build<<idx->name()<<','<<ns(before,Clock::now())<<','<<setup<<'\n';
            std::vector<Response> baseline;baseline.reserve(order.size());std::set<std::string> saved_scopes;
            for(const auto& item:order){
                const auto& c=cases[item.first];auto r=execute(*idx,backend,queries,global,c,item.second);same(r,r);
                if(saved_scopes.insert(c.id).second){scopes<<idx->name()<<'\t'<<c.id<<'\t'<<r.exists<<'\t';for(std::size_t i=0;i<r.candidates.size();++i){if(i)scopes<<',';scopes<<r.candidates[i];}scopes<<'\n';}
                results<<"{\"strategy\":\""<<idx->name()<<"\",\"case\":\""<<c.id<<"\",\"probes\":"<<item.second<<",\"ids\":[";
                for(std::size_t i=0;i<r.hits.size();++i){if(i)results<<',';results<<r.hits[i].id;}results<<"],\"distances\":[";
                for(std::size_t i=0;i<r.hits.size();++i){if(i)results<<',';results<<r.hits[i].distance;}results<<"]}\n";baseline.push_back(std::move(r));
            }
            struct Row{std::size_t item,repeat;long long dir,materialize,rank,total;};std::vector<Row> buffer;buffer.reserve(order.size()*repeats);
            for(std::size_t sweep=0;sweep<warmups+repeats;++sweep){
                for(std::size_t j=0;j<order.size();++j){const auto& item=order[j];auto r=execute(*idx,backend,queries,global,cases[item.first],item.second);same(baseline[j],r);
                    if(sweep>=warmups)buffer.push_back({j,sweep-warmups,r.directory_ns,r.materialize_ns,r.ranking_ns,r.total_ns});}
            }
            for(const auto& r:buffer){const auto& item=order[r.item];timing<<run<<','<<idx->name()<<','<<cases[item.first].id<<','<<item.second<<','<<r.repeat<<','<<r.dir<<','<<r.materialize<<','<<r.rank<<','<<r.total<<'\n';++rows;}
            std::cout<<"{\"strategy\":\""<<idx->name()<<"\",\"status\":\"completed\"}\n"<<std::flush;
        }
        require(bool(results)&&bool(scopes)&&bool(timing)&&bool(build)&&bool(calibration)&&bool(ordering),"write output failed");
        std::cout<<"{\"status\":\"completed\",\"timing_rows\":"<<rows<<",\"label\":\""<<label<<"\"}\n";
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
