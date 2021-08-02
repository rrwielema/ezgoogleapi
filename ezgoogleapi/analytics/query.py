import string
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, List
import sqlite3 as db
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
import os
from ezgoogleapi.analytics.variable_names import VariableName

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']


def initialize_analyticsreporting(keyfile) -> Any:
    credentials = Credentials.from_service_account_file(keyfile, scopes=SCOPES)
    analytics = build('analyticsreporting', 'v4', credentials=credentials)
    return analytics


class Query:
    def __init__(self, body, keyfile):
        '''
        Class to contain all bodies for a data range given a Body object.

        :param body: Body object
        :param keyfile: JSON keyfile name in the form "file_name.json".
        '''
        self.analytics = initialize_analyticsreporting(keyfile)
        self.body = body
        self.resource_quota = self.body.resource_quota
        self.date_range = calc_range(*body.date_range)
        self.name_client = VariableName()
        self.sampling_report = []  # TODO: implement
        self.results = []

    def run_query(self, per_day=True, sampling='fail'):
        '''
        Execute API requests for given body and given date range. Saves result to Query.results,
        which can be exported to csv, dataframe and sqlite.

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
                result = get_report(body, self.analytics, self.resource_quota, sampling)
                self.results.append(result)
                conn = db.connect('partial_results.db')
                df = pd.concat(self.results)
                df.to_sql('results', con=conn, index=False, if_exists='append')

        else:
            body = self.body.body
            body['reportRequests'][0]['dateRanges'] = [
                {'startDate': self.body.date_range[0], 'endDate': self.body.date_range[1]}]
            result = get_report(body, self.analytics, self.resource_quota, sampling)
            self.results.append(result)

    def to_csv(self, path):
        '''
        Save query results to a CSV file. Headers containing Google Analytics API codes will be replaced by
        their regular variable name.

        :param path: Relative or absolute path to the yet-to-be created CSV file.

        >>> Query.to_csv('example.csv')

        >>> Query.to_csv(r'C:\Users\someusr\Documents\example.csv')
        '''
        if not os.path.exists('Query results'):
            os.mkdir('Query results')
        df = pd.concat(self.results)
        df.columns = self.name_client.get_names(list(df.columns.values), return_type='name')
        df.to_csv(path, index=False)

    def to_sqlite(self, headers: list = None, name: str = None):
        '''
        Save query results to a SQLite database. Headers containing Google Analytics API codes will be replaced by
        their regular variable name.

        :param headers: [optional] Specify custom headers for the columns.
        :param name: [optional] Specify a name for the database. If not specified, then the query name from the
            Body object will be used.
        '''
        if not os.path.exists(f'{BASE_DIR}\\Query results'):
            os.mkdir(f'{BASE_DIR}\\Query results')
        if not name:
            conn = db.connect(f'{BASE_DIR}\\Query results\\' + self.body.name)
        else:
            conn = db.connect(f'{BASE_DIR}\\Query results\\' + name)

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

        df.to_sql('results', con=conn, index=False, if_exists='replace')
        conn.close()

    def to_dataframe(self) -> pd.DataFrame:
        '''
        Return the query results as a pandas DataFrame for data manipulation and analysis.
        '''
        df = pd.concat(self.results)
        df.columns = self.name_client.get_names(list(df.columns.values), return_type='name')
        return df


@lru_cache
def get_report(body, analytics, resource_quota, sampling) -> pd.DataFrame:
    results = []
    page_token = True
    while page_token:
        response = analytics.reports().batchGet(body=body).execute()
        for k, v in response.items():
            for report in v:
                dim_headers = report['columnHeader']['dimensions']
                met_headers = [f['name'] for f in report['columnHeader']['metricHeader']['metricHeaderEntries']]
                report_data = report['data']

                rows = report_data['rows']
                data = [row['dimensions'] + row['metrics'][0]['values'] for row in rows]
                headers = dim_headers + met_headers
                df_sub = pd.DataFrame(data=data, columns=headers)

                if 'SamplingReadCounts' in report_data.keys():
                    sample_size = int(body['samplesReadCounts'][0]) / int(body['samplingSpaceSizes'][0])
                    if resource_quota and not 'useResourceQuotas' in list(body.keys()):
                        body_rq = body['useResourceQuotas'] = True
                        return get_report(body_rq, analytics, resource_quota, sampling)
                    elif sampling == 'save':
                        df_sub['Sampling'] = sample_size
                    elif sampling == 'fail':
                        conn = db.connect('partial_results.db')
                        df = pd.read_sql('SELECT * FROM results')
                        df.to_csv(BASE_DIR + '\\partial_results.csv', index=False)
                        conn.close()
                        os.remove('partial_results.db')
                        raise SamplingError(sample_size)
                    else:
                        """skip"""
                        return pd.DataFrame()

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


class SamplingError(Exception):
    def __init__(self, percentage):
        self.percentage = round(percentage * 100, 1)
        self.message = f'Sampling detected in results ({self.percentage}%) and sampling is set to "fail"\n. ' \
                       f'Execution of queries is stopped and results untill now have been saved ' \
                       f'to {BASE_DIR + "/partial_results.csv"}. If you want to continue when sampling is ' \
                       f'encountered, then use the option sampling="skip" to only save results without sampling or ' \
                       f'sampling="save" to keep all the results.'
        super().__init__(self.message)
