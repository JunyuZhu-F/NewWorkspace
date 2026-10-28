#include "directory/diagnostics.hpp"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <limits>
#include <new>
#include <stdexcept>
#include <malloc.h>
#include "roaring.h"

namespace directory::diagnostics {
namespace {
using Clock=std::chrono::steady_clock;
PhaseReport phases;
Phase phase_stack[64];
Clock::time_point last;
Owner current_owner=Owner::observer;
void charge(Clock::time_point now) {
    if(phases.depth) phases.ns[static_cast<unsigned>(phase_stack[phases.depth-1])]+=static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(now-last).count());
}
}
void phase_reset() { if(phases.depth) std::abort(); phases={}; }
PhaseReport phase_report() { return phases; }
PhaseScope::PhaseScope(Phase p) noexcept {
#ifdef DIRECTORY_PHASE_DIAGNOSTICS
    auto now=Clock::now(); charge(now);
    if(phases.depth==64) { phases.valid=false; std::abort(); }
    phase_stack[phases.depth++]=p; ++phases.calls[static_cast<unsigned>(p)]; last=now; entered_=true;
#else
    (void)p;
#endif
}
PhaseScope::~PhaseScope() {
    if(entered_) { auto now=Clock::now(); charge(now); --phases.depth; last=now; }
}
Owner owner() { return current_owner; }
void set_owner(Owner value) { current_owner=value; }
}

