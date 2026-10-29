"""Keep regression UI preferences out of the user's actual configuration."""
import atexit,os,shutil,tempfile
_config=tempfile.mkdtemp(prefix='donusturucu-regression-config-')
os.environ['XDG_CONFIG_HOME']=_config
atexit.register(shutil.rmtree,_config,ignore_errors=True)
