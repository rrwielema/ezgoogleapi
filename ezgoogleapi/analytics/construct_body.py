import json
from datetime import datetime
import warnings
from ezgoogleapi.analytics.variable_names import VariableName
from itertools import count

mandatory = ['view_id', 'dimensions', 'metrics', 'start', 'end', 'date_range']

expressions = {
    'Dimension': {
        '==': 'EXACT',
        '!=': 'EXACT|NOT',
        '=@': 'PARTIAL',
        '!@': 'PARTIAL|NOT',
        '=~': 'REGEXP',
        '!~': 'REGEXP|NOT'
    },
    'Metric': {
        '==': 'EQUAL',
        '!=': 'EXACT|NOT',
        '<': 'LESS_THAN',
        '>': 'GREATER_THAN'
    }
}


class BodyObject:
    _ids = count(0)

    def __init__(self, report):
        self.id = next(self._ids)
        self.input_fields = list(report.keys())
        check_mandatory(self.input_fields)
        self.report = report
        self.view_id = report['view_id']
        self.name_client = VariableName()
        self.dimensions = self.name_client.get_names(report['dimensions'], return_type='apicode')
        self.metrics = self.name_client.get_names(report['metrics'], return_type='apicode')
        self.date_range = get_date_range(self)
        self.resource_quota = False
        self.name = None
        self.body = None
        construct_body(self)

    def __repr__(self):
        return f'{self.name}'


def get_date_range(self):
    if 'start' in self.report.keys():
        start = self.report['start']
        try:
            return [start, self.report['end']]
        except KeyError:
            raise KeyError('The "start" key is specified, but the there is no "end" key. '
                           'Either omit "start" and use the "date_range" option, or add an "end" key')
    elif 'date_range' in self.report.keys():
        return self.report["date_range"]


def construct_body(self):
    metrics = [{'expression': met} for met in self.metrics]
    dimensions = [{'name': dim} for dim in self.dimensions]
    self.body = {
        'reportRequests': [
            {
                'viewId': str(self.view_id),
                'metrics': metrics,
                'dimensions': dimensions,
                'samplingLevel': 'LARGE',
            }
        ],
    }

    fields = {
        'query_name': add_name,
        'segments': add_segments,
        'filters': add_filters,
        'order_by': add_ordering,
        'page_size': add_page_size,
        'resource_quota': add_resource_quota
    }

    added_fields = [field for field in self.input_fields if field not in mandatory and field in fields]
    for field in added_fields:
        if self.report[field]:
            fields[field](self)

    if not self.name:
        self.name = 'Query ' + str(self.id)


def add_name(self):
    self.name = self.report['query_name']


def add_segments(self):
    self.body['reportRequests'][0]['dimensions'].append({'name': 'ga:segment'})
    self.body['reportRequests'][0]['segments'] = []
    for f in self.report['segments']:
        self.body['reportRequests'][0]['segments'].append({'segmentId': f})


