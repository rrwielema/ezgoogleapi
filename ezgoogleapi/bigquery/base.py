import math
import warnings
from typing import Union
import pandas as pd
from google.cloud import bigquery
import os
from ezgoogleapi.common.validation import check_keyfile


BASE_DIR = os.getcwd()


class BigQuery:
    def __init__(self, keyfile: str):
        if not os.path.isabs(keyfile):
            keyfile = BASE_DIR + '\\' + keyfile
        self.keyfile = check_keyfile(keyfile)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = keyfile
        self.client = bigquery.Client()
        self.table = None
        self.table_name = None

    def set_table(self, table):
        if not check_table_format(table):
            raise ValueError(f'{table} is not a valid BigQuery table name. It should follow the format '
                             f'Project.Dataset.TableName.')
        else:
            self.table = table
            self.table_name = table.split('.')[2]

    def create_table(self, schema: list):
        sch = []
        for field in schema:
            if type(field) == list:
                sch.append(bigquery.SchemaField(field[0], field[1]))
            else:
                sch.append(bigquery.SchemaField(field, "STRING"))

        new_table = bigquery.Table(self.table, schema=sch)
        self.client.create_table(new_table)
        print(f'Created table {self.table_name}')

    def delete_table(self, sure: bool = False):
        check_table(self.table)
        if not sure:
            raise UserWarning(
                f'If you are sure you want to delete {self.table_name}, pass the sure=True option for the '
                f'delete_table() function. There is no way to recover the table once it has been deleted.')
        else:
            self.client.delete_table(self.table, not_found_ok=True)
            print(f'Table {self.table} was deleted')

    def delete_rows(self, condition: str = None, sure: bool = False):
        check_table(self.table)
        if not condition and not sure:
            raise UserWarning(f'Running delete_records() without a condition deletes every row in '
                              f'table {self.table_name}. If you are sure you want this, pass the sure=True parameter. '
                              f'Otherwise, provide a condition.')

        query = f'DELETE FROM {self.table}'
        if condition:
            query += ' WHERE ' + condition

        query_job = self.client.query(query)
        if not query_job:
            print('Rows deleted')

    def insert_rows(self, data: Union[list, dict, pd.DataFrame], per_request: int = 10000):
        if per_request > 10000 or per_request < 0 or type(per_request) != int:
            warnings.warn('Invalid entry. The per_request parameter is between 0 and 10000. Value will be set to 10000',
                          UserWarning)
            per_request = 10000

        check_table(self.table)
        if type(data) != pd.DataFrame:
            if type(data[0]) == dict:
                df = pd.DataFrame(data)
            elif type(data[0]) == list:
                columns = data[0]
                values = data[1:]
                df = pd.DataFrame(columns=columns, data=values)
            else:
                raise TypeError(
                    'Data is not specified in the correct format. It needs to be either:\n\n'
                    ' - a pandas DataFrame\n'
                    ' - a list containing dictionaries with the same keys in each dictionary\n'
                    ' - a list containing lists where the first list represents the headers and the following contain '
                    'the data '
                )
        else:
            df = data

        to_write = df.to_dict('records')
        for x in range(0, math.ceil(len(to_write) / per_request)):
            if x == math.ceil(len(to_write) / per_request) - 1:
                insert = to_write[0 + (x * per_request):]
            else:
                insert = to_write[0 + (x * per_request): per_request + (x * per_request)]

            errors = self.client.insert_rows_json(self.table, insert)
            if not errors:
                print(f"{len(insert)} rows added to table {self.table_name}")
            else:
                print(f"Error: {errors}")

    def read_table(self, columns: Union[list, str] = None, condition=None, return_format='df'):
        check_table(self.table)
        if columns:
            if type(columns) == list:
                query = f'SELECT {", ".join(columns)} FROM {self.table}'
            elif type(columns) == str:
                query = f'SELECT {columns} FROM {self.table}'
            else:
                raise ValueError(f'Incorrect data type \'{type(columns)}\' for parameter \'columns\'. Supply either '
                                 f'\'str\' or \'list\'')
        else:
            query = f'SELECT * FROM {self.table}'

        if condition:
            query += ' WHERE ' + condition

        query_job = self.client.query(query)

        result = query_job.result()

        result_rows = []
        for row in result:
            row_values = dict(zip(list(row.keys()), list(row.values())))
            result_rows.append(row_values)

        if return_format == 'list':
            return [f.values() for f in result_rows]
        elif return_format == 'dict':
            return result_rows
        elif return_format == 'df':
            return pd.DataFrame(result_rows)
        else:
            warnings.warn(
                f"Format {return_format} is not valid. There will be data returned in the form of a pd.DataFrame.\n"
                f"The valid formats are:\n\n"
                f"'df' - Returns pandas DataFrame (default).\n"
                f"'dict' - Returns list of dictionaries.\n"
                f"'list' - Returns list of lists containing the rows. Headers will be lost."
            )


def check_table_format(table):
    return len(table.split('.')) == 3


def check_table(table):
    if not table:
        raise UserWarning(
            'No table was specified via the BigQuery.set_table("Project.database.table") method.'
        )

