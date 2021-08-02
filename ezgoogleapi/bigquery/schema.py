from typing import List
import pandas as pd


class SchemaTypes:
    '''
    Class to easily assign a data type to a BigQuery-table column.
    '''
    INT64 = 'INT64'
    BOOL = 'BOOL'
    FLOAT64 = 'FLOAT64'
    STRING = 'STRING'
    OBJECT = 'STRING'
    BYTES = 'BYTES'
    TIMESTAMP = 'TIMESTAMP'
    DATE = 'DATE'
    TIME = 'TIME'
    DATETIME = 'DATETIME'
    DATETIME64 = 'DATETIME'
    TIMEDELTA = 'DATETIME'
    INTERVAL = 'INTERVAL'
    GEOGRAPHY = 'GEOGRAPHY'
    NUMERIC = 'NUMERIC'
    BIGNUMERIC = 'BIGNUMERIC'
    JSON = 'JSON'


def schema(df: pd.DataFrame) -> List[list]:
    '''
    Create a BigQuery table schema based on the data types of a pandas DataFrame.

    :param df: pandas DataFrame to base the schema on.
    :return: List of column names and data types.
    '''
    columns = df.columns.to_list()
    types = [f.name for f in list(df.dtypes.values)]

    return_schema = []
    for i, _ in enumerate(types):
        if _.replace('[ns]', '').upper() in SchemaTypes.__dict__.keys():
            return_schema.append([columns[i], SchemaTypes.__dict__[_.replace('[ns]', '').upper()]])
        else:
            return_schema.append([columns[i], SchemaTypes.STRING])

    return return_schema







