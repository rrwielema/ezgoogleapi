hard_dependencies = ("pandas", "google", "google-api-python-client")
missing_dependencies = []

for dependency in hard_dependencies:
    try:
        __import__(dependency)
    except ImportError as e:
        missing_dependencies.append(f"{dependency}: {e}")

if missing_dependencies:
    raise ImportError(
        "Unable to import required dependencies:\n" + "\n".join(missing_dependencies)
    )
del hard_dependencies, dependency, missing_dependencies

from ezgoogleapi.analytics.construct_body import Body
from ezgoogleapi.analytics.daterange import (TODAY,
                                             YESTERDAY,
                                             LAST_WEEK,
                                             LAST_7_DAYS,
                                             THIS_MONTH,
                                             LAST_MONTH,
                                             LAST_90_DAYS,
                                             LAST_YEAR,
                                             CURRENT_QUARTER,
                                             LAST_QUARTER,
                                             quarter,
                                             weeks)
from ezgoogleapi.analytics.query import Query
from ezgoogleapi.analytics.variable_names import VariableName
from ezgoogleapi.bigquery.base import BigQuery
from ezgoogleapi.bigquery.schema import schema, SchemaTypes
