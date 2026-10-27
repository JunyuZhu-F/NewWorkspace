"""One-time, checked annotation of the previously snapshotted baseline."""
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=root/'src/index.cpp';s=p.read_text(encoding='utf-8')
assert 'DIR_CORE' not in s
s=s.replace('#include "directory/index.hpp"','#include "directory/index.hpp"\n#include "directory/diagnostics.hpp"',1)
s=s.replace('std::map<Id, Token*> entries_;','std::map<Id, Token*> entries_ DIR_CATALOG_INIT;',1)
s=s.replace('public:\n    bool contains','public:\n    DIR_CATALOG_CONTROL\n    bool contains',1)
for signature in ['bool contains(Id id) const {','void bind(Id id, Token* directory) {','void rebind(Token* source, Token* target, MaintenanceWork& work) {']:
    assert s.count(signature)==1
    s=s.replace(signature,signature+' DIR_CATALOG_SCOPE',1)
for signature in ['void mkdir(const std::string& path) override {','void insert(Id id,const std::string& path) override {',
                  'QueryResult query(const std::string& path,bool recursive) const override {',
                  'void move(const std::string& source,const std::string& destination) override {',
                  'void merge(const std::string& source,const std::string& target) override {']:
    assert s.count(signature)==2,signature
    s=s.replace(signature,signature+'\n        DIR_CORE(directory)')
for signature in ['void update_ancestors(const std::string& old_root,const std::string& new_root,const Bitmap& ids) {',
                  'static void update_ancestors(const std::set<TrieNode*>& old_set,const std::set<TrieNode*>& new_set,const Bitmap& ids) {']:
    assert s.count(signature)==1
    s=s.replace(signature,signature+'\n        DIR_CORE(ancestors)',1)
signature='std::unique_ptr<Index> make_index(Strategy strategy) {'
assert s.count(signature)==1
s=s.replace(signature,signature+'\n    DIR_CORE(directory)',1)
p.write_text(s,encoding='utf-8')
p=root/'src/path.cpp';s=p.read_text(encoding='utf-8');assert 'DIR_PHASE' not in s
s=s.replace('#include "directory/index.hpp"','#include "directory/index.hpp"\n#include "directory/diagnostics.hpp"',1)
s=s.replace('std::vector<std::string> parse_path(const std::string& path) {','std::vector<std::string> parse_path(const std::string& path) {\n    DIR_PHASE(locate)',1)
p.write_text(s,encoding='utf-8')
p=root/'include/directory/bitmap.hpp';s=p.read_text(encoding='utf-8');assert 'DIR_PHASE' not in s
s=s.replace('#include "roaring.h"','#include "roaring.h"\n#include "directory/diagnostics.hpp"',1)
s=s.replace('checked(roaring::api::roaring_bitmap_create())','checked(DIR_VALUE(bitmap_copy, roaring::api::roaring_bitmap_create()))')
s=s.replace('checked(other.value_ ? roaring::api::roaring_bitmap_copy(other.value_) : roaring::api::roaring_bitmap_create())','checked(DIR_VALUE(bitmap_copy, other.value_ ? roaring::api::roaring_bitmap_copy(other.value_) : roaring::api::roaring_bitmap_create()))')
s=s.replace('~Bitmap() {','~Bitmap() { DIR_PHASE(cleanup)',1)
s=s.replace('Bitmap& operator|=(const Bitmap& other) {','Bitmap& operator|=(const Bitmap& other) { DIR_PHASE(bitmap_sets)',1)
s=s.replace('Bitmap& operator-=(const Bitmap& other) {','Bitmap& operator-=(const Bitmap& other) { DIR_PHASE(bitmap_sets)',1)
s=s.replace('void add(std::uint32_t id) {','void add(std::uint32_t id) { DIR_PHASE(bitmap_sets)',1)
p.write_text(s,encoding='utf-8')
print('Added only diagnostic macros/scopes to index/path/bitmap; algorithm statements retained.')
