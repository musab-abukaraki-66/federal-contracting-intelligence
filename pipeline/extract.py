import os as _os
PROJECT_ROOT = _os.environ.get("P06_ROOT", r"<PROJECT_ROOT>")
SCRATCH      = _os.environ.get("P06_SCRATCH", r"<SCRATCH>")


import zipfile, shutil, os, time, sys
SRC = PROJECT_ROOT + r"\01_Raw_Data\award_data_archive\FY2025_All_Contracts_Full_20260906.zip"
DST = SCRATCH + r"\csv"
z = zipfile.ZipFile(SRC)
for i in z.infolist():
    out = os.path.join(DST, i.filename)
    if os.path.exists(out) and os.path.getsize(out) == i.file_size:
        print("skip", i.filename, flush=True); continue
    t0 = time.time()
    with z.open(i) as f, open(out, "wb") as o:
        shutil.copyfileobj(f, o, 1024*1024*8)
    print(f"done {i.filename} {i.file_size/1048576:.0f} MB in {time.time()-t0:.0f}s", flush=True)
print("EXTRACT COMPLETE", flush=True)
