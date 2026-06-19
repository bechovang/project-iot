import os
import shutil

sound_dir = r"C:\Users\Admin\Desktop\GIT CLONE\IOT-project\project iot\test MAX98357A loa\sound"
data_dir = r"C:\Users\Admin\Desktop\GIT CLONE\IOT-project\project iot\test MAX98357A loa\data"

# Clear data directory
if os.path.exists(data_dir):
    shutil.rmtree(data_dir)
os.makedirs(data_dir)

# File mapping
mapping = {
    "ba.mp3": "ba.mp3",
    "bảy.mp3": "bay.mp3",
    "bốn.mp3": "bon.mp3",
    "chín.mp3": "chin.mp3",
    "hai.mp3": "hai.mp3",
    "mươi.mp3": "muoi.mp3",
    "mười.mp3": "muoi_10.mp3",
    "một.mp3": "mot.mp3",
    "nghìn đồng.mp3": "nghin_dong.mp3",
    "năm.mp3": "nam.mp3",
    "sáu.mp3": "sau.mp3",
    "tám.mp3": "tam.mp3",
    "đã nhận được.mp3": "da_nhan_duoc.mp3"
}

for src_name, dest_name in mapping.items():
    src_path = os.path.join(sound_dir, src_name)
    dest_path = os.path.join(data_dir, dest_name)
    if os.path.exists(src_path):
        shutil.copy2(src_path, dest_path)
        print("Copied successfully.")
    else:
        print("Warning: file not found!")
