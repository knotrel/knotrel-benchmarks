import sys,os,json,hashlib,subprocess,pathlib,shutil
sys.path.insert(0,str(pathlib.Path.cwd()/'scripts'))
from run_baseline import hashes,command,CORE
variant=sys.argv[1];out=pathlib.Path('/private/tmp/knotrel-hdt-joins')
env={k:v for k,v in os.environ.items() if k.startswith(('RUST','CARGO_'))}
args=['cargo','build','--release','--locked','--bin','knotrel-benchmarks']
subprocess.run(args,check=True)
binary=pathlib.Path('target/release/knotrel-benchmarks');shutil.copy2(binary,out/variant)
(out/(variant+'.json')).write_text(json.dumps(dict(source_sha256=hashes(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),core_revision=command(['git','rev-parse','HEAD'],CORE),benchmarks_revision=command(['git','rev-parse','HEAD']),build_command=args,build_environment=env),indent=2)+'\n')
