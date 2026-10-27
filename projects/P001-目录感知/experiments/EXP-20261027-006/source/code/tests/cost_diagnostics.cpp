// Reuse the existing frozen fixture loader and independent per-ID oracle checks.
#define main original_benchmark_entry_unused
#include "benchmark.cpp"
#undef main
#include "directory/diagnostics.hpp"
#include <functional>
#include <filesystem>

namespace {
namespace diag=directory::diagnostics;
constexpr bool allocation_mode=
#ifdef DIRECTORY_ALLOCATION_DIAGNOSTICS
true;
#else
false;
#endif
std::string cost_common(const Context& c) {
    auto value=c.common();const std::string old="PROTO-01-20261026";
    auto pos=value.find(old);require(pos!=std::string::npos,"Protocol prefix missing");
    value.replace(pos,old.size(),"PROTO-COST-02-20261027");return value;
}
std::string array_json(const std::array<std::uint64_t,4>& a) {
    return "["+std::to_string(a[0])+","+std::to_string(a[1])+","+std::to_string(a[2])+","+std::to_string(a[3])+"]";
}
struct Measurement { std::uint64_t total_ns; diag::PhaseReport phases; };
template<class F> Measurement observe(F action) {
    diag::phase_reset();auto begin=Clock::now();action();auto end=Clock::now();
    auto p=diag::phase_report();require(p.valid&&p.depth==0,"Unclosed phase event");
    return {static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count()),p};
}
std::string phase_json(const Measurement& m) {
    const char* names[]={"directory_misc","path_location","bitmap_create_copy","bitmap_sets","ancestor_update","catalog","bitmap_cleanup"};
    std::string result="\"diagnostic_total_ns\":"+std::to_string(m.total_ns)+",\"phase_ns\":{";
    for(unsigned i=0;i<7;++i) { if(i)result+=",";result+=escape(names[i])+":"+std::to_string(m.phases.ns[i]); }
    result+="},\"phase_calls\":{";
    for(unsigned i=0;i<7;++i) { if(i)result+=",";result+=escape(names[i])+":"+std::to_string(m.phases.calls[i]); }
    // Cleanup of function locals is charged to the outer core scope; caller result destruction is excluded.
    std::uint64_t directory_observed=0;for(unsigned i=0;i<7;++i)if(i!=5)directory_observed+=m.phases.ns[i];
    return result+"},\"directory_core_observed_ns\":"+std::to_string(directory_observed)+",\"coverage\":\"public_core_scopes_with_direct_nested_intervals\",\"catalog_status\":"+escape(m.phases.calls[5]?"directly_timed":"no_call")+",\"exception_catch_timing\":\"outside_core_scopes_in_public_total\"";
}
void phase_contract() {
    diag::phase_reset();
    try { diag::PhaseScope outer(diag::Phase::directory); {diag::PhaseScope inner(diag::Phase::catalog);} throw 1; } catch(int) {}
    auto r=diag::phase_report();require(r.valid&&r.depth==0,"Exception event closure");
    if(!allocation_mode) require(r.calls[0]==1&&r.calls[5]==1,"Nested phase call counts");
    diag::phase_reset();require(diag::phase_report().calls[5]==0,"Phase reset stale state");
}
void zero_allocations() {
    auto r=diag::allocation_report();require(r.valid,"Allocation ledger invalid");
    require(r.live[1]==0&&r.live[2]==0&&r.live[3]==0,"Owned allocation leak after index destruction");
    require(r.blocks[1]==0&&r.blocks[2]==0&&r.blocks[3]==0,"Owned block leak");
}
void memory_row(const Context& c,const std::string& series,const std::string& label,int iteration,bool warmup) {
    auto r=diag::allocation_report();auto m=memory();require(r.valid,"Allocation ledger invalid");
    append(c.output+"/raw/allocation.jsonl","{"+cost_common(c)+",\"diagnostic_kind\":\"allocation\",\"series\":"+escape(series)+",\"state\":"+escape(label)+",\"iteration\":"+std::to_string(iteration)+",\"warmup\":"+(warmup?"true":"false")+
        ",\"owner_order\":[\"observer_excluded\",\"directory\",\"catalog\",\"bitmap\"],\"requested_live_bytes\":"+array_json(r.live)+",\"category_peak_bytes\":"+array_json(r.peak)+",\"live_blocks\":"+array_json(r.blocks)+",\"total_peak_requested_bytes\":"+std::to_string(r.total_peak)+",\"working_set_bytes\":"+std::to_string(m.working)+",\"private_bytes\":"+std::to_string(m.private_bytes)+",\"peak_working_set_bytes\":"+std::to_string(m.peak)+",\"system_available_physical_bytes\":"+std::to_string(m.available)+",\"process_memory_includes_observer_storage\":true,\"ledger_complete\":true,\"allocator_metadata_included\":false}");
}
// Snapshot before any oracle exists; oracle and validator allocate outside core ownership scopes.
void check_without_retained_oracle(Index& index,const Fixture& f,const std::vector<Operation>& applied) {
    auto before=diag::allocation_report();
    { auto oracle=make_oracle(f);for(const auto& op:applied) if(op.accepted) {if(op.kind=="move")oracle.move(op.a,op.b);else oracle.merge(op.a,op.b);}check_state(index,oracle,f,applied.empty()); }
    if(allocation_mode) require(diag::allocation_report().live==before.live,"Oracle/validation altered owned live bytes");
}
void phase_work(const Context& c,const Fixture& f,Strategy s,int iterations,bool gate) {
    std::unique_ptr<Index> dsq_index;
    if(c.subload=="dsq") {dsq_index=build_index(s,f);check_without_retained_oracle(*dsq_index,f,{});}
    for(int it=0;it<iterations;++it) {
        check_resources();
        auto emit=[&](const std::string& name,const Measurement& m,const std::string& fields) {
            require(allocation_mode||m.phases.calls[0]>0,"Missing core scope");
            append(c.output+"/raw/phases.jsonl","{"+cost_common(c)+",\"diagnostic_kind\":\"phase\",\"sample\":"+escape(name)+",\"iteration\":"+std::to_string(it)+",\"warmup\":"+(!gate&&it<3?"true":"false")+","+phase_json(m)+fields+"}");
        };
        if(c.subload=="build") {
            std::unique_ptr<Index> index;auto m=observe([&] {index=build_index(s,f);});
            if(!allocation_mode) require(m.phases.calls[5]>=f.rows.size()*2,"Build catalog contains/bind coverage");
            emit("build",m,",\"entry_count\":"+std::to_string(f.rows.size()));check_without_retained_oracle(*index,f,{});
        } else if(c.subload=="dsq") {
            for(const auto& q:f.queries) {
                diag::phase_reset();auto begin=Clock::now();auto result=dsq_index->query(q.path,q.recursive);auto end=Clock::now();
                Measurement m{static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(end-begin).count()),diag::phase_report()};
                require(m.phases.valid&&m.phases.depth==0,"Query event closure");
                auto v=result.ids.values();require(v.size()==q.count&&digest(v)==q.digest,"Phase query frozen digest");
                {auto oracle=make_oracle(f);require(ids(result.ids)==oracle.query(q.path,q.recursive).ids,"Phase query per-ID oracle");}
                emit(q.path+(q.recursive?":recursive":":local"),m,",\"path\":"+escape(q.path)+",\"recursive\":"+(q.recursive?"true":"false")+",\"candidate_count\":"+std::to_string(v.size()));
            }
        } else {
            auto index=build_index(s,f);std::vector<Operation> applied;
            for(const auto& op:f.operations) {
                bool accepted=false;
                auto m=observe([&] {try {if(op.kind=="move")index->move(op.a,op.b);else index->merge(op.a,op.b);accepted=true;} catch(const directory::Error&) {}});
                require(accepted==op.accepted,"Phase operation acceptance");
                if(!allocation_mode) require((op.kind=="merge"&&accepted)?m.phases.calls[5]>0:m.phases.calls[5]==0,"Catalog scope call/reset mismatch");
                applied.push_back(op);check_without_retained_oracle(*index,f,applied);
                emit(op.kind+op.a,m,",\"operation\":"+escape(op.kind)+",\"source\":"+escape(op.a)+",\"target\":"+escape(op.b)+",\"accepted\":"+(accepted?"true":"false")+",\"rejection_exception_propagation_coverage\":"+escape(accepted?"not_applicable":"incomplete_outside_core_unwind"));
            }
        }
        if(!dsq_index)zero_allocations();
    }
}
void allocation_work(const Context& c,const Fixture& f,Strategy s,int iterations,bool gate) {
    for(int it=0;it<iterations;++it) {
        check_resources();zero_allocations();diag::allocation_reset_peaks();
        auto index=build_index(s,f);memory_row(c,f.name,"initial",it,!gate&&it<3);check_without_retained_oracle(*index,f,{});
        std::vector<Operation> applied;
        for(const auto& op:f.operations) {
            auto before=diag::allocation_report();diag::allocation_reset_peaks();bool accepted=false;
            try { if(op.kind=="move")index->move(op.a,op.b);else index->merge(op.a,op.b);accepted=true; } catch(const directory::Error&) {}
            require(accepted==op.accepted,"Allocation operation acceptance");
            if(!accepted) require(before.live==diag::allocation_report().live,"Rejected operation live bytes changed");
            memory_row(c,f.name,"after_"+op.kind+(accepted?"":"_rejected"),it,!gate&&it<3);
            applied.push_back(op);check_without_retained_oracle(*index,f,applied);
        }
        index.reset();zero_allocations();memory_row(c,f.name,"after_destroy",it,!gate&&it<3);
    }
}
void overhead(const std::string& out) {
    diag::phase_reset();std::vector<std::uint64_t> empty,framed,deltas;empty.reserve(10000);framed.reserve(10000);deltas.reserve(10000);std::size_t zero=0;
    for(int i=0;i<10000;++i) {
        auto a=Clock::now(),b=Clock::now();auto dt=std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count();empty.push_back(dt);if(dt)deltas.push_back(dt);else ++zero;
        a=Clock::now();{diag::PhaseScope scope(diag::Phase::directory);}b=Clock::now();framed.push_back(std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count());
    }
    auto summarise=[](std::vector<std::uint64_t>& v){std::sort(v.begin(),v.end());return "{\"n\":10000,\"mean_ns\":"+std::to_string(std::accumulate(v.begin(),v.end(),0.0)/v.size())+",\"p90_ns\":"+std::to_string(v[8999])+",\"p99_ns\":"+std::to_string(v[9899])+"}";};
    append(out+"/raw/overhead.jsonl","{\"allocation_mode\":"+std::string(allocation_mode?"true":"false")+",\"nominal_period_ns\":"+std::to_string(double(Clock::period::num)*1e9/Clock::period::den)+",\"minimum_observed_nonzero_delta_ns\":"+(deltas.empty()?"null":std::to_string(*std::min_element(deltas.begin(),deltas.end())))+",\"zero_delta_count\":"+std::to_string(zero)+",\"empty\":"+summarise(empty)+",\"phase_frame\":"+summarise(framed)+"}");
    diag::phase_reset();
}
}
int main(int argc,char** argv) {
    try {
        require(argc>=4,"Usage: cost_diag admit FIXTURE OUTPUT | run FIXTURE INPUT SUBLOAD STRATEGY OUTPUT EXP RUN HASH");
        diag::allocation_initialize();phase_contract();diag::allocation_contract_test();zero_allocations();
        if(std::string(argv[1])=="admit") {
            std::string dir=argv[2],out=std::string(argv[3])+"/attempt-"+std::to_string(epoch_ms());std::filesystem::create_directories(out+"/raw");overhead(out);self_test(dir,false);zero_allocations();
            for(auto s:{Strategy::pe_online,Strategy::pe_offline,Strategy::trie_hi}) {
                for(const auto& base:{"figure2","time"}) {
                    for(const auto& sub:{"build","dsq"}) {
                        auto f=load_fixture(dir,std::string(base)+"-"+sub,base);
                        Context c{"admission_only","admission_source","frozen",std::string(s==Strategy::pe_online?"pe_online":s==Strategy::pe_offline?"pe_offline":"trie_hi"),base,sub,out,0,true};
                        if(!allocation_mode)phase_work(c,f,s,1,true);
                    }
                }
                for(const auto& name:{"figure2-move","figure2-merge","time-dsm"}) {
                    const std::string base=std::string(name)=="time-dsm"?"time":"figure2";
                    auto f=load_fixture(dir,name,base);Context c{"admission_only","admission_source","frozen",std::string(s==Strategy::pe_online?"pe_online":s==Strategy::pe_offline?"pe_offline":"trie_hi"),base,allocation_mode?"allocation":name,out,0,true};
                    if(allocation_mode)allocation_work(c,f,s,1,true);else phase_work(c,f,s,1,true);
                }
            }
            zero_allocations();std::cout<<"Cost admission passed; allocation_mode="<<allocation_mode<<"; no formal matrix run; evidence="<<out<<"\n";return 0;
        }
        require(std::string(argv[1])=="run"&&argc==11,"Invalid formal arguments");
        std::string input=argv[3],subload=argv[4];Context c{argv[7],argv[9],argv[10],argv[5],input,subload,argv[6],std::stoi(argv[8]),true};
        overhead(c.output);auto s=strategy(c.strategy_name);
        if(allocation_mode) {
            require(subload=="allocation","Allocation executable requires allocation workload");
            for(const auto& name:(input=="figure2"?std::vector<std::string>{"figure2-move","figure2-merge"}:std::vector<std::string>{"time-dsm"}))allocation_work(c,load_fixture(argv[2],name,input),s,23,false);
        } else phase_work(c,load_fixture(argv[2],input+"-"+subload,input),s,23,false);
        zero_allocations();append(c.output+"/raw/cost-process.jsonl","{"+cost_common(c)+",\"status\":\"passed\",\"diagnostic_kind\":"+escape(allocation_mode?"allocation":"phase")+"}");return 0;
    } catch(const std::exception& e) {std::cerr<<"Cost diagnostics failed: "<<e.what()<<'\n';return 1;}
}
