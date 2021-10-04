import json
import pathlib
import string
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, List, Callable
import sqlite3 as db
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
import os
from ezgoogleapi.analytics.variable_names import VariableName
from ezgoogleapi.common.exceptions import SamplingError

BASE_DIR = os.getcwd()
DIR = str(pathlib.Path(__file__).parent)
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']


def initialize_analyticsreporting(keyfile) -> Any:
    credentials = Credentials.from_service_account_file(keyfile, scopes=SCOPES)
    analytics = build('analyticsreporting', 'v4', credentials=credentials)
    return analytics

# TODO: socket timeout op requests afvangen
class Query:
    def __init__(self, body, keyfile: str, clean_up: Callable = None):
        '''
        Class to run queries for a given Body object.

        :param body: ezgoogleapi.analytics.Body object
        :param keyfile: JSON keyfile name in the form "file_name.json".
        '''
        self.analytics = initialize_analyticsreporting(keyfile)
        self.body = body
        self.resource_quota = self.body.resource_quota
        self.date_range = calc_range(*body.date_range)
        self.name_client = VariableName()
        self.sampling_report = []
        self.results = []
        self.clean_up_func = clean_up

    def run(self, per_day=True, sampling='fail', clean_headers=False, logging=True):
        '''
        Execute API requests for given body and given date range. Saves result to Query.results,
        which can be exported to csv, dataframe and sqlite.

        :param logging: Enable or disble prints
        :param clean_headers: [optional] Specify whether to use the Google Ananlytics variable name e.g. Device
            Category or the API code ga:deviceCategory
        :param per_day: Default True.
            Execute queries per day. Reduces chance of sampling.
        :param sampling: Default 'fail'.
            Specify what to do when sampled results are encountered. Options: 'fail' (generate error), 'skip'
            (do not generate error), 'save' (save the record as normal, and include column with sample percentage).
        '''

        if per_day:
            for date in self.date_range:
                body = self.body.body
                body['reportRequests'][0]['dateRanges'] = [{'startDate': date, 'endDate': date}]
                result = get_report(json.dumps(body), self.analytics, self.resource_quota, sampling)
                if logging:
                    print(f'Result for date {date} contains {len(result)} rows')
                if clean_headers:
                    result.columns = self.name_client.get_names(list(result.columns), return_type='name')
                if self.clean_up_func:
                    result = self.clean_up_func(result)
                self.results.append(result)
                with db.connect('partial_results.db') as conn:
                    try:
                        result.to_sql('results', con=conn, index=False, if_exists='append')
                    except db.OperationalError:
                        pass
                        # TODO: toevoegen error handling

                conn.close()
                time.sleep(0.5)
            os.remove('partial_results.db')

        else:
            body = self.body.body
            body['reportRequests'][0]['dateRanges'] = [
                {'startDate': self.body.date_range[0], 'endDate': self.body.date_range[1]}]
            result = get_report(body, self.analytics, self.resource_quota, sampling)
            if clean_headers:
                result.columns = self.name_client.get_names(list(result.columns), return_type='name')
            if self.clean_up_func:
                result = self.clean_up_func(result)
            self.results.append(result)

    def to_csv(self, path):
        '''
        Save query results to a CSV file. Headers containing Google Analytics API codes will be replaced by
        their regular variable name.

        :param path: Relative or absolute path to the yet-to-be created CSV file.

        >> Query.to_csv('example.csv')

        >> Query.to_csv('C:/Users/someusr/Documents/example.csv')
        '''
        if not os.path.isabs(path):
            path = BASE_DIR + '\\' + path
        df = pd.concat(self.results)
        df.columns = self.name_client.get_names(list(df.columns.values), return_type='name')
        df.to_csv(path, index=False)
        print(f'CSV created: {path}')

    def to_sqlite(self, headers: list = None, db_name: str = None, table_name='results'):
        '''
        Save query results to a SQLite database. Headers containing Google Analytics API codes will be replaced by
        their regular variable name. Any special characters or spaces will be replaced by an underscore.

        :param table_name: [optional] Defaults to 'results'
        :param headers: [optional] Specify custom headers for the columns.
        :param db_name: [optional] Specify a name for the database. If not specified, then the query name from the
            Body object will be used. If that also isn't specified, it will fall back to Query [num], depending on the
            amount of Body instances. Ex. Query 0 for the first one.
        '''
        if not os.path.exists(f'{BASE_DIR}\\Query results'):
            os.mkdir(f'{BASE_DIR}\\Query results')
        if not db_name:
            db_name = self.body.name
        conn = db.connect(f'{BASE_DIR}\\Query results\\' + db_name)

        df = pd.concat(self.results)
        if headers:
            cols = df.columns
            if len(cols) == len(headers):
                df.columns = headers
            elif len(cols) < len(headers):
                raise ValueError(f'Too many headers ({len(headers)}) specified for the amount of '
                                 f'columns ({len(cols)}). Cannot write to SQLite.')
            else:
                raise ValueError(
                    f'Too few headers ({len(headers)}) specified for the amount of columns ({len(cols)}).'
                    f' Cannot write to SQLite.')
        else:
            df.columns = self.name_client.get_names(list(df.columns.values), return_type='name')

        clean_cols = []
        for col in df.columns:
            if type(col) == str:
                new_col = ''
                for char in col:
                    if char in string.punctuation or char == ' ':
                        new_col += '_'
                    else:
                        new_col += char
                clean_cols.append(new_col)
            else:
                clean_cols.append(col)

        df.columns = clean_cols

        df.to_sql(table_name, conn, index=False, if_exists='replace')
        conn.close()
        print(f'New SQLite DB created with path {BASE_DIR}\\Query results\\{db_name}.db, using \'{table_name}\' as '
              f'the table name and {", ".join(clean_cols)} as columns.')

    def to_dataframe(self) -> pd.DataFrame:
        '''
        Return the query results as a pandas DataFrame for data manipulation and analysis.
        '''
        df = pd.concat(self.results)
        df.columns = self.name_client.get_names(list(df.columns.values), return_type='name')
        return df


