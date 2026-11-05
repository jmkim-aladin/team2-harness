#!/usr/bin/env python3
"""Build a private immutable runtime; activation is an explicit deployment action."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_prod_jobs import SCHEMA_VERSION
from db_query_control import Denied, Store

CAPABILITIES = ['detached_jobs', 'repeatable_fetch', 'durable_ack', 'csv_export']


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def _private(path, *, create=False):
    path = Path(path)
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Denied('untrusted_runtime_directory')
    return path


def _fsync(path):
    fd = os.open(path, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def verify_bundle(bundle):
    bundle = _private(bundle)
    manifest_path = bundle/'manifest.json'
    if manifest_path.is_symlink():
        raise Denied('runtime_manifest_untrusted')
    manifest = json.loads(manifest_path.read_text())
    if (set(manifest) != {'format','job_schema','capabilities','files'} or manifest['format'] != 1
            or manifest['job_schema'] != SCHEMA_VERSION or manifest['capabilities'] != CAPABILITIES
            or hashlib.sha256(_encoded(manifest)).hexdigest() != bundle.name):
        raise Denied('runtime_manifest_incompatible')
    if set(p.name for p in bundle.iterdir()) != set(manifest['files']) | {'manifest.json'}:
        raise Denied('runtime_files_changed')
    for name, expected in manifest['files'].items():
        if Path(name).name != name:
            raise Denied('runtime_path_invalid')
        path = bundle/name; info = path.lstat()
        if (path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o277 or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise Denied('runtime_files_changed')
    if bundle.stat().st_mode & 0o200 or manifest_path.stat().st_mode & 0o277:
        raise Denied('runtime_not_immutable')
    return manifest


def build_bundle(source, root):
    source, root = Path(source), _private(root, create=True)
    bundles = _private(root/'bundles', create=True)
    paths = sorted(source.glob('db_prod_*.py')) + [source/'db_query_control.py', source/'db_prod_keychain.swift']
    files = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise Denied('runtime_source_invalid')
        files[path.name] = path.read_bytes()
    required = {'db_prod_gateway.py','db_prod_client.py','db_prod_runtime.py','db_prod_jobs.py','db_prod_approval.py'}
    if not required <= set(files):
        raise Denied('runtime_source_incomplete')
    manifest = dict(format=1, job_schema=SCHEMA_VERSION, capabilities=CAPABILITIES,
                    files={name:hashlib.sha256(data).hexdigest() for name,data in files.items()})
    bundle = bundles/hashlib.sha256(_encoded(manifest)).hexdigest()
    if bundle.exists():
        verify_bundle(bundle)
        return bundle
    staging = Path(tempfile.mkdtemp(prefix='.staging-',dir=bundles))
    try:
        for name,data in dict(files, **{'manifest.json':_encoded(manifest)}).items():
            path = staging/name
            with path.open('xb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            path.chmod(0o400)
        _fsync(staging); staging.chmod(0o500)
        os.rename(staging,bundle); _fsync(bundles)
    except BaseException:
        if staging.exists():
            staging.chmod(0o700); shutil.rmtree(staging)
        raise
    verify_bundle(bundle)
    return bundle


def activate_bundle(root, bundle, state):
    """Caller explicitly deploys; a live gateway or uncertain slot rejects swap."""
    root, state = _private(root), _private(state)
    bundle = Path(bundle).absolute()
    if bundle.parent != root.absolute()/'bundles':
        raise Denied('runtime_outside_installation')
    verify_bundle(bundle)
    descriptor = os.open(state/'gateway.lock',os.O_WRONLY|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(descriptor,'a') as lock:
        if os.fstat(lock.fileno()).st_uid != os.getuid() or not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise Denied('runtime_lock_untrusted')
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise Denied('gateway_must_be_stopped') from None
        store = Store(state/'control.sqlite3')
        with store.transaction() as c:
            control = store._state(c)
            if control['active'] is not None or control['phase'] != 'idle' or not control['halted']:
                raise Denied('runtime_switch_requires_halted_idle')
            exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='query_job_schema'").fetchone()
            if exists and [r[0] for r in c.execute('SELECT version FROM query_job_schema')] != [SCHEMA_VERSION]:
                raise Denied('incompatible_job_schema')
            current = root/'current'
            if current.exists() and not current.is_symlink():
                raise Denied('runtime_selection_untrusted')
            temporary = root/('.current-'+os.urandom(8).hex())
            try:
                temporary.symlink_to(bundle.relative_to(root.absolute()))
                os.replace(temporary,current); _fsync(root)
            finally:
                temporary.unlink(missing_ok=True)
    return bundle


def launch_agent(root, python=sys.executable):
    root = Path(root).absolute()
    # Produce a reviewable plist only. Loading launchd is a separate deployment.
    return plistlib.dumps(dict(Label='kr.co.aladin.team2-db',
        ProgramArguments=[str(Path(python).resolve()),'-I',str(root/'current/db_prod_gateway.py'),'serve'],
        RunAtLoad=True, KeepAlive=True, ThrottleInterval=10, ProcessType='Background',
        EnvironmentVariables=dict(HOME=str(Path.home()),PATH='/usr/bin:/bin:/opt/homebrew/bin'),
        StandardOutPath='/dev/null',StandardErrorPath='/dev/null'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    build=sub.add_parser('build'); build.add_argument('--source',required=True); build.add_argument('--root',required=True)
    activate=sub.add_parser('activate'); activate.add_argument('--root',required=True); activate.add_argument('--bundle',required=True); activate.add_argument('--state',required=True)
    agent=sub.add_parser('launchagent'); agent.add_argument('--root',required=True)
    args=parser.parse_args()
    if args.action=='build': print(build_bundle(args.source,args.root))
    elif args.action=='activate': print(activate_bundle(args.root,args.bundle,args.state))
    else: sys.stdout.buffer.write(launch_agent(args.root))


if __name__=='__main__':
    try: main()
    except Exception:
        print('Runtime operation refused; installation unchanged or requires inspection.',file=sys.stderr)
        raise SystemExit(1)
