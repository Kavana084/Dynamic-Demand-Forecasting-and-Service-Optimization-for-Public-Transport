import shutil
import os

# Check disk usage for C: and F:
c_total, c_used, c_free = shutil.disk_usage("C:\\")
f_total, f_used, f_free = shutil.disk_usage("F:\\")

print(f"C: Free: {c_free // (2**30)} GB / {c_total // (2**30)} GB")
print(f"F: Free: {f_free // (2**30)} GB / {f_total // (2**30)} GB")

def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                except Exception:
                    pass
    return total_size

print(f"npm cache size: {get_size('C:\\Users\\kavan\\AppData\\Local\\npm-cache') // (2**20)} MB")
