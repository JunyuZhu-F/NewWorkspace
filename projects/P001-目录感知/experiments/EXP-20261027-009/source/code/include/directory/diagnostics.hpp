#pragma once
// Diagnostics compile out entirely from default/work-counter builds.
#if defined(DIRECTORY_PHASE_DIAGNOSTICS) || defined(DIRECTORY_ALLOCATION_DIAGNOSTICS)
#include <array>
#include <cstddef>
#include <cstdint>
namespace directory::diagnostics {
enum class Phase : unsigned { directory, locate, bitmap_copy, bitmap_sets, ancestors, catalog, cleanup, count };
enum class Owner : unsigned { observer, directory, catalog, bitmap, count };
struct PhaseReport {
    std::array<std::uint64_t,7> ns{}, calls{};
    unsigned depth=0;
    bool valid=true;
};
void phase_reset();
PhaseReport phase_report();
class PhaseScope {
    bool entered_=false;
public:
    explicit PhaseScope(Phase) noexcept;
    ~PhaseScope();
    PhaseScope(const PhaseScope&)=delete;
};
struct AllocationReport {
    std::array<std::uint64_t,4> live{}, peak{}, blocks{};
    std::uint64_t total_peak=0, allocations=0, releases=0, failures=0;
    bool valid=true;
};
Owner owner();
void set_owner(Owner);
class OwnerScope {
    Owner previous_;
public:
    explicit OwnerScope(Owner value) : previous_(owner()) { set_owner(value); }
    ~OwnerScope() { set_owner(previous_); }
};
template<class T> T catalog_construct() { PhaseScope phase(Phase::catalog); OwnerScope scope(Owner::catalog); return T{}; }
void split_catalog(void* address,std::size_t bytes);
void allocation_initialize();
void allocation_reset_peaks();
AllocationReport allocation_report();
void allocation_contract_test();
}
#endif

#ifdef DIRECTORY_PHASE_DIAGNOSTICS
#define DIR_PHASE(name) directory::diagnostics::PhaseScope dir_phase_scope(directory::diagnostics::Phase::name);
#define DIR_VALUE(name, expr) ([&](){ directory::diagnostics::PhaseScope dir_value_scope(directory::diagnostics::Phase::name); return (expr); }())
#else
#define DIR_PHASE(name)
#define DIR_VALUE(name, expr) (expr)
#endif
#ifdef DIRECTORY_ALLOCATION_DIAGNOSTICS
#define DIR_OWNER(name) directory::diagnostics::OwnerScope dir_owner_scope(directory::diagnostics::Owner::name);
#define DIR_CATALOG_CONTROL Catalog() { directory::diagnostics::split_catalog(this,sizeof(Catalog)); }
#else
#define DIR_OWNER(name)
#define DIR_CATALOG_CONTROL
#endif
#if defined(DIRECTORY_PHASE_DIAGNOSTICS) || defined(DIRECTORY_ALLOCATION_DIAGNOSTICS)
#define DIR_CATALOG_INIT = directory::diagnostics::catalog_construct<std::map<Id,Token*>>()
#else
#define DIR_CATALOG_INIT
#endif
#define DIR_CORE(name) DIR_PHASE(name) DIR_OWNER(directory)
#define DIR_CATALOG_SCOPE DIR_PHASE(catalog) DIR_OWNER(catalog)
