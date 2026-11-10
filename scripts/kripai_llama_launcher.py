"""Opcjonalny serwer modelu KripAI; uruchamiany wyłącznie na Windows."""
import ctypes
import csv
import io
import secrets
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys

PORT = 17012


def gpu_idle():
    """Zachowawczy zapas pamięci oraz kontrola znanych gier i serwerów modeli."""
    system = Path(os.environ["SystemRoot"]) / "System32"
    processes = subprocess.run(
        [str(system / "WindowsPowerShell" / "v1.0" / "powershell.exe"), "-NoProfile", "-NonInteractive", "-Command", "Get-Process | ForEach-Object { $_.ProcessName }"],
        capture_output=True, text=True, timeout=30, check=True,
    )
    blocked = {"cs2.exe", "csgo.exe", "llama-server.exe", "ollama.exe",
               "ollama_llama_server.exe", "lm studio.exe", "koboldcpp.exe"}
    names = {line.strip().lower() + ".exe" for line in processes.stdout.splitlines() if line.strip()}
    if names & blocked:
        return False
    result = subprocess.run(
        [str(system / "nvidia-smi.exe"), "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    # Jedna karta jest obsługiwana jawnie; brak danych nigdy nie oznacza wolnej GPU.
    return len(values) == 1 and values[0] >= 4096


def key_file(base):
    """Klucz przechowujemy w prywatnym katalogu danych, nigdy w argumentach."""
    folder = base / "Odysseus-kripusek-data" / "private-model"
    folder.mkdir(parents=True, exist_ok=True)
    system = Path(os.environ["SystemRoot"]) / "System32"
    who = subprocess.run([str(system / "whoami.exe"), "/user", "/fo", "csv", "/nh"],
                         capture_output=True, text=True, timeout=10, check=True)
    sid = next(csv.reader(io.StringIO(who.stdout)))[1]
    if not sid.startswith("S-1-"):
        raise RuntimeError("Nie można ustalić uprawnień katalogu klucza")
    subprocess.run([str(system / "icacls.exe"), str(folder), "/inheritance:r", "/grant:r",
                    f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-32-544:(OI)(CI)F"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
    path = folder / "llama-api-key.txt"
    try:
        with path.open("x", encoding="ascii") as f:
            f.write(secrets.token_urlsafe(32) + "\n")
    except FileExistsError:
        pass
    value = path.read_text(encoding="ascii").strip()
    if len(value) < 32 or "\n" in value or "\r" in value:
        raise RuntimeError("Nieprawidłowy plik klucza modelu")
    return path


def run():
    if os.name != "nt":
        raise RuntimeError("Wymagany Windows")
    base = Path(os.environ["LOCALAPPDATA"])
    exe = base / "KripAI" / "runtime" / "llama" / "llama-server.exe"
    model = base / "KripAI-data" / "models" / "model.gguf"
    if not exe.is_file() or not model.is_file():
        raise RuntimeError("Brak lokalnego serwera lub modelu KripAI")

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    k.CreateMutexW.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    mutex = k.CreateMutexW(None, True, "Local\\OdysseusKripusekLlama")
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        k.CloseHandle(mutex)
        raise RuntimeError("Launcher modelu już działa")
    try:
        if not gpu_idle():
            raise RuntimeError("GPU jest zajęty lub zgłasza aktywne procesy; start anulowany")
        _run_in_job(k, exe, model, key_file(base))
    finally:
        k.CloseHandle(mutex)


def _run_in_job(k, exe, model, key_path):
    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class BASIC_LIMIT(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                    ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BASIC_LIMIT), ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class STARTUPINFO(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
                    ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD),
                    ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.POINTER(ctypes.c_byte)), ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    k.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID,
                                 wintypes.BOOL, wintypes.DWORD, wintypes.LPVOID, wintypes.LPCWSTR,
                                 ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESS_INFORMATION)]
    k.ResumeThread.argtypes = [wintypes.HANDLE]
    k.ResumeThread.restype = wintypes.DWORD
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    job = k.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    pi = PROCESS_INFORMATION()
    assigned = False
    try:
        limits = EXTENDED_LIMIT()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not k.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        args = [str(exe), "-m", str(model), "--host", "127.0.0.1", "--port", str(PORT), "-ngl", "12", "-c", "2048", "--api-key-file", str(key_path)]
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
        startup = STARTUPINFO(); startup.cb = ctypes.sizeof(startup)
        # CREATE_SUSPENDED eliminuje wyścig między startem a dołączeniem do Job Object.
        if not k.CreateProcessW(str(exe), command, None, None, False, 0x4 | 0x08000000, None, str(exe.parent), ctypes.byref(startup), ctypes.byref(pi)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not k.AssignProcessToJobObject(job, pi.hProcess):
            raise ctypes.WinError(ctypes.get_last_error())
        assigned = True
        if k.ResumeThread(pi.hThread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        print(f"Serwer modelu: http://127.0.0.1:{PORT}/v1 (Ctrl+C kończy)", flush=True)
        # Częste oczekiwanie pozwala Pythonowi odebrać Ctrl+C.
        while True:
            result = k.WaitForSingleObject(pi.hProcess, 500)
            if result == 0:
                break
            if result != 0x102:
                raise ctypes.WinError(ctypes.get_last_error())
        code = wintypes.DWORD()
        k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        if not k.GetExitCodeProcess(pi.hProcess, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        if code.value:
            raise RuntimeError(f"Serwer zakończył pracę kodem {code.value}")
    finally:
        if pi.hProcess and not assigned:
            k.TerminateProcess(pi.hProcess, 1)
        k.CloseHandle(job)
        if pi.hThread:
            k.CloseHandle(pi.hThread)
        if pi.hProcess:
            k.CloseHandle(pi.hProcess)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("Zatrzymano serwer modelu.")
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Nie uruchomiono modelu: {exc}", file=sys.stderr)
        sys.exit(1)
