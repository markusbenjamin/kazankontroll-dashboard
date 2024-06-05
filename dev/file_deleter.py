import os

def delete_files_with_specific_name(root_dir, target_filename):
    """
    Iterate through the folder tree and delete all files with the specific name.

    Parameters:
    root_dir (str): The root directory to start the search.
    target_filename (str): The name of the files to delete.
    """
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename == target_filename:
                file_path = os.path.join(dirpath, filename)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

# Example usage
root_directory = 'C:/Users/Beno/Documents/SZAKI/dev/kazankontroll-dashboard/data/raw'
file_to_delete = 'heatmeter_belief_state_net.csv'
delete_files_with_specific_name(root_directory, file_to_delete)
