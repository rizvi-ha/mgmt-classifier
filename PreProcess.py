#This file takes in a pathlist of .nii,gz and makes them coregistered
# to the t1, and skull stripped

import os
import subprocess
import pandas as pd
from tqdm import tqdm
import time

dataset_all = pd.read_csv('pathlist.csv', usecols=[1,2,3,4])
dataset_all.head()
t1 = dataset_all['t1']
t1c = dataset_all['t1c']
t2 = dataset_all['t2']
flair = dataset_all['flair']

#if running on local machine
def convert_paths(pathlist):
    newlist = [p.replace('/trials', '/shares/trials') for p in pathlist]
    return newlist

t1 = convert_paths(t1)
t1c = convert_paths(t1c)
t2 = convert_paths(t2)
flair = convert_paths(flair)

def find_parent_folder(file_path):
    result = file_path
    leftover = ""
    while result[-1] != '/':
        leftover = result[-1] + leftover
        result = result[:-1]
    return result, leftover


def process_image(file_path, atlas_path):
    
    parent_folder, filename = find_parent_folder(file_path)
    file_path = parent_folder + '_bet/' + filename
    coreg_output = file_path.replace('special','final')

    if os.path.isfile(coreg_output):
        print('Already done!')
        return
    
    coreg_command = ['flirt -in ' + file_path + ' -ref ' + atlas_path + ' -out ' + coreg_output + ' -bins 128 -cost normmi -searchrx -45 45 -searchry -45 45 -searchrz -45 45 -dof 6  -interp trilinear' ]

    try:
        subprocess.run(coreg_command, shell=True, timeout=400, capture_output = True)
    except:
        print(coreg_output + ' failed. Continuing')
        return

    return
    
def skull_strip_batch(folder_path):

    if os.path.isdir(folder_path + "_bet/"):
        print("Skull stripping already done.")
        return
    
    bet_command = ["hd-bet -i " + folder_path + " -mode fast -tta 0 -s 0"]
    subprocess.run(bet_command, shell=True, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
    return

def process_patient(t1_path, t1c_path, t2_path, flair_path, patientno):

    t1_output = t1_path.replace('.nii.gz', '.special.nii.gz')
    parent_folder0, filename0 = find_parent_folder(t1_output)
    t1_target = parent_folder0 + "reg/" + filename0
    
    t1c_output = t1c_path.replace('.nii.gz', '.special.nii.gz')
    parent_folder1, filename1 = find_parent_folder(t1c_output)
    t1c_target = parent_folder1 + "reg/" + filename1

    t2_output = t2_path.replace('.nii.gz', '.special.nii.gz')
    parent_folder2, filename2 = find_parent_folder(t2_output)
    t2_target = parent_folder2 + "reg/" + filename2

    flair_output = flair_path.replace('.nii.gz', '.special.nii.gz')
    parent_folder3, filename3 = find_parent_folder(flair_output)
    flair_target = parent_folder3 + "reg/" + filename3

    assert(parent_folder1 == parent_folder2)
    assert(parent_folder2 == parent_folder0)

    if not os.path.isdir(parent_folder1 + "reg/"):
        mkdir_command = ["mkdir " + parent_folder1 + "reg/"]
        subprocess.run(mkdir_command, shell=True)

    cp_command0 = ["cp " + t1_path + " " + t1_target]
    cp_command1 = ["cp " + t1c_path + " " + t1c_target]
    cp_command2 = ["cp " + t2_path + " " + t2_target]
    cp_command3 = ["cp " + flair_path + " " + flair_target]

    subprocess.run(cp_command0, shell=True)
    subprocess.run(cp_command1, shell=True)
    subprocess.run(cp_command2, shell=True)
    subprocess.run(cp_command3, shell=True)

    print('Skull stripping patient#: ' + str(patientno))
    start = time.time()
    skull_strip_batch(parent_folder1 + "reg/")
    end = time.time()
    print("Took " + str(end-start) + " seconds to skull strip")

    template_folder, template_filename = find_parent_folder(t1_target)
    template = template_folder + "_bet/" + template_filename

    print('Registering t1c#: ' + str(patientno))
    start = time.time()
    process_image(t1c_target, template)
    end = time.time()
    print("Took " + str(end-start) + " seconds to register t1c #: " + str(patientno))

    print('Registering t2#: ' + str(patientno))
    start = time.time()
    process_image(t2_target, template)
    end = time.time()
    print("Took " + str(end-start) + " seconds to register t2 #: " + str(patientno))

    print('Registering flair#: ' + str(patientno))
    start = time.time()
    process_image(flair_target, template)
    end = time.time()
    print("Took " + str(end-start) + " seconds to register flair #: " + str(patientno))

    return
    

paths = zip(t1, t1c, t2, flair)
patientno = 1

for t1_path, t1c_path, t2_path, flair_path in zip(tqdm(t1), t1c, t2, flair):
    process_patient(t1_path, t1c_path, t2_path, flair_path, patientno)
    patientno += 1
