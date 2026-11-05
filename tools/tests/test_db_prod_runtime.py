"""Runtime bundles are prepared only in temporary private directories."""
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import unittest
import fcntl
import plistlib
import socket
import subprocess
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class RuntimeTests(unittest.TestCase):
    def temporary_bundle(self):
        from db_prod_runtime import build_bundle
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        self.addCleanup(temp.cleanup)
        bundle = build_bundle(Path(__file__).resolve().parents[1],root/'runtime')
        self.addCleanup(lambda:bundle.chmod(0o700))
        return root,bundle

    def test_bundle_remains_valid_after_development_source_changes(self):
        from db_prod_runtime import build_bundle, verify_bundle
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'source'; source.mkdir()
            tools = Path(__file__).resolve().parents[1]
            for name in ['db_query_control.py','db_prod_keychain.swift']+[p.name for p in tools.glob('db_prod_*.py')]:
                shutil.copyfile(tools/name, source/name)
            bundle = build_bundle(source, root/'runtime')
            before = verify_bundle(bundle)
            (source/'db_prod_gateway.py').write_text('# a later development change\n')
            self.assertEqual(verify_bundle(bundle), before)
            self.assertIn('detached_jobs', before['capabilities'])
            self.assertEqual(bundle.stat().st_mode & 0o777, 0o500)
            for p in bundle.iterdir(): self.assertEqual(p.stat().st_mode & 0o777, 0o400)
            # Restore owner write permission so tempdir cleanup works on macOS.
            bundle.chmod(0o700)

    def test_modified_payload_or_permissions_are_refused(self):
        from db_prod_runtime import verify_bundle
        from db_query_control import Denied
        root,bundle=self.temporary_bundle()
        payload=bundle/'db_prod_client.py'
        payload.chmod(0o600)
        with self.assertRaises(Denied): verify_bundle(bundle)
        payload.write_text('# changed\n'); payload.chmod(0o400)
        with self.assertRaises(Denied): verify_bundle(bundle)

    def test_activation_requires_stopped_halted_idle_and_compatible_schema(self):
        from db_prod_runtime import activate_bundle
        from db_query_control import Store,Denied
        root,bundle=self.temporary_bundle()
        state=root/'state'; Store.initialize(state/'control.sqlite3')
        with (state/'gateway.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(Denied): activate_bundle(root/'runtime',bundle,state)
        store=Store(state/'control.sqlite3')
        store.clear(store.status(), resume=True)
        with self.assertRaises(Denied): activate_bundle(root/'runtime',bundle,state)
        store.stop('operator_stop')
        with store.transaction() as c:
            c.execute("UPDATE control SET active='fixture-run',phase='unconfirmed' WHERE id=1")
        with self.assertRaises(Denied): activate_bundle(root/'runtime',bundle,state)
        with store.transaction() as c:
            c.execute("UPDATE control SET active=NULL,phase='idle' WHERE id=1")
        activate_bundle(root/'runtime',bundle,state)
        self.assertEqual((root/'runtime/current').resolve(),bundle.resolve())
        self.assertTrue(store.status()['halted'])
        with store.transaction() as c:
            c.execute('CREATE TABLE query_job_schema(version INTEGER)');c.execute('INSERT INTO query_job_schema VALUES (99)')
        with self.assertRaises(Denied): activate_bundle(root/'runtime',bundle,state)
        self.assertEqual((root/'runtime/current').resolve(),bundle.resolve())

    def test_launchagent_and_isolated_cli_use_selected_bundle(self):
        from db_prod_runtime import launch_agent
        root,bundle=self.temporary_bundle()
        plist=plistlib.loads(launch_agent(root/'runtime'))
        self.assertEqual(plist['ProgramArguments'][1:],['-I',str(root/'runtime/current/db_prod_gateway.py'),'serve'])
        proc=subprocess.run([sys.executable,'-I',str(bundle/'db_prod_client.py'),'--help'],capture_output=True,text=True,timeout=5)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn('job-status',proc.stdout)
        self.assertFalse((root/'runtime/current').exists())

    def test_bundled_gateway_boots_halted_without_credentials_or_database(self):
        from db_query_control import Store
        root,bundle=self.temporary_bundle()
        state=root/'state';Store.initialize(state/'control.sqlite3')
        (state/'config.json').write_text(json.dumps(dict(allowed_uids=[os.getuid()],targets={})))
        sock=Path('/tmp')/('q3-'+root.name+'.sock')
        code="""import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import db_prod_gateway as g
g.STATE=Path(sys.argv[2]);g.SOCKET=Path(sys.argv[3])
g.serve()
"""
        child=subprocess.Popen([sys.executable,'-I','-c',code,str(bundle),str(state),str(sock)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+5
            while not sock.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(sock.exists(),'gateway did not boot')
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                client.settimeout(2);client.connect(str(sock));client.sendall(b'{"action":"status"}\n')
                data=bytearray()
                while not data.endswith(b'\n'):data.extend(client.recv(65536))
            status=json.loads(data)
            self.assertTrue(status['halted']);self.assertIsNone(status['active'])
            self.assertIn('durable_ack',status['capabilities'])
            self.assertFalse((state/'db-prod-keychain').exists())
        finally:
            child.terminate()
            try:out,err=child.communicate(timeout=5)
            except subprocess.TimeoutExpired:child.kill();out,err=child.communicate()
            sock.unlink(missing_ok=True)
        self.assertEqual(child.returncode,0,err.decode(errors='replace'))


if __name__ == '__main__':
    unittest.main()
