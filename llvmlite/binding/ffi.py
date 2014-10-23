import ctypes
import os
import sys

from .common import _decode_string, _is_shutting_down


def _make_opaque_ref(name):
    newcls = type(name, (ctypes.Structure,), {})
    return ctypes.POINTER(newcls)


LLVMContextRef = _make_opaque_ref("LLVMContext")
LLVMModuleRef = _make_opaque_ref("LLVMModule")
LLVMValueRef = _make_opaque_ref("LLVMValue")
LLVMTypeRef = _make_opaque_ref("LLVMType")
LLVMExecutionEngineRef = _make_opaque_ref("LLVMExecutionEngine")
LLVMPassManagerBuilderRef = _make_opaque_ref("LLVMPassManagerBuilder")
LLVMPassManagerRef = _make_opaque_ref("LLVMPassManager")
LLVMTargetDataRef = _make_opaque_ref("LLVMTargetData")
LLVMTargetLibraryInfoRef = _make_opaque_ref("LLVMTargetLibraryInfo")
LLVMTargetRef = _make_opaque_ref("LLVMTarget")
LLVMTargetMachineRef = _make_opaque_ref("LLVMTargetMachine")
LLVMMemoryBufferRef = _make_opaque_ref("LLVMMemoryBuffer")

ffi_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ffi')

if os.name == 'posix':
    if sys.platform == 'darwin':
        lib = ctypes.CDLL(os.path.join(ffi_dir, 'libllvmlite.dylib'))
    else:
        lib = ctypes.CDLL(os.path.join(ffi_dir, 'libllvmlite.so'))
else:
    assert os.name == 'nt'
    lib = ctypes.CDLL(os.path.join(ffi_dir, 'build', 'Release', 'llvmlite.dll'))


class _DeadPointer(object):
    """
    Dummy class to make error messages more helpful.
    """


class OutputString(object):
    """Object for managing output string memory
    """
    _as_parameter_ = _DeadPointer()

    def __init__(self, owned=True):
        self._ptr = ctypes.c_char_p(None)
        self._as_parameter_ = ctypes.byref(self._ptr)
        self._owned = owned

    def close(self):
        if self._ptr is not None:
            if self._owned:
                lib.LLVMPY_DisposeString(self._ptr)
            self._ptr = None
            del self._as_parameter_

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self, _is_shutting_down=_is_shutting_down):
        # Avoid errors trying to rely on globals and modules at interpreter
        # shutdown.
        if not _is_shutting_down():
            self.close()

    def __str__(self):
        if self._ptr is None:
            return "<dead OutputString>"
        s = self._ptr.value
        assert s is not None
        return _decode_string(s)

    def __bool__(self):
        return bool(self._ptr)

    __nonzero__ = __bool__


class ObjectRef(object):
    """Weak reference to LLVM objects
    """
    _closed = False
    _as_parameter_ = _DeadPointer()
    # Whether this object pointer is owned by another one.
    _owned = False

    def __init__(self, ptr):
        if ptr is None:
            raise ValueError("NULL pointer")
        self._ptr = ptr
        self._as_parameter_ = ptr

    def close(self):
        """
        Close this object and do any required clean-up actions.
        """
        try:
            if not self._closed and not self._owned:
                self._dispose()
        finally:
            self.detach()

    def detach(self):
        """
        Detach the underlying LLVM resource without disposing of it.
        """
        if not self._closed:
            del self._as_parameter_
            self._closed = True
            self._ptr = None

    def _dispose(self):
        """
        Dispose of the underlying LLVM resource.  Should be overriden
        by subclasses.
        """

    @property
    def closed(self):
        return self._closed

    def __enter__(self):
        assert hasattr(self, "close")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def __bool__(self):
        return bool(self._ptr)

    __nonzero__ = __bool__

    # XXX useful?
    def __hash__(self):
        return hash(ctypes.cast(self._ptr, ctypes.c_void_p).value)