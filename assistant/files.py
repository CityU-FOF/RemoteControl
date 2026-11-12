"""Read-only OS handles. Never authorize by a textual prefix."""
import contextlib, os, stat
from pathlib import Path, PurePosixPath

class Denied(OSError): pass

def parts(relative):
    if not isinstance(relative, str) or len(relative) > 4096 or any(c in relative for c in ('\\', ':', '\x00')):
        raise Denied('非法路徑')
    if relative.startswith('/'):
        raise Denied('非法路徑')
    bits = relative.split('/') if relative else []
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in bits):
        raise Denied('非法路徑')
    if any(p.split('.')[0].upper() in {'CON','PRN','AUX','NUL', *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))} for p in bits):
        raise Denied('非法路徑')
    return bits

def identity(root, st):
    if str(st.st_dev) != root.device or str(st.st_ino) != root.inode:
        raise Denied('資料夾已更換，請本機重新設定')

@contextlib.contextmanager
def opened(root, relative='', directory=False):
    bits = parts(relative)
    if os.name == 'nt':
        with windows_open(root, bits, directory) as value: yield value
        return
    fds = []
    try:
        fd = os.open(root.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fds.append(fd)
        identity(root, os.fstat(fd))
        for i, part in enumerate(bits):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if i < len(bits)-1 or directory: flags |= os.O_DIRECTORY
            fd = os.open(part, flags, dir_fd=fd)
            fds.append(fd)
        st = os.fstat(fd)
        if directory and not stat.S_ISDIR(st.st_mode) or not directory and not stat.S_ISREG(st.st_mode):
            raise Denied('不支援此檔案類型')
        yield fd
    finally:
        for fd in reversed(fds): os.close(fd)

@contextlib.contextmanager
def windows_open(root, bits, directory):
    # Pin EVERY ancestor without FILE_SHARE_WRITE or FILE_SHARE_DELETE, reject all reparse points.
    # This prevents a junction/rename race between validation and enumeration.
    import ctypes, msvcrt
    from ctypes import wintypes as w
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateFileW.argtypes = [w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE]
    k.CreateFileW.restype = w.HANDLE
    k.CloseHandle.argtypes = [w.HANDLE]
    k.GetFileInformationByHandleEx.argtypes = [w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD]
    class Tag(ctypes.Structure): _fields_ = [('attrs',w.DWORD),('tag',w.DWORD)]
    path = Path(root.path)
    if not path.is_absolute(): raise Denied('需要絕對路徑')
    handles = []
    fd = None
    try:
        current = Path(path.anchor)
        all_parts = list(path.parts[1:]) + bits
        # Opening the drive/share root also pins its identity.
        for i, part in enumerate([''] + all_parts):
            if part: current /= part
            h = k.CreateFileW(str(current), 0x80000000, 0x1, None, 3, 0x02000000 | 0x00200000, None)
            if h == w.HANDLE(-1).value: raise ctypes.WinError(ctypes.get_last_error())
            handles.append(h)
            tag = Tag()
            if not k.GetFileInformationByHandleEx(h, 9, ctypes.byref(tag), ctypes.sizeof(tag)):
                raise ctypes.WinError(ctypes.get_last_error())
            if tag.attrs & 0x400: raise Denied('不允許符號連結、junction 或其他 reparse point')
            if i == len(path.parts)-1:
                identity(root, os.stat(current, follow_symlinks=False))
        isdir = bool(tag.attrs & 0x10)
        if isdir != directory: raise Denied('檔案類型不符')
        if directory:
            yield str(current)
        else:
            fd = msvcrt.open_osfhandle(handles.pop(), os.O_RDONLY | os.O_BINARY)
            if not stat.S_ISREG(os.fstat(fd).st_mode): raise Denied('不支援此檔案')
            yield fd
    finally:
        if fd is not None: os.close(fd)
        for h in reversed(handles): k.CloseHandle(h)

def entries(root, relative):
    with opened(root, relative, directory=True) as directory:
        with os.scandir(directory) as scan:
            for entry in scan:
                try:
                    st = entry.stat(follow_symlinks=False)
                    if entry.is_symlink() or getattr(st, 'st_file_attributes', 0) & 0x400: continue
                    if not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)): continue
                    parts(entry.name)
                    yield {'name': entry.name, 'path': '/'.join(filter(None, [relative, entry.name])), 'folder': relative, 'directory': stat.S_ISDIR(st.st_mode), 'size': st.st_size, 'modified': st.st_mtime}
                except OSError:
                    continue
