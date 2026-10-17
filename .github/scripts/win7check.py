"""Contrôle de la version Windows 7 : aucune DLL / .pyd embarquée ne doit appeler
une fonction apparue avec Windows 8 ou plus récent (sinon l'exe ne démarre pas sous Windows 7).
Usage : python win7check.py build/HFImage/Analysis-00.toc"""
import os
import re
import sys

import pefile

W8 = {"GetSystemTimePreciseAsFileTime", "CreateFile2", "GetCurrentThreadStackLimits", "SetThreadInformation",
      "GetThreadInformation", "GetProcessMitigationPolicy", "SetProcessMitigationPolicy", "WaitOnAddress",
      "WakeByAddressAll", "WakeByAddressSingle", "GetOverlappedResultEx", "CopyFile2", "PrefetchVirtualMemory",
      "DiscardVirtualMemory", "OfferVirtualMemory", "ReclaimVirtualMemory", "GetFirmwareType", "GetPackageFamilyName",
      "GetCurrentPackageId", "GetCurrentPackageFullName", "CreateFileMappingFromApp", "MapViewOfFileFromApp",
      "PathCchCombineEx", "PathCchCanonicalizeEx", "GetProcessInformation", "SetProcessInformation", "GetDpiForMonitor",
      "SetProcessDpiAwareness", "GetDpiForWindow", "SetThreadDescription", "GetThreadDescription", "VirtualAlloc2",
      "MapViewOfFile3", "GetDpiForSystem", "SetProcessDpiAwarenessContext", "CreateMemoryResourceNotification2"}
BAD_DLL = re.compile(r"api-ms-win-core-path|api-ms-win-core-synch-l1-2|api-ms-win-core-.*-l1-2-[1-9]")

toc = open(sys.argv[1], encoding="utf-8", errors="replace").read()
files = {re.sub(r"\\+", r"\\", p) for p in re.findall(r"'([A-Za-z]:\\[^']+?\.(?:dll|pyd|DLL|PYD))'", toc)}
files = [f for f in files if os.path.exists(f) and "\\windows\\system32\\" not in f.lower()]
bad = {}
for f in files:
    pe = pefile.PE(f, fast_load=True)
    pe.parse_data_directories([pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                               pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
    for attr in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
        for e in getattr(pe, attr, []):
            dll = e.dll.decode().lower()
            for imp in e.imports:
                n = (imp.name or b"").decode()
                if n in W8 or BAD_DLL.match(dll):
                    bad.setdefault(os.path.basename(f), set()).add(f"{dll}:{n}")
print(f"{len(files)} binaires analysés")
for k, v in sorted(bad.items()):
    print(f"::error::{k} : {', '.join(sorted(v))}")
sys.exit(1 if bad else 0)
