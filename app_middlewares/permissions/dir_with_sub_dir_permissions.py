import os
import pwd
import grp
from pathlib import Path








class DirectoryPermission:

    def recursive_chown_change_ownership(directory_path, user_name, group_name):
        """
        Recursively change ownership of a directory and its contents.
        
        Args:
            directory_path (str): Path to the target directory.
            user_name (str): Username to set as owner (e.g., 'rimes').
            group_name (str): Group name to set as group (e.g., 'ffwc').
            
        Requires:
            - Must be run with root privileges (sudo)
            - User and group must exist on the system
        """
        try:
            # Get numeric user/group IDs
            uid = pwd.getpwnam(user_name).pw_uid
            gid = grp.getgrnam(group_name).gr_gid
        except KeyError as e:
            raise ValueError(f"User/group not found: {e}") from None

        # Walk through directory tree
        for root, dirs, files in os.walk(directory_path):
            # Process current directory
            try:
                os.chown(root, uid, gid)
            except PermissionError as e:
                raise RuntimeError(f"Permission denied for {root}. Run with sudo!") from e
            
            # Process files in current directory
            for file in files:
                file_path = os.path.join(root, file)
                os.chown(file_path, uid, gid)

            # Directories in 'dirs' will be processed automatically by os.walk
            # as subsequent 'root' values
        print(f"Changed ownership for user: {user_name} and group: {group_name} successfully.")
        
            
    def directory_all_files_and_folder_permissions(directory_path, permission_mode): 
        directory_path = directory_path     # '/rimes_sesame_backend/static/'
        permission_mode = permission_mode   # 0o777

        # Change the permission of the directory and all its contents
        for root, dirs, files in os.walk(directory_path):
            # Change the permission of the directory itself
            os.chmod(root, permission_mode)
            # Change the permission of all subdirectories
            for dir in dirs:
                os.chmod(os.path.join(root, dir), permission_mode)
            # Change the permission of all files
            for file in files:
                os.chmod(os.path.join(root, file), permission_mode)
                
        print(f"Permissions for '{directory_path}' and all its contents have been set to 777.")

    def directory_all_files_and_folder_permissions_v2(directory_path, permission_mode, user_name): 
        """
            #################################################
            ### This function is for FFWC Server user
            #################################################
        """
        directory_path = directory_path     # '/rimes_sesame_backend/static/'
        permission_mode = permission_mode   # 0o777
        user_name = user_name               # 'sajib'

        # Get UID and GID for the user
        uid = pwd.getpwnam(user_name).pw_uid
        gid = grp.getgrnam(user_name).gr_gid
        # print("$$$$$$$$ user of uid: ", uid)
        # print("$$$$$$$$ user of gid: ", gid)

        # Change ownership and permission of the directory and all its contents
        for root, dirs, files in os.walk(directory_path):
            # Change ownership of the directory itself
            os.chown(root, uid, gid)
            os.chmod(root, permission_mode)
            
            # Change ownership and permission of all subdirectories
            for dir in dirs:
                os.chown(os.path.join(root, dir), uid, gid)
                os.chmod(os.path.join(root, dir), permission_mode)
            
            # Change ownership and permission of all files
            for file in files:
                os.chown(os.path.join(root, file), uid, gid)
                os.chmod(os.path.join(root, file), permission_mode)
                
        print(f"Ownership and permissions for '{directory_path}' and all its contents have been set to user '{user_name}' with mode {oct(permission_mode)}.")


    def directory_all_files_and_folder_permissions_v3(directory_path, permission_mode, user_name):
        for root, dirs, files in os.walk(directory_path):
            os.chmod(root, permission_mode)
            for dir in dirs:
                os.chmod(os.path.join(root, dir), permission_mode)
            for file in files:
                os.chmod(os.path.join(root, file), permission_mode)


    def directory_all_files_and_folder_permissions_v4(directory_path, permission_mode, user_name): 
        """
            #################################################
            ### This function is for FFWC Server user
            #################################################
        """
        directory_path = directory_path     # '/rimes_sesame_backend/static/'
        permission_mode = permission_mode   # 0o777
        user_name = user_name               # 'sajib'

        p = Path(directory_path) 
        p.chmod(permission_mode) 
        for child in p.rglob("*"):
            child.chmod(permission_mode)
                
        print(f"Ownership and permissions for '{directory_path}' and all its contents have been set to user '{user_name}' with mode {oct(permission_mode)}.")
