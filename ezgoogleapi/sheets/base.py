from typing import Union
import numpy as np
from google.oauth2 import service_account
import pandas as pd
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from ezgoogleapi.common.validation import check_keyfile, check_range, request_wrapper, validate_email, \
    check_data_to_write
import math
from ezgoogleapi.sheets.ranges import _get_ranges, _get_columns


def create_conn_sheets(keyfile):
    creds = service_account.Credentials.from_service_account_file(
        keyfile, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    creds.refresh(Request())

    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()


def create_conn_drive(keyfile):
    creds = service_account.Credentials.from_service_account_file(
        keyfile, scopes=['https://www.googleapis.com/auth/drive'])
    creds.refresh(Request())

    service = build('drive', 'v3', credentials=creds)
    return service


class Permission:
    def __init__(self, email, role, group=False):
        self.emailAddress = validate_email(email)
        if role not in ['writer', 'reader', 'owner']:
            raise ValueError(f'{role} must be "owner", "reader" or "writer".')
        self.role = role
        self.type = 'user'
        if group:
            self.type = 'group'


class SpreadSheet:
    def __init__(self, keyfile: str):
        self.service = create_conn_sheets(check_keyfile(keyfile))
        self.sheet_id = None
        self.keyfile = keyfile

    def set_sheet_id(self, sheet_id: str):
        self.sheet_id = sheet_id

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
    def append(self, data: Union[list, pd.DataFrame], cell_range: str = None, tab: str = None,
               per_request: int = 10000) -> None:
        data = check_data_to_write(data)

        if cell_range:
            cell_range = check_range(cell_range, tab, self.sheet_id)
        else:
            range_ = _get_columns(width=len(data[0]))
            cell_range = check_range(f'{range_[0]}:{range_[-1]}', tab, self.sheet_id)

        written = 0
        for x in range(0, math.ceil(len(data) / per_request)):
            if x == math.ceil(len(data) / per_request) - 1:
                to_write = data[0 + (x * per_request):]
            else:
                to_write = data[0 + (x * per_request): per_request + (x * per_request)]

            response = self.service.values().append(
                spreadsheetId=self.sheet_id,
                valueInputOption='RAW',
                range=cell_range,
                body=dict(
                    majorDimension='ROWS',
                    values=to_write
                )
            ).execute()

            written += response['updates']['updatedRows']
            print(f'Rows appended: {written} / {len(to_write)}')

    @request_wrapper('sheets')
    def clear(self, cell_range: Union[str, list], tab: str = None) -> dict:
        cell_range = check_range(cell_range, tab, self.sheet_id)
        response = self.service.values().clear(spreadsheetId=self.sheet_id, range=cell_range).execute()
        return response

    def add_permissions(self, permission):
        drive = create_conn_drive(self.keyfile)
        if type(permission) != list:
            permission = [permission]
        for p in permission:
            if p.role == 'owner':
                drive.permissions().create(fileId=self.sheet_id, body=p.__dict__, fields='id',
                                           transferOwnership=True).execute()
            else:
                drive.permissions().create(fileId=self.sheet_id, body=p.__dict__, fields='id').execute()
            print(f'Added {p.role} permissions for {self.sheet_id} to {p.emailAddress}')

    def create(self, title: str, permissions: Union[list[Permission], Permission] = None):
        config = {
            'properties': {
                'title': title
            }
        }
        spreadsheet = self.service.create(body=config, fields='spreadsheetId').execute()
        self.sheet_id = spreadsheet['spreadsheetId']
        print(
            f'Spreadsheet created with name {title} and ID {self.sheet_id} - '
            f'https://docs.google.com/spreadsheets/d/{self.sheet_id}')

        if permissions:
            self.add_permissions(permissions)
