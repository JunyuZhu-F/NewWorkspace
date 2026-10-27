#pragma once
// Thin ownership adapter over the pinned CRoaring C API. No directory logic.
#include "roaring.h"
#include "directory/diagnostics.hpp"
#include <cstdint>
#include <new>
#include <utility>
#include <vector>
namespace directory {
class Bitmap {
    roaring::api::roaring_bitmap_t* value_;
    void ensure() { if (!value_) value_=checked(DIR_VALUE(bitmap_copy, roaring::api::roaring_bitmap_create())); }
    static roaring::api::roaring_bitmap_t* checked(roaring::api::roaring_bitmap_t* value) {
        if (!value) throw std::bad_alloc();
        return value;
    }
public:
    Bitmap() : value_(checked(DIR_VALUE(bitmap_copy, roaring::api::roaring_bitmap_create()))) {}
    ~Bitmap() { DIR_PHASE(cleanup) if (value_) roaring::api::roaring_bitmap_free(value_); }
    Bitmap(const Bitmap& other) : value_(checked(DIR_VALUE(bitmap_copy, other.value_ ? roaring::api::roaring_bitmap_copy(other.value_) : roaring::api::roaring_bitmap_create()))) {}
    Bitmap(Bitmap&& other) noexcept : value_(std::exchange(other.value_, nullptr)) {}
    Bitmap& operator=(Bitmap other) noexcept { std::swap(value_,other.value_); return *this; }
    void add(std::uint32_t id) { DIR_PHASE(bitmap_sets) ensure(); roaring::api::roaring_bitmap_add(value_, id); }
    void remove(std::uint32_t id) { if (value_) roaring::api::roaring_bitmap_remove(value_, id); }
    bool contains(std::uint32_t id) const { return value_ && roaring::api::roaring_bitmap_contains(value_, id); }
    std::size_t portable_size() const { return value_ ? roaring::api::roaring_bitmap_portable_size_in_bytes(value_) : 0; }
    std::uint64_t cardinality() const { return value_ ? roaring::api::roaring_bitmap_get_cardinality(value_) : 0; }
    std::vector<std::uint32_t> values() const {
        std::vector<std::uint32_t> result(static_cast<std::size_t>(cardinality()));
        if (!result.empty()) roaring::api::roaring_bitmap_to_uint32_array(value_, result.data());
        return result;
    }
    Bitmap& operator|=(const Bitmap& other) { DIR_PHASE(bitmap_sets) if (this!=&other && other.value_) { ensure(); roaring::api::roaring_bitmap_or_inplace(value_,other.value_); } return *this; }
    Bitmap& operator-=(const Bitmap& other) { DIR_PHASE(bitmap_sets) if (this==&other) { *this=Bitmap{}; } else if (value_ && other.value_) roaring::api::roaring_bitmap_andnot_inplace(value_,other.value_); return *this; }
    bool operator==(const Bitmap& other) const { return (!value_ || !other.value_) ? cardinality()==other.cardinality() : roaring::api::roaring_bitmap_equals(value_,other.value_); }
    bool operator!=(const Bitmap& other) const { return !(*this==other); }
};
} // namespace directory
