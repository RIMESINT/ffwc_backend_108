
from collections import OrderedDict
import decimal
import pandas
from django.db import connection
import os
import imghdr
import base64
import time 
from django.conf import settings
from django.core.files.storage import FileSystemStorage










def document_upload(datafile, file_name, file_folder):
    """
        Upload file
        Args:
            datafile (str): uploaded file object
            file_name (str): uplaod file name
            file_folder (str): destination folder
        Returns:
            str: Uploaded file path
    """

    file_name = file_name.replace(' ', '_')
    user_path_filename = os.path.join(settings.MEDIA_ROOT, file_folder)
    if not os.path.exists(user_path_filename):
        os.makedirs(user_path_filename)
    fs = FileSystemStorage(location=user_path_filename)

    file_extension = datafile.name.split(".")
    myfile_name = str(int(round(time.time() * 1000))) + "." + str(file_extension[-1])
    # myfile_name = str(int(round(time.time() * 1000))) + "_" + str(datafile.name) #+ str(file_name) + "_" 
    filename = fs.save(myfile_name, datafile)
    full_file_path = myfile_name   #"media/" + file_folder + "/" + myfile_name

    return full_file_path



"""
    Various types of document upload like json, video, image and many more
"""
class DocumentUpload:
    def level_wise_shapefile_upload(datafile, file_name, file_folder):
        """
            Upload file
            Args:
                datafile (str): uploaded file object
                file_name (str): uplaod file name
                file_folder (str): destination folder
            Returns:
                str: Uploaded file path
        """

        file_name = file_name.split('.')
        file_name = file_name[0:(len(file_name)-1)]
        file_name = ''.join(file_name)
        file_name = file_name.replace(' ', '_')
        user_path_filename = os.path.join(settings.MEDIA_ROOT, file_folder)

        # if os.path.exists(user_path_filename):
        #     os.remove(user_path_filename)

        if not os.path.exists(user_path_filename):
            os.makedirs(user_path_filename)
        
        fs = FileSystemStorage(location=user_path_filename)

        myfile_name = str(int(round(time.time() * 1000))) + "_" + str(datafile.name)
        filename = fs.save(myfile_name, datafile)
        full_file_path = myfile_name   

        # return [full_file_path, myfile_name]
        return full_file_path