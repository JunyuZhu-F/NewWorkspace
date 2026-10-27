// Independent exact/IVF-Flat admission backend, NOT Viking or its PG executor.
// Frozen project protocol: notes/search01-protocol-20261027.md.
#include "directory/index.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <vector>

using directory::Id;
static void require(bool b, const std::string& s) { if (!b) throw std::runtime_error(s); }
struct Matrix {
    std::size_t n=0, d=0;
    std::vector<float> x;
    const float* row(std::size_t i) const { require(i<n,"vector row out of bounds"); return x.data()+i*d; }
};
static Matrix load_vectors(const std::filesystem::path& p) {
    std::ifstream in(p,std::ios::binary); require(bool(in),"open vectors");
    Matrix m; std::int32_t d;
    while (in.read(reinterpret_cast<char*>(&d),4)) {
        require(d>0 && d<=4096,"bad dimension");
        if (!m.d) m.d=static_cast<std::size_t>(d);
        require(m.d==static_cast<std::size_t>(d),"inconsistent dimension");
        const auto start=m.x.size(); m.x.resize(start+m.d);
        in.read(reinterpret_cast<char*>(m.x.data()+start),static_cast<std::streamsize>(4*m.d));
        require(bool(in),"truncated vector");
        for (std::size_t j=start;j<m.x.size();++j) require(std::isfinite(m.x[j]),"nonfinite vector");
        ++m.n;
    }
    require(in.eof() && in.gcount()==0 && m.n>0,"trailing header or empty vectors");
    return m;
}
static double l2(const float* a,const float* b,std::size_t d) {
    double total=0;
    for (std::size_t j=0;j<d;++j) { double v=double(a[j])-double(b[j]); total+=v*v; }
    return total;
}
struct Hit { Id id; double distance; };
static bool less_hit(const Hit& a,const Hit& b) { return a.distance<b.distance || (a.distance==b.distance && a.id<b.id); }
class Backend {
    const Matrix& m_;
    std::size_t clusters_;
    std::vector<double> centers_;
    std::vector<std::size_t> assignment_;
    double coarse(const float* q,std::size_t c) const {
        double sum=0;
        for (std::size_t j=0;j<m_.d;++j) { double v=double(q[j])-centers_[c*m_.d+j]; sum+=v*v; }
        return sum;
    }
    std::size_t nearest(const float* q) const {
        std::size_t best=0; double score=coarse(q,0);
        for (std::size_t c=1;c<clusters_;++c) { double v=coarse(q,c); if (v<score) { score=v;best=c; } }
        return best;
    }
public:
    Backend(const Matrix& m,std::size_t clusters,unsigned seed,std::size_t iterations) : m_(m),clusters_(clusters) {
        require(m.n && m.d && clusters>0 && clusters<=m.n,"invalid training shape");
        centers_.resize(clusters*m.d); assignment_.resize(m.n);
        std::mt19937 rng(seed); std::set<std::size_t> selected;
        for (std::size_t c=0;c<clusters;++c) {
            std::size_t i;
            do { i=static_cast<std::size_t>(rng())%m.n; } while (!selected.insert(i).second);
            std::copy(m.row(i),m.row(i)+m.d,centers_.begin()+c*m.d);
        }
        for (std::size_t step=0;step<iterations;++step) {
            std::vector<double> sum(clusters*m.d,0); std::vector<std::size_t> count(clusters,0);
            for (std::size_t i=0;i<m.n;++i) {
                const auto c=nearest(m.row(i)); assignment_[i]=c; ++count[c];
                for (std::size_t j=0;j<m.d;++j) sum[c*m.d+j]+=double(m.row(i)[j]);
            }
            for (std::size_t c=0;c<clusters;++c) if (count[c])
                for (std::size_t j=0;j<m.d;++j) centers_[c*m.d+j]=sum[c*m.d+j]/double(count[c]);
        }
        // Final assignment must correspond to the final saved centroids.
        for (std::size_t i=0;i<m.n;++i) assignment_[i]=nearest(m.row(i));
    }
    std::vector<Hit> search(const float* q,const std::vector<Id>& allowed,std::size_t k,std::size_t probes) const {
        require(probes<=clusters_,"too many probes");
        for (std::size_t j=0;j<m_.d;++j) require(std::isfinite(q[j]),"nonfinite query");
        require(std::is_sorted(allowed.begin(),allowed.end()) && std::adjacent_find(allowed.begin(),allowed.end())==allowed.end(),"candidate IDs must be sorted unique");
        std::vector<bool> visit(clusters_,probes==0);
        if (probes) {
            std::vector<std::pair<double,std::size_t>> rank;
            for (std::size_t c=0;c<clusters_;++c) rank.emplace_back(coarse(q,c),c);
            std::sort(rank.begin(),rank.end());
            for (std::size_t j=0;j<probes;++j) visit[rank[j].second]=true;
        }
        std::vector<Hit> hits;
        for (const auto id:allowed) {
            require(id<m_.n,"candidate ID outside vector matrix");
            if (visit[assignment_[id]]) hits.push_back({id,l2(q,m_.row(id),m_.d)});
        }
        const auto size=std::min(k,hits.size());
        std::partial_sort(hits.begin(),hits.begin()+size,hits.end(),less_hit); hits.resize(size);
        return hits;
    }
    void save(const std::filesystem::path& p) const {
        std::ofstream out(p); require(bool(out),"open model output"); out<<std::setprecision(17);
        out<<"{\"clusters\":"<<clusters_<<",\"dimension\":"<<m_.d<<",\"centers\":[";
        for (std::size_t i=0;i<centers_.size();++i) { if(i) out<<',';out<<centers_[i]; }
        out<<"],\"assignment\":[";
        for (std::size_t i=0;i<assignment_.size();++i) { if(i) out<<',';out<<assignment_[i]; }
        out<<"]}\n"; require(bool(out),"write model");
    }
};
static void self_test() {
    Matrix m{6,2,{0,0, 1,0, -1,0, 0,1, 2,0, 0,0}};
    Backend b(m,3,42,8); const float q[2]{0,0};
    const std::vector<Id> all{0,1,2,3,4,5};
    const auto exact=b.search(q,all,100,0), full=b.search(q,all,100,3);
    require(exact.size()==6 && exact[0].id==0 && exact[1].id==5 && exact[2].id==1 && exact[3].id==2 && exact[4].id==3,"tie/order/<k contract");
    for(std::size_t i=0;i<exact.size();++i) require(exact[i].id==full[i].id && exact[i].distance==full[i].distance,"all-list equivalence");
    require(b.search(q,{},100,0).empty() && b.search(q,all,0,1).empty(),"empty/k0 contract");
    require(b.search(q,{2,4},1,0)[0].id==2,"prefilter before topk");
    int rejected=0;
    try { b.search(q,{6},1,0); } catch(const std::runtime_error&) { ++rejected; }
    try { b.search(q,{1,1},1,0); } catch(const std::runtime_error&) { ++rejected; }
    try { b.search(q,all,1,4); } catch(const std::runtime_error&) { ++rejected; }
    const float bad[2]{std::numeric_limits<float>::quiet_NaN(),0};
    try { b.search(bad,all,1,0); } catch(const std::runtime_error&) { ++rejected; }
    require(rejected==4,"invalid request rejection");
    // A moved/merged scope must consume the same stable vectors, without reindexing.
    for(const auto strategy:{directory::Strategy::pe_online,directory::Strategy::pe_offline,directory::Strategy::trie_hi}) {
        auto idx=directory::make_index(strategy); idx->insert(0,"/a/");idx->insert(1,"/a/x/");idx->insert(2,"/ab/");
        require(idx->query("/a/",true).ids.values()==std::vector<Id>({0,1}),"path segment boundary");
        idx->mkdir("/b/");idx->move("/a/","/b/");
        require(!idx->query("/a/",true).exists,"old moved scope");
        require(b.search(q,idx->query("/b/a/",true).ids.values(),100,0)[0].id==0,"search after move");
        idx->merge("/b/a/","/ab/");
        const auto h=b.search(q,idx->query("/ab/",true).ids.values(),100,0);
        require(h.size()==3 && h[0].id==0 && h[1].id==1 && h[2].id==2,"search after merge");
        require(idx->validate().empty(),"post-maintenance invariants");
    }
    std::cout<<"{\"status\":\"passed\",\"suite\":\"search_contract\"}\n";
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string(argv[1])=="self-test") { self_test();return 0; }
        require(argc==3,"usage: directory_search <fixture-dir> <new-output-dir> | self-test");
        const std::filesystem::path fixture=argv[1],output=argv[2];
        require(!std::filesystem::exists(output),"output already exists");std::filesystem::create_directories(output);
        const auto corpus=load_vectors(fixture/"corpus.fvecs"),queries=load_vectors(fixture/"queries.fvecs");
        require(corpus.d==queries.d && corpus.n==10000 && corpus.d==1024,"unexpected admission shape");
        Backend backend(corpus,16,42,8);backend.save(output/"model.json");
        std::vector<std::string> paths;std::ifstream bind(fixture/"bindings.tsv"); require(bool(bind),"open bindings");
        Id id;std::string p;
        while(bind>>id>>p) {require(id==paths.size(),"binding row/ID mismatch");paths.push_back(p);}
        require(bind.eof() && paths.size()==corpus.n,"bad bindings");
        std::ofstream scopes(output/"scopes.tsv"),results(output/"results.jsonl");
        require(bool(scopes)&&bool(results),"open outputs");results<<std::setprecision(17);
        std::size_t rows=0,cases=0;
        for(const auto strategy:{directory::Strategy::pe_online,directory::Strategy::pe_offline,directory::Strategy::trie_hi}) {
            auto idx=directory::make_index(strategy);
            for(std::size_t i=0;i<paths.size();++i) idx->insert(static_cast<Id>(i),paths[i]);
            idx->mkdir("/__empty__/");require(idx->validate().empty(),"index invariant failure");
            std::ifstream input(fixture/"cases.tsv"); require(bool(input),"open cases");
            std::string caseid,path;std::size_t qrow,k;int recursive;
            while(input>>caseid>>qrow>>path>>recursive>>k) {
                require(recursive==0 || recursive==1,"bad mode");
                const auto scope=idx->query(path,recursive==1);const auto allowed=scope.ids.values();
                scopes<<idx->name()<<'\t'<<caseid<<'\t'<<scope.exists<<'\t';
                for(std::size_t i=0;i<allowed.size();++i) {if(i) scopes<<',';scopes<<allowed[i];}scopes<<'\n';
                for(const std::size_t probes:{0u,1u,4u,16u}) {
                    const auto hits=backend.search(queries.row(qrow),allowed,k,probes);
                    results<<"{\"strategy\":\""<<idx->name()<<"\",\"case\":\""<<caseid<<"\",\"probes\":"<<probes<<",\"ids\":[";
                    for(std::size_t i=0;i<hits.size();++i) {if(i)results<<',';results<<hits[i].id;}
                    results<<"],\"distances\":[";
                    for(std::size_t i=0;i<hits.size();++i) {if(i)results<<',';results<<hits[i].distance;}
                    results<<"]}\n";++rows;
                }
                ++cases;
            }
            require(input.eof(),"bad case file");
        }
        require(bool(scopes)&&bool(results),"write outputs");
        std::cout<<"{\"status\":\"completed\",\"scope_rows\":"<<cases<<",\"result_rows\":"<<rows<<"}\n";
        return 0;
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}
