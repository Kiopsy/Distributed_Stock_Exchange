import os, shutil
import constants as c
from UI.client_application import db

def depersist():
    for folder_path in [c.LOG_DIR, c.PKL_DIR]:
        try:
            # Delete all the files and subdirectories inside the folder
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)

            # Delete the folder itself
            # shutil.rmtree(folder_path)

            print("Folders cleared successfully!")
        except OSError as e:
            print(f"Error: {folder_path} : {e.strerror}")

    try:
        db.execute("""DROP TABLE users;""")
        db.execute("""DROP TABLE transactions;""")
        print("Dropped tables!")
    except:
        print("Tables have already been dropped!")
       
if __name__ == "__main__":
    depersist()