def add_filters(self):
    def single_filter(filter_list, val_type):
        if val_type == 'd':
            r_filter = {
                'dimensionName': filter_list[0],
                'operator': filter_list[1],
                'expressions': [filter_list[3]]
            }
        else:
            r_filter = {
                'metricName': filter_list[0],
                'operator': filter_list[1],
                'comparisonValue': filter_list[3]
            }
        if filter_list[2]:
            r_filter['not'] = True
        return r_filter

    logical_operator = None
    filters = self.report['filters']
    if len(filters) > 1:
        try:
            logical_operator = self.report['logical_operator']
        except KeyError:
            warnings.warn(
                "Multiple filters given, but no logical operator is supplied. Assuming 'AND' operator to combine filters.",
                UserWarning)
            logical_operator = 'AND'

    dimension_filters = []
    metric_filters = []

    for filter_ in filters:
        found = False
        for f in list(expressions['Dimension'].keys()) + list(expressions['Metric'].keys()):
            splitted = filter_.split(f)
            if len(splitted) > 1:
                name = splitted[0]
                op = f
                exp = splitted[1]
                if 'ga:dimension' in name:
                    type_ = 'Dimension'
                elif 'ga:metric' in name:
                    type_ = 'Metric'
                else:
                    type_ = self.name_client.get_names(name.replace(' ', ''))[0]['type']
                op = expressions[type_][op]

                if 'NOT' in op:
                    op = op.split('|')[0]
                    NOT = True
                else:
                    NOT = False

                if type_ == 'Dimension':
                    dimension_filters.append([splitted[0], op, NOT, exp])
                else:
                    metric_filters.append([splitted[0], op, NOT, exp])
                found = True
                break

        if not found:
            warnings.warn(f'Filter expression {filter_} could not be processed. No matching operator found.')

    dim_filters = [{'filters': []}]
    if len(dimension_filters) > 1:
        dim_filters[0]['operator'] = logical_operator
    for _ in dimension_filters:
        dim_filters[0]['filters'].append(single_filter(_, 'd'))

    met_filters = [{'filters': []}]
    if len(met_filters) > 1:
        met_filters[0]['operator'] = logical_operator
    for _ in metric_filters:
        met_filters[0]['filters'].append(single_filter(_, 'm'))

    if dim_filters != [{'filters': []}]:
        self.body['reportRequests'][0]['dimensionFilterClauses'] = dim_filters
    if met_filters != [{'filters': []}]:
        self.body['reportRequests'][0]['metricFilterClauses'] = met_filters


def add_ordering(self):
    self.body['reportRequests'][0]['orderBys'] = []
    for var in self.report['order_by']:
        sort_order = 'DESCENDING'
        if '&&ASC' in var:
            sort_order = 'ASCENDING'
            var = var.replace('&&ASC', '')
        self.body['reportRequests'][0]['orderBys'].append({
            'fieldName': self.name_client.get_names(var, return_type='apicode')[0],
            'orderType': 'VALUE',
            'sortOrder': sort_order
        })


def add_page_size(self):
    if self.report['page_size'] > 100000:
        warnings.warn('Page size too large, must be <= 100.000. Setting page size for query to 100.000', UserWarning)
        self.body['reportRequests'][0]['pageSize'] = 100000
    elif self.report['page_size'] <= 0:
        warnings.warn('Page size not specified or negative. Using built-in default page size of 1.000', UserWarning)
    else:
        self.body['reportRequests'][0]['pageSize'] = self.report['page_size']


def add_resource_quota(self):
    self.resource_quota = True


def check_mandatory(input_fields):
    missing_keys = [field for field in mandatory if field not in input_fields]
    if missing_keys == ['start', 'end'] or missing_keys == ['date_range']:
        return
    else:
        raise SyntaxError(f'Missing mandatory keys in query settings: {", ".join(missing_keys)}. '
                          f'Required keys are:\n'
                          f' - view_id\n'
                          f' - dimensions\n'
                          f' - metrics\n'
                          f' - start\n'
                          f' - end\n'
                          f'Start and end can be omitted when using the date_range option.')


def to_query_date(date):
    if type(date) == 'str':
        return datetime.strptime(date, '%Y-%m-%d')
    else:
        return datetime.strftime(date, '%Y-%m-%d')


class Body:
    @staticmethod
    def from_json(file: str) -> BodyObject:
        '''
        Load body settings from a JSON file.

        :param file: Path to file relative to working directory
        :return: BodyObject
        '''
        if '.json' not in file:
            raise IOError(f'{file} is not a JSON file.')
        with open(file, 'r') as f:
            f = json.load(f)
            return BodyObject(f)

    @staticmethod
    def from_dict(dictionary):
        '''
        Load body settings from a dictionary.

        :param dictionary: Body settings
        :return: BodyObject
        '''
        return BodyObject(dictionary)


Body = Body()
