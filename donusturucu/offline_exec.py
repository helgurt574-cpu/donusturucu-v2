"""Linux helper: install an inherited seccomp network filter, then exec once.
Run in a fresh Python process, never as a multithreaded preexec_fn.
Local AF_UNIX IPC (office/fonts) remains available. No root/user namespace needed.
"""
import ctypes,errno,os,socket,sys

def restrict_network():
    lib=None
    # Portable bundles ship their own copy; distributions without libseccomp still get the filter.
    for name in [os.environ.get('DONUSTURUCU_LIBSECCOMP'),'libseccomp.so.2',os.path.join(sys.prefix,'lib','libseccomp.so.2')]:
        if not name:continue
        try:lib=ctypes.CDLL(name,use_errno=True);break
        except OSError:continue
    if lib is None:raise OSError('libseccomp.so.2 not found')
    lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_release.argtypes=[ctypes.c_void_p]
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    class Comparison(ctypes.Structure):
        _fields_=[('arg',ctypes.c_uint),('op',ctypes.c_uint),('datum_a',ctypes.c_uint64),('datum_b',ctypes.c_uint64)]
    lib.seccomp_rule_add_array.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint,ctypes.POINTER(Comparison)]
    lib.seccomp_rule_add_array.restype=ctypes.c_int
    lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_load.restype=ctypes.c_int
    ctx=lib.seccomp_init(0x7fff0000) # SCMP_ACT_ALLOW
    if not ctx:raise OSError('seccomp_init failed')
    try:
        # SCMP_CMP_NE: only local Unix sockets may be created. Other families
        # cannot obtain a socket descriptor, including IPv4, IPv6 and packet.
        condition=Comparison(0,1,socket.AF_UNIX,0)
        for syscall in [b'socket',b'socketpair']:
            number=lib.seccomp_syscall_resolve_name(syscall)
            if number<0:raise OSError('Unknown syscall: '+syscall.decode())
            if lib.seccomp_rule_add_array(ctx,0x50000|errno.EPERM,number,1,ctypes.byref(condition))!=0:raise OSError('Could not add network rule')
        if lib.seccomp_load(ctx)!=0:raise OSError('Could not load seccomp filter')
    finally:lib.seccomp_release(ctx)

def main():
    try:
        restrict_network()
        if sys.argv[1:]==['--probe']:
            local=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);local.close()
            for family in [socket.AF_INET,socket.AF_INET6]:
                try:network=socket.socket(family,socket.SOCK_STREAM)
                except OSError as exc:
                    if exc.errno!=errno.EPERM:raise
                else:network.close();raise RuntimeError('Network filter did not block socket')
            return 0
        if len(sys.argv)<2:raise ValueError('Missing command')
        os.execvpe(sys.argv[1],sys.argv[1:],os.environ)
    except Exception as exc:
        print('Local offline execution failed: '+str(exc),file=sys.stderr);return 125
if __name__=='__main__':raise SystemExit(main())
