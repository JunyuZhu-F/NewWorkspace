# -*- coding: utf-8 -*-
"""Whitelist-only admission wrapper around the frozen WIKI directory driver."""
import hashlib
import json
from pathlib import Path
import sys

def render(source):
    text=source.decode('utf-8');changes=[]
    def replace(old,new,count=1):
        nonlocal text
        assert text.count(old)==count,old
        text=text.replace(old,new);changes.append(dict(old=old,new=new,count=count))
    replace('require(!std::filesystem::exists(out)&&warmups>=0&&repeats>0,"output/iteration contract");',
            'require(run==0 && warmups==0 && repeats==1 && std::string(argv[6])=="admission","admission only contract");require(!std::filesystem::exists(out),"output exists");')
    replace('Fixture fixture;std::ifstream input(f/"bindings.tsv");',
            'const auto run_started=Clock::now();std::ifstream shape(f/"shape.tsv");std::size_t expected_rows=0,source_rows=0;require(bool(shape>>expected_rows>>source_rows),"shape read");shape>>std::ws;require(shape.eof() && expected_rows>=2 && expected_rows<=25000 && source_rows>=expected_rows && source_rows<=4294967296ull,"shape range");\n    Fixture fixture;std::ifstream input(f/"bindings.tsv");')
    replace('require(dense==fixture.rows.size(),"dense IDs");',
            'require(dense==fixture.rows.size(),"dense IDs");require(id<source_rows && (fixture.rows.empty() || id>fixture.rows.back().first),"global IDs must be increasing and in range");')
    replace('fixture.rows.size()==10000','fixture.rows.size()==expected_rows')
    replace('/__wiki_bench__/','/__scale_prep__/',2)
    replace('oracle.mkdir("/__scale_prep__/");','require(!oracle.query("/__scale_prep__/",true).exists,"reserved directory collision");oracle.mkdir("/__scale_prep__/");')
    replace('std::ofstream times(out/"timings.tsv")',
            'const auto setup_end=Clock::now();std::ofstream wall(out/"wall.tsv");require(bool(wall),"wall output");wall<<"kind\\tstrategy\\tpass\\telapsed_ns\\n";wall<<"setup\\tall\\t-1\\t"<<std::chrono::duration_cast<std::chrono::nanoseconds>(setup_end-run_started).count()<<\'\\n\';\n    std::ofstream times(out/"timings.tsv")')
    replace('for(int pass=0;pass<warmups+repeats;++pass){','for(int pass=0;pass<warmups+repeats;++pass){const auto pass_begin=Clock::now();')
    replace('        }\n        std::cout<<"strategy="',
            '            const auto strategy_name=index->name();index.reset();const auto pass_end=Clock::now();wall<<"pass\\t"<<strategy_name<<\'\\t\'<<pass<<\'\\t\'<<std::chrono::duration_cast<std::chrono::nanoseconds>(pass_end-pass_begin).count()<<\'\\n\';\n        }\n        std::cout<<"strategy="')
    replace('times.flush();answers.flush();space.flush();clock.flush();',
            'times.flush();answers.flush();space.flush();clock.flush();wall<<"total\\tall\\t-1\\t"<<std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-run_started).count()<<\'\\n\';wall.flush();')
    replace('&&clock.good(),"write failure"','&&clock.good()&&wall.good(),"write failure"')
    assert text.count('for(int j=0;j<10000;++j)')==1,'clock calibration changed'
    return text.encode('utf-8'),changes

def main():
    source=Path(sys.argv[1]).read_bytes();dest=Path(sys.argv[2]);generated,changes=render(source);dest.write_bytes(generated)
    dest.with_suffix('.changes.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source).hexdigest(),generated_sha256=hashlib.sha256(generated).hexdigest(),changes=changes),indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
