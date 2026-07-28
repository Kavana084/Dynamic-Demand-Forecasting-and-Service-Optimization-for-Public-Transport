import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

def cleanup():
    print("--- Starting Cleanup Process ---")
    
    # 1. Remove models directory
    models_dir = os.path.join(BASE_DIR, "models")
    if os.path.exists(models_dir):
        shutil.rmtree(models_dir)
        print(f"✔ Deleted entire 'models' directory: {models_dir}")
    else:
        print(f"ℹ 'models' directory not found, skipping.")
        
    # 2. Remove old scripts
    lstm_script = os.path.join(BASE_DIR, "scripts", "lstm_dataset_builder.py")
    if os.path.exists(lstm_script):
        os.remove(lstm_script)
        print(f"✔ Deleted old script: {lstm_script}")
        
    # 3. Update requirements.txt
    req_file = os.path.join(BASE_DIR, "requirements.txt")
    if os.path.exists(req_file):
        with open(req_file, "r") as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            line = line.strip()
            # Remove tensorflow, keras
            if line and "tensorflow" not in line and "keras" not in line and "catboost" not in line and "apscheduler" not in line:
                new_lines.append(line)
                
        # Add new requirements
        new_lines.append("catboost==1.2.2")
        new_lines.append("APScheduler==3.10.4")
        
        # Write back
        with open(req_file, "w") as f:
            for line in sorted(new_lines):
                f.write(line + "\n")
        print(f"✔ Updated requirements.txt to remove tensorflow and add catboost, apscheduler")
        
    print("--- Cleanup Complete ---")

if __name__ == "__main__":
    cleanup()
