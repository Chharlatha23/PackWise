import os
import glob

def fix_imports():
    app_dir = os.path.join("backend", "app")
    files = glob.glob(os.path.join(app_dir, "**", "*.py"), recursive=True)
    
    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        new_content = content.replace("from backend.app.", "from app.")
        new_content = new_content.replace("import backend.app.", "import app.")
        
        if content != new_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Fixed {filepath}")

if __name__ == "__main__":
    fix_imports()
