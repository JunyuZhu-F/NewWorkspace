#define main original_core_test_entry
#include "core_tests.cpp"
#undef main
#include "directory/diagnostics.hpp"
int main(int argc,char** argv) {
    directory::diagnostics::allocation_initialize();
    int result=original_core_test_entry(argc,argv);
    auto live=directory::diagnostics::allocation_report();
    if(!live.valid||live.live[1]||live.live[2]||live.live[3]) {std::cerr<<"Owned memory remains after core test\n";return 1;}
    return result;
}
