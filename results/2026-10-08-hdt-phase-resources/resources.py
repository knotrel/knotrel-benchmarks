"""Read macOS task counters for an owned diagnostic child (SDK proc_taskinfo)."""
import ctypes,os
class TaskInfo(ctypes.Structure):
 _fields_=[(n,ctypes.c_uint64) for n in ('virtual_size','resident_size','total_user','total_system','threads_user','threads_system')]+[(n,ctypes.c_int32) for n in ('policy','faults','pageins','cow_faults','messages_sent','messages_received','syscalls_mach','syscalls_unix','csw','threadnum','numrunning','priority')]
lib=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
lib.proc_pidinfo.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int];lib.proc_pidinfo.restype=ctypes.c_int
def snapshot(pid):
 info=TaskInfo();n=lib.proc_pidinfo(pid,4,0,ctypes.byref(info),ctypes.sizeof(info))
 if n!=ctypes.sizeof(info):raise OSError(ctypes.get_errno(),f'proc_pidinfo returned {n}, expected {ctypes.sizeof(info)}')
 return {k:getattr(info,k) for k,_ in info._fields_}

class Timebase(ctypes.Structure):
 _fields_=[('numer',ctypes.c_uint32),('denom',ctypes.c_uint32)]
system=ctypes.CDLL('/usr/lib/libSystem.B.dylib');system.mach_timebase_info.argtypes=[ctypes.POINTER(Timebase)];system.mach_timebase_info.restype=ctypes.c_int
base=Timebase();assert system.mach_timebase_info(ctypes.byref(base))==0 and base.denom
TIMEBASE={'numer':base.numer,'denom':base.denom}
def cpu_ns(raw_ticks):return raw_ticks*base.numer/base.denom
