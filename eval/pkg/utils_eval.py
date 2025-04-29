# %%
import os
import shutil


# This will help translate all .tofu files to .tf files.
def change_extension_and_copy(src_dir, dest_dir, old_ext, new_ext):
    for root, dirs, files in os.walk(src_dir):
        # Create the corresponding directory structure in the destination
        relative_path = os.path.relpath(root, src_dir)
        dest_path = os.path.join(dest_dir, relative_path)
        os.makedirs(dest_path, exist_ok=True)

        for file in files:
            if file.endswith(old_ext):
                # Create new file name with the new extension
                new_file_name = file.replace(old_ext, new_ext)
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest_path, new_file_name)

                # Copy the file to the new destination
                shutil.copy2(src_file_path, dest_file_path)
                print(f'Copied {src_file_path} to {dest_file_path}')
