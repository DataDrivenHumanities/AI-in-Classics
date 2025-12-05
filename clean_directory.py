import os
import re

def remove_non_matching_files(directory_path):
    """
    Removes files in the specified directory that do NOT match the given regex pattern.

    Args:
        directory_path (str): The path to the directory to process.
    """
    removed_files = 0
    removed_file_names = []
    # check to make sure it is xml else go to next file
    for filename in os.listdir(directory_path):
        if not re.fullmatch(".*\.xml", filename):
            continue
        if not re.search("-grc.*\.xml", filename):
            os.remove(directory_path + "/" + filename)
            removed_files += 1
            removed_file_names.append(filename)
    return removed_files, removed_file_names

if __name__=="__main__":
    directory = "./original_xml"
    if directory == "./original_xml/script_test":
        number, names = remove_non_matching_files(directory)
        print(f"{directory} parsing complete. Files removed: {number}. File names: {names}")
    else:
        for d in os.walk(directory):
            sub = d[0]
            number, names = remove_non_matching_files(sub)
            print(f"{sub} parsing complete. Files removed: {number}. File names: {names}")
    print("Cleaning of non-Greek XML files is complete.")