@lru_cache
def get_report(body: str, analytics: Any, resource_quota: bool, sampling: str) -> pd.DataFrame:
    page_token = True
    body = json.loads(body)
    date = body['reportRequests'][0]['dateRanges'][0]['startDate']
    results = []
    while page_token:
        response = analytics.reports().batchGet(body=body).execute()
        for k, v in response.items():
            for report in v:
                dim_headers = report['columnHeader']['dimensions']
                met_headers = [f['name'] for f in report['columnHeader']['metricHeader']['metricHeaderEntries']]
                report_data = report['data']

                try:
                    rows = report_data['rows']
                except KeyError:
                    results.append(pd.DataFrame())
                    continue
                data = [row['dimensions'] + row['metrics'][0]['values'] for row in rows]
                headers = dim_headers + met_headers
                df_sub = pd.DataFrame(data=data, columns=headers)

                if 'SamplingReadCounts' in report_data.keys():
                    sample_size = int(body['samplesReadCounts'][0]) / int(body['samplingSpaceSizes'][0])
                    if resource_quota and 'useResourceQuotas' not in list(body.keys()):
                        body['useResourceQuotas'] = True
                        return get_report(json.dumps(body), analytics, resource_quota, sampling)
                    elif sampling == 'save':
                        df_sub['Sampling'] = sample_size
                        percentage = round(sample_size * 100, 1)
                        print(f'{date} contains sampled data: {percentage}%')
                    elif sampling == 'fail':
                        if os.path.exists(DIR + '\\partial_results.db'):
                            conn = db.connect(DIR + '\\partial_results.db')
                            df = pd.read_sql('SELECT * FROM results', conn)
                            df.to_csv(BASE_DIR + '\\partial_results.csv', index=False)
                            conn.close()
                            os.remove('partial_results.db')
                            csv = True
                        else:
                            csv = False
                        raise SamplingError(sample_size, csv)
                    else:
                        """skip"""
                        results.append(pd.DataFrame())
                        print(f'{date} contains sampled data and will not be available in the results')
                        continue

                results.append(df_sub)

                if 'nextPageToken' in report.keys():
                    body['reportRequests'][0]['pageToken'] = report['nextPageToken']
                    continue
                else:
                    page_token = False

    return pd.concat(results)


def calc_range(start, end) -> List[str]:
    if type(start) == str and type(end) == str:
        start = datetime.strptime(start, '%Y-%m-%d')
        end = datetime.strptime(end, '%Y-%m-%d')

    if start == end:
        return [datetime.strftime(start, '%Y-%m-%d')]
    delta = end - start
    if delta.days < 0:
        delta = start - end
    return [datetime.strftime(end - timedelta(days=day), '%Y-%m-%d') for day in range(delta.days + 1)][::-1]



