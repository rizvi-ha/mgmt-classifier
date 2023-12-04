#This file takes in a pathlist of .nii,gz and makes them coregistered,
# resampled, and skull stripped

import os
import subprocess
import pandas as pd
from tqdm import tqdm
import time

dataset_all = pd.read_csv('pathlist.csv', usecols=[1,2,3,4])
dataset_all.head()
t1c = dataset_all['t1c']
t2 = dataset_all['t2']
flair = dataset_all['flair']

#if running on local machine
def convert_paths(pathlist):
    newlist = [p.replace('/trials', '/shares/trials') for p in pathlist]
    return newlist


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
    
    coreg_command = ['flirt -in ' + file_path + ' -ref ' + atlas_path + ' -out ' + coreg_output + ' -bins 256 -cost normmi -searchrx -180 180 -searchry -180 180 -searchrz -180 180 -dof 12  -interp trilinear' ]
    coreg_command2 = ['flirt -in ' + coreg_output + ' -ref ' + coreg_output + ' -out ' + coreg_output + ' -applyisoxfm 1']

    try:
        subprocess.run(coreg_command, shell=True, timeout=400, capture_output = True)
        subprocess.run(coreg_command2, shell=True, timeout=300)
    except:
        print(coreg_output + ' failed. Continuing')
        return

    runn = True
    starttryremove = time.time()
    clean_command = ["rm " + file_path + " " + parent_folder + filename]

    while (runn):
        try: 
            subprocess.run(clean_command)
            runn = False
        except:
            if (time.time() - starttryremove) > 2:
                print("couldnt clean up")
                return
            continue

    print(coreg_output)
    return
    
def skull_strip_batch(folder_path):

    if os.path.isdir(folder_path + "_bet/"):
        print("Skull stripping already done.")
        return
    
    bet_command = ["hd-bet -i " + folder_path + " -device cpu -mode fast -tta 0 -s 0"]
    subprocess.run(bet_command, shell=True)
    print(folder_path)

    return

def process_patient(t1c_path, t2_path, flair_path, template, patientno):
    t1c_output = t1c_path.replace('.nii.gz', '.special.nii.gz')
    parent_folder1, filename1 = find_parent_folder(t1c_output)
    t1c_target = parent_folder1 + "proc/" + filename1

    t2_output = t2_path.replace('.nii.gz', '.special.nii.gz')
    parent_folder2, filename2 = find_parent_folder(t2_output)
    t2_target = parent_folder2 + "proc/" + filename2

    flair_output = flair_path.replace('.nii.gz', '.special.nii.gz')
    parent_folder3, filename3 = find_parent_folder(flair_output)
    flair_target = parent_folder3 + "proc/" + filename3

    assert(parent_folder1 == parent_folder2)
    assert(parent_folder2 == parent_folder3)

    if not os.path.isdir(parent_folder1 + "proc/"):
        mkdir_command = ["mkdir " + parent_folder1 + "proc/"]
        subprocess.run(mkdir_command, shell=True)

    cp_command1 = ["cp " + t1c_path + " " + t1c_target]
    cp_command2 = ["cp " + t2_path + " " + t2_target]
    cp_command3 = ["cp " + flair_path + " " + flair_target]

    subprocess.run(cp_command1, shell=True)
    subprocess.run(cp_command2, shell=True)
    subprocess.run(cp_command3, shell=True)

    print('Skull stripping patient#: ' + str(patientno))
    start = time.time()
    skull_strip_batch(parent_folder1 + "proc/")
    end = time.time()
    print("Took " + str(end-start) + " seconds to skull strip")
    
    start = time.time()
    process_image(t1c_target, template)
    end = time.time()
    print("Took " + str(end-start) + " seconds to register t1c #: " + str(patientno))

    start = time.time()
    process_image(t2_target, template)
    end = time.time()
    print("Took " + str(end-start) + " seconds to register t2 #: " + str(patientno))

    start = time.time()
    process_image(flair_target, template)
    end = time.time()
    print("Took " + str(end-start) + " seconds to register flair #: " + str(patientno))

    return
    

template = '/shares/trials/_BTIL-LIB_/01_Matlab_Scripts/2_Registration/baseanat2.nii.gz'

paths = zip(t1c, t2, flair)
patientno = 1

for t1c_path, t2_path, flair_path in zip(tqdm(t1c), t2, flair):
    process_patient(t1c_path, t2_path, flair_path, template, patientno)
    patientno += 1