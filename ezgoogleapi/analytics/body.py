import json
from datetime import datetime
import warnings
from typing import Union

from ezgoogleapi.analytics.variable_names import VariableName
from ezgoogleapi.common.validation import validate_json_file
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


class Body:
    """Class to """
    _ids = count(0)

    def __init__(self, report: Union[dict, str]):
        if type(report) == str:
            report = validate_json_file(report)
            with open(report, 'r') as f:
                report = json.load(f)
        elif type(report) == dict:
            pass
        else:
            raise ValueError(f'{type(report)} is not a valid type for the report parameter. Use a dictionary or a '
                             f'string representing the path to a JSON file.')

        self.id = next(self._ids)
        self.input_fields = list(report.keys())
        _check_mandatory(self.input_fields)
        self.report = report
        self.view_id = report['view_id']
        self.name_client = VariableName()
        self.dimensions = self.name_client.get_names(report['dimensions'], return_type='apicode')
        self.metrics = self.name_client.get_names(report['metrics'], return_type='apicode')
        self.date_range = _get_date_range(self)
        self.resource_quota = False
        self.name = None
        self.body = None
        _construct_body(self)

    def __repr__(self):
        return f'{self.name}'


def _get_date_range(body_obj: Body):
    if 'start' in body_obj.report.keys():
        start = body_obj.report['start']
        try:
            return [start, body_obj.report['end']]
        except KeyError:
            raise KeyError('The "start" key is specified, but the there is no "end" key. '
                           'Either omit "start" and use the "date_range" option, or add an "end" key')
    elif 'end' in body_obj.report.keys():
        if 'date_range' not in body_obj.report.keys():
            raise KeyError('The "end" key is specified, but the there is no "start" key. '
                           'Either omit "end" and use the "date_range" option, or add a "start" key')
    elif 'date_range' in body_obj.report.keys():
        return body_obj.report["date_range"]


def _construct_body(body_obj):
    metrics = [{'expression': met} for met in body_obj.metrics]
    dimensions = [{'name': dim} for dim in body_obj.dimensions]
    body_obj.body = {
        'reportRequests': [
            {
                'viewId': str(body_obj.view_id),
                'metrics': metrics,
                'dimensions': dimensions,
                'samplingLevel': 'LARGE',
            }
        ],
    }

    fields = {
        'query_name': _add_name,
        'segments': _add_segments,
        'filters': _add_filters,
        'order_by': _add_ordering,
        'page_size': _add_page_size,
        'resource_quota': _add_resource_quota
    }

    added_fields = [field for field in body_obj.input_fields if field not in mandatory and field in fields]
    for field in added_fields:
        if body_obj.report[field]:
            fields[field](body_obj)

    if not body_obj.name:
        body_obj.name = 'Query ' + str(body_obj.id)


def _add_name(body_obj):
    body_obj.name = body_obj.report['query_name']


def _add_segments(body_obj):
    body_obj.body['reportRequests'][0]['dimensions'].append({'name': 'ga:segment'})
    body_obj.body['reportRequests'][0]['segments'] = []
    for f in body_obj.report['segments']:
        body_obj.body['reportRequests'][0]['segments'].append({'segmentId': f})


def _add_filters(body_obj):
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
    filters = body_obj.report['filters']
    if len(filters) > 1:
        try:
            logical_operator = body_obj.report['logical_operator']
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
                    names = body_obj.name_client.get_names(name.strip())[0]
                    type_ = names['type']
                    name = names['apicode']

                op = expressions[type_][op]

                if 'NOT' in op:
                    op = op.split('|')[0]
                    NOT = True
                else:
                    NOT = False

                if type_ == 'Dimension':
                    dimension_filters.append([name, op, NOT, exp])
                else:
                    metric_filters.append([name, op, NOT, exp])
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
        body_obj.body['reportRequests'][0]['dimensionFilterClauses'] = dim_filters
    if met_filters != [{'filters': []}]:
        body_obj.body['reportRequests'][0]['metricFilterClauses'] = met_filters


def _add_ordering(body_obj):
    body_obj.body['reportRequests'][0]['orderBys'] = []
    for var in body_obj.report['order_by']:
        sort_order = 'DESCENDING'
        if '&&ASC' in var:
            sort_order = 'ASCENDING'
            var = var.replace('&&ASC', '')
        body_obj.body['reportRequests'][0]['orderBys'].append({
            'fieldName': body_obj.name_client.get_names(var, return_type='apicode')[0],
            'orderType': 'VALUE',
            'sortOrder': sort_order
        })


def _add_page_size(body_obj):
    if body_obj.report['page_size'] > 100000:
        warnings.warn('Page size too large, must be <= 100.000. Setting page size for query to 100.000', UserWarning)
        body_obj.body['reportRequests'][0]['pageSize'] = 100000
    elif body_obj.report['page_size'] <= 0:
        warnings.warn('Page size not specified or negative. Using built-in default page size of 1.000', UserWarning)
    else:
        body_obj.body['reportRequests'][0]['pageSize'] = body_obj.report['page_size']


def _add_resource_quota(body_obj):
    body_obj.resource_quota = True


def _check_mandatory(input_fields):
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
                          f'*Start and end can be omitted when using the date_range option.')


def _to_query_date(date):
    if type(date) == 'str':
        return datetime.strptime(date, '%Y-%m-%d')
    else:
        return datetime.strftime(date, '%Y-%m-%d')
