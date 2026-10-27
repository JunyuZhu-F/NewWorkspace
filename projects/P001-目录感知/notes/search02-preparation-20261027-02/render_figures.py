import subprocess,os,pathlib,json,shutil,sys
project=pathlib.Path.cwd(); exp=project/'experiments/EXP-20261027-006'; out=exp/'analysis-02';out.mkdir(exist_ok=False)
shutil.copyfile(exp/'verification.json',out/'verification.json')
root=pathlib.Path('D:/anaconda3/envs/zhu_3_10');env=os.environ.copy()
remaining=[x for x in env.get('PATH','').split(os.pathsep) if 'anaconda3' not in x.lower()]
env['PATH']=os.pathsep.join([str(root),str(root/'Library/bin'),str(root/'Scripts'),str(root/'DLLs')]+remaining);env['CONDA_PREFIX']=str(root)
command=[str(root/'python.exe'),'code/search02/analyze.py','--experiment','experiments/EXP-20261027-006/analysis-02','--skill-scripts','C:/Users/PC/.codex/skills/nature-figure/scripts']
with (exp/'figure-render-v3.log').open('xb') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
record={'command':command,'exit_code':r.returncode,'python':str(root/'python.exe'),'numpy':'1.26.4','matplotlib':'3.10.9','runtime_change':'Existing conda environment; child PATH isolates base conda DLLs. No packages installed or changed.','original_verification_copy':str(out/'verification.json'),'original_render_attempts_preserved':True}
(exp/'plot-runtime.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record))
if r.returncode==0:shutil.copyfile(out/'results.md',exp/'results.md')
else:print((exp/'figure-render-v3.log').read_text(encoding='utf-8',errors='replace')[-2500:])
sys.exit(r.returncode)
