from typing import Union

import numpy as np
from google.oauth2 import service_account
import pandas as pd
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from ezgoogleapi.common.validation import check_keyfile, check_range, request_wrapper
import math

from ezgoogleapi.sheets.ranges import _get_ranges, _get_columns


def create_conn(keyfile):
    creds = service_account.Credentials.from_service_account_file(
        keyfile, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    creds.refresh(Request())

    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()


# TODO: separate results
# TODO: query by filter (df.loc[])
# TODO: new tab
# TODO: dynamic columns based on ranges
# columns = list(string.ascii_uppercase) + [c+d for c in string.ascii_uppercase for d in string.ascii_uppercase]

class Sheet:
    def __init__(self, keyfile: str):
        self.service = create_conn(check_keyfile(keyfile))
        self.sheet_id = None

    def set_sheet_id(self, sheet_id: str):
        self.sheet_id = sheet_id
        print(f'{self.sheet_id} set as sheet ID')

    @request_wrapper('sheets')
    def read(self, cell_range: str, tab: str = None, return_format='df', header_range: str = None,
             headers: list = None) -> Union[list[list], pd.DataFrame]:
        cell_range = check_range(cell_range, tab, self.sheet_id)
        if header_range:
            header_range = check_range(header_range, tab, self.sheet_id)
            results = self.service.values().get(spreadsheetId=self.sheet_id,
                                                     range=header_range).execute()
            headers = results['values'][0]
        results = self.service.values().get(spreadsheetId=self.sheet_id,
                                                 range=cell_range).execute()

        all_rows = results['values']

        if return_format == 'list':
            return all_rows
        else:
            index, columns = _get_ranges(cell_range)
            if not headers:
                headers = columns
                if not headers:
                    headers = _get_columns(width=len(all_rows[0]))

            data = [row for row in all_rows if row != headers]

            if index is None:
                return pd.DataFrame(columns=headers, data=data)
            elif type(index) == int:
                index = np.arange(index, index + len(all_rows) + 1)
            diff = len(all_rows) - len(data)
            if diff > 0:
                index = index[diff:]

            return pd.DataFrame(index=index, columns=headers, data=data)

    @request_wrapper('sheets')
    def append(self, data: Union[list, pd.DataFrame], cell_range: str, tab: str = None,
               per_request: int = 10000) -> dict:
        cell_range = check_range(cell_range, tab, self.sheet_id)

        if isinstance(data, pd.DataFrame):
            data = data.values.tolist()
        elif type(data) == list:
            if type(data[0]) != list:
                data = [data]
        else:
            raise TypeError(f'Type {type(data)} is not supported for writing to Google Sheets. \n'
                            f'Use lists or pandas DataFrame to append rows.')

        for x in range(0, math.ceil(len(data) / per_request)):
            if x == math.ceil(len(data) / per_request) - 1:
                data = data[0 + (x * per_request):]
            else:
                data = data[0 + (x * per_request): per_request + (x * per_request)]

            response = self.service.values().append(
                spreadsheetId=self.sheet_id,
                valueInputOption='RAW',
                range=cell_range,
                body=dict(
                    majorDimension='ROWS',
                    values=data
                )
            ).execute()

            return response

    @request_wrapper('sheets')
    def clear(self, cell_range: Union[str, list], tab: str = None) -> dict:
        cell_range = check_range(cell_range, tab, self.sheet_id)
        response = self.service.values().clear(spreadsheetId=self.sheet_id, range=cell_range).execute()
        return response

    def update(self):
        pass

    def copy(self):
        pass

    def read_by_filter(self, cell_range, condition, tab=None):
        pass

    def create_sheet(self, title: str) -> str:
        config = {
            'properties': {
                'title': title
            }
        }
        spreadsheet = self.service.create(body=config, fields='spreadsheetId').execute()
        print(f'Spreadsheet created with name {title} and ID {spreadsheet["spreadsheetId"]}')
        return spreadsheet['spreadsheetId']


if __name__ == '__main__':
    k = r'C:\Users\p290157\PycharmProjects\ezgoogleapi\gold-totem-285615-7a83b4a2d2e8.json'

    sheet = Sheet(k)
    SHEET_ID = '1ujWe0uAHPESFUA3qoi_LvJzrwJUhHXnqmqUdZWYvd8c'
    RANGE = 'A1:G15'
    sheet.set_sheet_id(SHEET_ID)
    # print(sheet.append(['a' for a in range(7)], RANGE, tab='Sheet1'))
    a = sheet.read(RANGE, tab='Sheet1', header_range='A1:G1')
    print('yeet')
