import re
from typing import Union, List
import json
from urllib import request
import sqlite3 as db
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
from ezgoogleapi.bigquery.base import check_keyfile


class VariableName:
    def __init__(self):
        '''
        Class to instantiate a search object for variable names
        '''
        conn = db.connect('google_api_variable_names.db')
        self.all_names = pd.read_sql('SELECT * FROM vars', con=conn)
        conn.close()

        if len(self.all_names[self.all_names['type'] == 'Custom Dimension']) == 0 and \
                len(self.all_names[self.all_names['type'] == 'Custom Metric']) == 0:
            self.cd_cm = False
        else:
            self.cd_cm = True

    @staticmethod
    def create_database():
        '''
        Creates an SQLite database with the standard Google Analytics dimensions and metrics.
        The package will already have a database included.
        '''
        r = request.urlopen('https://rrwielema.github.io/page/apis/ga_vars.json')
        ga_vars = json.loads(r.read())['data']
        df = pd.DataFrame(ga_vars)
        conn = db.connect('google_api_variable_names.db')
        df.to_sql('vars', conn, index=False, if_exists='replace')
        conn.close()

    def add_custom_variables(self, keyfile: str, property_id: str, overwrite: bool = False):
        '''
        Adds custom dimensions and metrics to the database from a given property ID.

        :param keyfile: JSON keyfile.
            For authenticating the request to the GA property.
        :param property_id: Google Analytics property ID.
            Property ID where the custom dimensions and metrics are contained.
        :param overwrite: [optional] Overwrite current custom dimensions and metrics in the database.
            Useful when querying multiple properties.
        '''
        if self.cd_cm and not overwrite:
            raise UserWarning('Database already contains custom dimensions and/or custom metrics.\n'
                              'If you want to overwrite the current entries, you need to pass the parameter '
                              'overwrite=True.')
        check_keyfile(keyfile)
        id_check = re.match(r'^UA-[0-9]{8}-[0-9]{1,2}$', property_id)
        if not id_check:
            raise ValueError(f'{property_id} is not a valid property ID in format UA-XXXXXXXX-X(X)')

        scopes = ['https://www.googleapis.com/auth/analytics.readonly']
        credentials = Credentials.from_service_account_file(scopes=scopes)
        analytics = build('analytics', 'v3', credentials=credentials)

        dimensions = analytics.management().customDimensions().list(
            accountId=property_id.split('-')[1],
            webPropertyId=property_id
        ).execute()

        metrics = analytics.management().customMetrics().list(
            accountId=property_id.split('-')[1],
            webPropertyId=property_id
        ).execute()

        vals = []
        for item in dimensions['items'] + metrics['items']:
            type_ = 'Custom Metric'
            if 'Dimension' in item['kind']:
                type_ = 'Custom Dimension'
            val_name = item['name']
            api = item['id']
            vals.append({'name': val_name, 'type': type_, 'apicode': api})

        df = pd.DataFrame(vals)
        if overwrite:
            self.create_database()

        conn = db.connect('google_api_variable_names.db')
        df.to_sql('vars', conn, index=False, if_exists='append')
        self.all_names = pd.read_sql('SELECT * FROM vars', con=conn)
        self.cd_cm = True
        conn.close()

    def get_names(self, names: Union[list, str], return_type: str = None) -> Union[List[dict], list]:
        '''
        Retrieve information about a variable or a list of variables.

        :param names: Single name as a string or list of names to lookup. Either in ga:someVariable
            format or regular variable name.
        :param return_type: Specify the type of return. Options: 'name' to get a list of regular names, 'apicode'
            to get a list of the API codes. Default: list of dictionaries containing 'name', 'type'
            (Dimension or Metric) and 'apicode'.
        :return: List or list of dictionaries
        '''
        if type(names) == str:
            names = [names]

        results = []
        for name in names:
            if 'ga:' in name:
                if name == 'ga:segment':
                    results.append({'name': 'Segment', 'type': 'dimension', 'apicode': name})
                    continue
                if 'ga:metric' in name and not self.cd_cm:
                    num = name.replace('ga:metric', '')
                    results.append({'name': f'Metric {num}', 'type': 'metric', 'apicode': name})
                    continue

                if 'ga:dimension' in name and not self.cd_cm:
                    num = name.replace('ga:dimension', '')
                    results.append({'name': f'Dimension {num}', 'type': 'dimension', 'apicode': name})
                    continue

                df_name = self.all_names[self.all_names['apicode'] == name]
                if len(df_name) == 0:
                    raise ValueError(f'\'{name}\' is not a valid API code.')
            else:
                df_name = self.all_names[self.all_names['name'] == name]
                if len(df_name) == 0:
                    raise ValueError(f'\'{name}\' is not a valid variable name.')

            results.append(df_name.to_dict('records')[0])

        if return_type == 'name':
            return [f['name'] for f in results]
        elif return_type == 'apicode':
            return [f['apicode'] for f in results]
        return results
