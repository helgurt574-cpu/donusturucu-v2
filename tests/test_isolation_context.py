import subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from donusturucu import runtime,core
class IsolationContextTests(unittest.TestCase):
 def setUp(self):runtime._isolation_probe.cache_clear();runtime._seccomp_probe.cache_clear()
 def tearDown(self):runtime._isolation_probe.cache_clear();runtime._seccomp_probe.cache_clear()
 def test_denied_bwrap_runs_local_command(self):
  denied=subprocess.CompletedProcess([],1,b'bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted')
  with patch.object(runtime,'tool_path',side_effect=lambda n:'/usr/bin/bwrap' if n=='bwrap' else None),patch.object(runtime.subprocess,'run',return_value=denied),patch.object(runtime,'_seccomp_probe',return_value=(True,'')):
   self.assertIn('offline_exec.py',runtime.isolate(['/bin/true'])[1]);self.assertEqual(runtime.isolate(['/bin/true'])[-1],'/bin/true');self.assertEqual(runtime.isolation_status()['provider'],'seccomp')
 def test_allowed_bwrap_probe_cached(self):
  with patch.object(runtime,'tool_path',return_value='/usr/bin/bwrap'),patch.object(runtime.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'')) as probe:
   self.assertIn('--unshare-net',runtime.isolate(['/bin/true']));runtime.isolate(['/bin/true']);self.assertEqual(probe.call_count,1)
 def test_probe_timeout_falls_back(self):
  with patch.object(runtime,'tool_path',side_effect=lambda n:'/usr/bin/bwrap' if n=='bwrap' else None),patch.object(runtime.subprocess,'run',side_effect=subprocess.TimeoutExpired('bwrap',5)),patch.object(runtime,'_seccomp_probe',return_value=(True,'')):
   self.assertIn('offline_exec.py',runtime.isolate(['/bin/true'])[1])
 def test_real_command_failure_not_retried(self):
  import sys
  with tempfile.TemporaryDirectory() as tmp:
   marker=Path(tmp)/'once'
   with self.assertRaises(core.ConversionError):core.Runner().run([sys.executable,'-c',"from pathlib import Path; p=Path(__import__('sys').argv[1]); p.write_text(p.read_text()+'x' if p.exists() else 'x'); raise SystemExit(2)",str(marker)])
   self.assertEqual(marker.read_text(),'x')
 def test_missing_bwrap_uses_seccomp(self):
  with patch.object(runtime,'tool_path',return_value=None),patch.object(runtime,'_seccomp_probe',return_value=(True,'')):
   self.assertIn('offline_exec.py',runtime.isolate(['/bin/true'])[1])
 def test_no_working_network_filter_fails_closed(self):
  with patch.object(runtime,'tool_path',return_value=None),patch.object(runtime,'_seccomp_probe',return_value=(False,'denied')):
   with self.assertRaisesRegex(RuntimeError,'offline isolation unavailable'):runtime.isolate(['/bin/true'])
 def test_unix_sockets_allowed(self):
  import sys
  core.Runner().run([sys.executable,'-c',"import socket; s=socket.socket(socket.AF_UNIX); s.close()"])
 def test_offline_environment(self):
  env=runtime.process_env();self.assertEqual(env['HF_HUB_OFFLINE'],'1');self.assertEqual(env['TRANSFORMERS_OFFLINE'],'1')
if __name__=='__main__':unittest.main()
