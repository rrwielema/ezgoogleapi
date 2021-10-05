import json
import re

import pandas as pd
import validators
from googleapiclient.errors import HttpError
from ezgoogleapi.common.exceptions import InvalidKeyFileError, InvalidRangeError, NotAuthorizedError
import os


def check_keyfile(keyfile):
    if '.json' not in keyfile:
        raise IOError('Keyfile needs to be in .json format. Read more about the keyfile: '
                      'https://developers.google.com/identity/protocols/oauth2')
    try:
        file = open(keyfile, 'r')
    except FileNotFoundError:
        raise FileNotFoundError('Keyfile not found. Make sure it is located in the working directory and use only '
                                '"file_name.json" to specify.')

    headers = json.loads(file.read())
    mandatory_headers = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'auth_uri',
                         'token_uri']
    missing = [header for header in mandatory_headers if header not in headers]
    if len(missing) > 0:
        raise InvalidKeyFileError(
            f'{keyfile} is not a valid keyfile as it misses at least 1 mandatory headers: {", ".join(missing)}. '
            f'Make sure to provide a keyfile containing: {", ".join(mandatory_headers)}')
    else:
        return keyfile


def check_range(cell_range, tab, sheet_id):
    if not re.match(r'[A-z]{1,2}[0-9]{,7}:[A-z]{1,2}[0-9]{,7}', cell_range):
        raise InvalidRangeError(f'{cell_range} is not a valid range. It should follow the format "A:F" or '
                                f'"A1:F1000"')
    if tab:
        cell_range = f"'{tab}'!" + cell_range

    if not sheet_id:
        raise UserWarning('No sheet ID was set using sheet.set_sheet_id(your_sheet_id).')

    return cell_range


def request_wrapper(module):
    def decorator(request):
        def sheet_handling(*args, **kwargs):
            try:
                return request(*args, **kwargs)
            except HttpError as err:
                if err.status_code == 400:
                    raise InvalidRangeError(f'{kwargs["cell_range"]} does not exist.')
                elif err.status_code == 403:
                    raise NotAuthorizedError(f'No access to sheet. \n'
                                             f'1. Make sure the Sheets and Drive API are activated in the Google '
                                             f'Console. See: https://support.google.com/googleapi/answer/6158841?hl=en\n'
                                             f'2. Make sure to add the service account email in the JSON keyfile'
                                             f' to the sheet\n\n.'
                                             f'Full error: {err}')
            except KeyError:
                raise InvalidRangeError(f'No values found for range {kwargs["cell_range"]}. Range may be empty.')
        if module == 'sheets':
            return sheet_handling
    return decorator


def validate_email(email):
    if validators.email(email):
        return email
    else:
        raise ValueError(f'{email} is not a valid email address.')


def validate_json_file(file):
    match = re.fullmatch(r'.*\.json$', file)
    if not match:
        raise IOError(f'{file} is not a valid JSON file. Insert a valid JSON file or use a dictionary.')
    if not os.path.exists(file):
        raise IOError(f'File {file} does not exist. If it should exist, try using the absolute file path.')
    return file


def check_data_to_write(data):
    if isinstance(data, pd.DataFrame):
        data = data.values.tolist()
    elif type(data) == list:
        if type(data[0]) != list:
            data = [data]
    else:
        raise TypeError(f'Type {type(data)} is not supported for writing to Google Sheets. \n'
                        f'Use lists or pandas DataFrame to append rows.')
    return data
