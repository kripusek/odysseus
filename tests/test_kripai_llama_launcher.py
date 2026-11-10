from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import time

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "kripai_llama_launcher.py"
spec = importlib.util.spec_from_file_location("kripai_llama_launcher", PATH)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_gpu_idle_fails_closed(monkeypatch):
    class Result:
        stdout = ""
    def check(*args, **kwargs):
        r = Result()
        r.stdout = 'explorer\n' if 'powershell.exe' in args[0][0] else '5000\n'
        return r
    monkeypatch.setattr(launcher.subprocess, "run", check)
    assert launcher.gpu_idle()
    def busy(*args, **kwargs):
        r = check(*args, **kwargs)
        if 'powershell.exe' in args[0][0]: r.stdout = 'cs2\n'
        return r
    monkeypatch.setattr(launcher.subprocess, "run", busy)
    assert not launcher.gpu_idle()
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "nvidia-smi")
    monkeypatch.setattr(launcher.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        launcher.gpu_idle()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object")
def test_job_kills_child_when_parent_is_terminated(tmp_path):
    pidfile = tmp_path / "child.pid"
    # The child uses no GPU. The launcher receives a real Windows process and Job Object.
    child = f"import os,time; open({str(pidfile)!r},'w').write(str(os.getpid())); time.sleep(120)"
    driver = f'''import importlib.util,subprocess,sys
s=importlib.util.spec_from_file_location("launcher",{str(PATH)!r})
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
original=subprocess.list2cmdline
m.subprocess.list2cmdline=lambda args: original([sys.executable,"-c",{child!r}])
m._run_in_job(__import__("ctypes").WinDLL("kernel32",use_last_error=True),__import__("pathlib").Path(sys.executable),__import__("pathlib").Path(sys.executable),__import__("pathlib").Path(sys.executable))
'''
    parent = subprocess.Popen([sys.executable, "-c", driver], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pid = None
    try:
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text():
                pid = int(pidfile.read_text()); break
            assert parent.poll() is None, "launcher exited before child started"
            time.sleep(.1)
        assert pid is not None
        parent.kill(); parent.wait(timeout=10)
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if handle:
            try:
                assert kernel.WaitForSingleObject(handle, 10000) == 0
            finally:
                kernel.CloseHandle(handle)
    finally:
        if parent.poll() is None:
            parent.kill(); parent.wait(timeout=10)
