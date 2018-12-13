import requests
import tempfile
import json


def get_existing_fitbit(oh_member):
    fitbit_files = {}
    for dfile in oh_member.list_files():
        if 'Fitbit Intraday' in dfile['metadata']['tags']:
            # get file here and read the json into memory
            fitbit_files[dfile['basename'][16:23]] = dfile
    print("----")
    print(fitbit_files)
    print("----")
    if fitbit_files:
        filenames = list(fitbit_files.keys())
        filenames.sort()
        print("----")
        print(fitbit_files)
        print("----")
        last_file = fitbit_files[filenames[-1]]
        tf_in = tempfile.NamedTemporaryFile(suffix='.json')
        tf_in.write(requests.get(last_file['download_url']).content)
        tf_in.flush()
        fitbit_data = json.load(open(tf_in.name))
        print("fetched existing data from OH")
        # print(fitbit_data)
        return fitbit_data, last_file['id'], filenames[-1]
    fitbit_data = {}
    return fitbit_data, None, None
