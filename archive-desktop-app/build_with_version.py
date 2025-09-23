import re
import sys
import subprocess

# 1. Read version from pdf_filler_gui.py
with open("pdf_filler_gui.py", encoding="utf-8") as f:
    content = f.read()
match = re.search(r'VERSION\s*=\s*[\'\"]([^\'\"]+)[\'\"]', content)
if not match:
    print("Could not find VERSION in pdf_filler_gui.py")
    sys.exit(1)
version = match.group(1)

# 2. Update the name in pdf_filler.spec to always use underscores
app_base_name = "PDF_Form_Filler"
safe_version = version.replace(' ', '_')
new_name = f"name='{app_base_name}_v{safe_version}',"
spec_pattern = r"name\s*=\s*['\"][^'\"]*['\"],"
with open("pdf_filler.spec", encoding="utf-8") as f:
    spec = f.read()
spec = re.sub(spec_pattern, new_name, spec)

with open("pdf_filler.spec", "w", encoding="utf-8") as f:
    f.write(spec)

# 3. Run PyInstaller
subprocess.run(["pyinstaller", "pdf_filler.spec"], check=True) 