#ifdef DIRECTORY_ALLOCATION_DIAGNOSTICS
namespace {
using directory::diagnostics::Owner;
constexpr std::size_t capacity=1u<<18;
struct Entry { void* pointer; std::size_t bytes, catalog_inline; Owner tag; unsigned char state; };
Entry ledger[capacity]{}; // Observer storage: fixed, no recursion or allocated map nodes.
directory::diagnostics::AllocationReport accounting;
bool fail_next=false;
std::size_t hash_pointer(void* p) { return (reinterpret_cast<std::uintptr_t>(p)>>4)*11400714819323198485ull&(capacity-1); }
Entry* find_entry(void* p) {
    auto h=hash_pointer(p);
    for(std::size_t n=0;n<capacity;++n) {
        auto& e=ledger[(h+n)&(capacity-1)];
        if(!e.state) return nullptr;
        if(e.state==1&&e.pointer==p) return &e;
    }
    return nullptr;
}
void peaks() {
    std::uint64_t total=0;
    for(unsigned i=1;i<4;++i) { accounting.peak[i]=std::max(accounting.peak[i],accounting.live[i]); total+=accounting.live[i]; }
    accounting.total_peak=std::max(accounting.total_peak,total);
}
void record(void* p,std::size_t size,Owner tag) {
    if(!p) { ++accounting.failures; return; }
    if(tag==Owner::observer) return;
    auto h=hash_pointer(p);Entry* tombstone=nullptr;
    for(std::size_t n=0;n<capacity;++n) {
        auto& e=ledger[(h+n)&(capacity-1)];
        if(e.state==1&&e.pointer==p) std::abort();
        if(e.state==2&&!tombstone) tombstone=&e;
        if(!e.state) {
            auto* slot=tombstone?tombstone:&e; *slot={p,size,0,tag,1};
            auto i=static_cast<unsigned>(tag);accounting.live[i]+=size;++accounting.blocks[i];++accounting.allocations;peaks();return;
        }
    }
    if(tombstone) {
        *tombstone={p,size,0,tag,1};auto i=static_cast<unsigned>(tag);accounting.live[i]+=size;++accounting.blocks[i];++accounting.allocations;peaks();return;
    }
    accounting.valid=false;std::abort();
}
void forget(void* p) {
    if(!p) return;
    if(auto* e=find_entry(p)) {
        const auto i=static_cast<unsigned>(e->tag);
        accounting.live[i]-=e->bytes-e->catalog_inline;
        accounting.live[static_cast<unsigned>(Owner::catalog)]-=e->catalog_inline;
        --accounting.blocks[i];++accounting.releases;e->state=2;
    }
}
void* allocate(std::size_t bytes,bool aligned=false,std::size_t alignment=0) {
    if(fail_next) { fail_next=false;++accounting.failures;return nullptr; }
    auto* p=aligned?_aligned_malloc(bytes?bytes:1,alignment):std::malloc(bytes?bytes:1);
    record(p,bytes,directory::diagnostics::owner());return p;
}
void release(void* p,bool aligned=false) { forget(p);if(aligned) _aligned_free(p);else std::free(p); }
void* bitmap_malloc(std::size_t n) { directory::diagnostics::OwnerScope scope(directory::diagnostics::owner()==Owner::observer?Owner::observer:Owner::bitmap);return allocate(n); }
void* bitmap_calloc(std::size_t n,std::size_t size) {
    if(size&&n>std::numeric_limits<std::size_t>::max()/size) { ++accounting.failures; return nullptr; }
    directory::diagnostics::OwnerScope scope(directory::diagnostics::owner()==Owner::observer?Owner::observer:Owner::bitmap);
    if(fail_next) { fail_next=false;++accounting.failures;return nullptr; }
    auto* p=std::calloc(n,size);record(p,n*size,directory::diagnostics::owner());return p;
}
void* bitmap_realloc(void* old,std::size_t n) {
    if(!old) return bitmap_malloc(n);
    if(!n) { release(old);return nullptr; }
    if(fail_next) { fail_next=false;++accounting.failures;return nullptr; }
    auto* e=find_entry(old); const auto tag=e?e->tag:Owner::observer;
    auto* p=std::realloc(old,n);
    if(!p) { ++accounting.failures;return nullptr; }
    forget(old);record(p,n,tag);return p;
}
void bitmap_free(void* p) { release(p); }
void* bitmap_aligned(std::size_t alignment,std::size_t n) {
    directory::diagnostics::OwnerScope scope(directory::diagnostics::owner()==Owner::observer?Owner::observer:Owner::bitmap);return allocate(n,true,alignment);
}
void bitmap_aligned_free(void* p) { release(p,true); }
void contract(bool condition,const char* message) { if(!condition) throw std::runtime_error(message); }
}
void* operator new(std::size_t n) { if(auto* p=allocate(n)) return p;throw std::bad_alloc(); }
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void* p) noexcept { release(p); }
void operator delete[](void* p) noexcept { release(p); }
void operator delete(void* p,std::size_t) noexcept { release(p); }
void operator delete[](void* p,std::size_t) noexcept { release(p); }
void* operator new(std::size_t n,const std::nothrow_t&) noexcept { return allocate(n); }
void* operator new[](std::size_t n,const std::nothrow_t&) noexcept { return allocate(n); }
void operator delete(void* p,const std::nothrow_t&) noexcept { release(p); }
void operator delete[](void* p,const std::nothrow_t&) noexcept { release(p); }
void* operator new(std::size_t n,std::align_val_t a) { if(auto* p=allocate(n,true,static_cast<std::size_t>(a))) return p;throw std::bad_alloc(); }
void* operator new[](std::size_t n,std::align_val_t a) { return ::operator new(n,a); }
void operator delete(void* p,std::align_val_t) noexcept { release(p,true); }
void operator delete[](void* p,std::align_val_t) noexcept { release(p,true); }
void operator delete(void* p,std::size_t,std::align_val_t) noexcept { release(p,true); }
void operator delete[](void* p,std::size_t,std::align_val_t) noexcept { release(p,true); }
void* operator new(std::size_t n,std::align_val_t a,const std::nothrow_t&) noexcept { return allocate(n,true,static_cast<std::size_t>(a)); }
void* operator new[](std::size_t n,std::align_val_t a,const std::nothrow_t&) noexcept { return allocate(n,true,static_cast<std::size_t>(a)); }
void operator delete(void* p,std::align_val_t,const std::nothrow_t&) noexcept { release(p,true); }
void operator delete[](void* p,std::align_val_t,const std::nothrow_t&) noexcept { release(p,true); }
namespace directory::diagnostics {
void split_catalog(void* address,std::size_t bytes) {
    const auto a=reinterpret_cast<std::uintptr_t>(address);
    for(auto& e:ledger) if(e.state==1&&e.tag==Owner::directory) {
        auto start=reinterpret_cast<std::uintptr_t>(e.pointer);
        if(a>=start&&a-start<=e.bytes&&bytes<=e.bytes-(a-start)) {
            if(e.catalog_inline) std::abort(); e.catalog_inline=bytes;
            accounting.live[1]-=bytes;accounting.live[2]+=bytes;peaks();return;
        }
    }
    accounting.valid=false;std::abort();
}
void allocation_initialize() {
    roaring_memory_t hooks{bitmap_malloc,bitmap_realloc,bitmap_calloc,bitmap_free,bitmap_aligned,bitmap_aligned_free};
    roaring_init_memory_hook(hooks);
}
void allocation_reset_peaks() { accounting.peak=accounting.live;accounting.total_peak=accounting.live[1]+accounting.live[2]+accounting.live[3]; }
AllocationReport allocation_report() { return accounting; }
void allocation_contract_test() {
    auto before=allocation_report();
    {
        OwnerScope scope(Owner::directory);
        void* p=::operator new(23);contract(accounting.live[1]==before.live[1]+23,"new requested size");
        { OwnerScope other(Owner::catalog);::operator delete(p,std::size_t(23)); }
        p=::operator new[](37,std::nothrow);::operator delete[](p,std::nothrow);
        p=::operator new(64,std::align_val_t(64));contract(reinterpret_cast<std::uintptr_t>(p)%64==0,"aligned new");::operator delete(p,std::size_t(64),std::align_val_t(64));
        p=::operator new[](128,std::align_val_t(64),std::nothrow);::operator delete[](p,std::align_val_t(64),std::nothrow);
        p=::operator new(0);::operator delete(p);
        p=::operator new[](41);::operator delete[](p,std::size_t(41));
        p=::operator new[](96,std::align_val_t(32));::operator delete[](p,std::align_val_t(32));
        fail_next=true;contract(::operator new(12,std::nothrow)==nullptr,"nothrow failure");
        fail_next=true;bool threw=false;try { (void)::operator new(12); } catch(const std::bad_alloc&) { threw=true; }contract(threw,"throwing new failure");
        p=bitmap_calloc(5,13);contract(accounting.live[3]==before.live[3]+65,"calloc ledger");
        fail_next=true;contract(bitmap_realloc(p,130)==nullptr,"realloc failure");contract(accounting.live[3]==before.live[3]+65,"failed realloc keeps old block");
        p=bitmap_realloc(p,130);contract(accounting.live[3]==before.live[3]+130,"realloc ledger");bitmap_free(p);
        p=bitmap_aligned(64,256);contract(reinterpret_cast<std::uintptr_t>(p)%64==0,"aligned roaring");bitmap_aligned_free(p);
        contract(bitmap_calloc(std::numeric_limits<std::size_t>::max(),2)==nullptr,"calloc overflow");
        bitmap_free(nullptr);::operator delete(nullptr);p=bitmap_realloc(nullptr,32);bitmap_realloc(p,0);
    }
    contract(allocation_report().live==before.live,"contract returns to baseline");
}
}
#else
namespace directory::diagnostics {
void split_catalog(void*,std::size_t) {}
void allocation_initialize() {}
void allocation_reset_peaks() {}
AllocationReport allocation_report() { return {}; }
void allocation_contract_test() {}
}
#endif
