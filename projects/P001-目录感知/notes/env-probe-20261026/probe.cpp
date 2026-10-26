// Environment-only probe. No directory index, ANN, or dataset is used.
#include <iostream>
#include <vector>

int main() {
    const std::vector<int> values{1, 2, 3};
    const bool ok = values.size() == 3 && sizeof(void*) == 8;
    std::cout << "{\"cplusplus\":" << __cplusplus
              << ",\"msvc\":" << _MSC_VER
              << ",\"pointer_bits\":" << sizeof(void*) * 8
              << ",\"ok\":" << (ok ? "true" : "false") << "}\n";
    return ok ? 0 : 1;
}
