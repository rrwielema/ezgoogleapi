# ezgoogleapi

This package contains wrapper functions and shortcuts for using web-related Google API's. 
For now it has functionality for Google Analytics (GA4 not included), BigQuery and Google Sheets. It integrates with pandas for easy data manipulation, preperation, and analysis. It is only tested for usage on Windows.

### Table of contents
- [Installation](#installation)
- [Google Analytics](#google-analytics)
  - [Requirements](#11-requirements)
  - [Quickstart](#12-quick-start)
  - [Configuring the body](#13-configuring-body)
    - [Options](#131-options)
    - [Dimensions and metrics](#132-dimensions-and-metrics)
    - [Ordering](#133-ordering)
    - [Resource quota](#134-resource-quota)
    - [Dates](#135-dates)
    - [Page size](#136-page-size)
    - [Segments](#137-segments)
    - [Filters](#138-filters)
    - [Logical operator](#139-logical-operator)
  - [Preparing the query](#14-preparing-the-query-class)
  - [Running the query](#15-running-the-query)
  - [Getting and saving the results](#16-getting-and-saving-the-results)
    - [Save to CSV](#161-save-to-csv)
    - [Save to SQLite](#162-save-to-sqlite)
    - [Return pandas DataFrame](#163-return-pandas-dataframe)
- [BigQuery](#2-bigquery)
  - [Requirements](#21-requirements)
  - [Quickstart](#22-quickstart)
  - [Initializing the BigQuery class](#23-initializing-the-bigquery-class)
  - [Setting the correct table](#24-setting-the-correct-table)
  - [Reading a table](#25-reading-a-table)
  - [Inserting rows](#26-inserting-rows)
  - [Deleting rows](#27-deleting-rows)
  - [Creating a table](#28-create-a-table)
    - [Complex schema's](#281-easy-creation-of-a-more-complex-schema)
  - [Deleting a table](#29-delete-table)
- [Google Sheets](#3-google-sheets)
  - [Requirements](#31-requirements)
  - [Quickstart](#32-quickstart)
  - [Reading sheets](#33-reading-sheets)
    - [Reading with no headers supplied](#331-reading-with-no-headers-supplied)
    - [Reading with custom headers](#332-reading-with-custom-headers)
  - [Writing to sheets](#34-writing-to-sheets)
  - [Clearing cell ranges](#35-clearing-cell-ranges)
  - [Creating a spreadsheet](#36-creating-a-spreadsheet)
    - [Adding permissions to a sheet](#361-adding-permissions-to-an-existing-sheet)
  

# Installation
Install the package through pip

`pip install git+https://github.com/rrwielema/ezgoogleapi`

# Google Analytics
This subpackage complements the Google Analytics API v4 and offers:
 - Automatic conversion of variable names into API reference codes and vice versa
 - Easy configuration of queries
 - Queries per day within the given date range to minimize sampling chance
 - Custom clean-up functions using pandas
 - Direct export of results to SQLite, CSV or DataFrame
 - Built-in date ranges
 - Built-in page token handling
 - Built-in sampling detection with customizable handling
 - Built-in error handling with (somewhat) useful feedback for easy trouble-shooting

## 1.1 Requirements
1. JSON key file containing the credentials for the service account, placed in the working directory - More information [here](https://support.google.com/a/answer/7378726?hl=en).
2. Activated Google Analytics API - More information [here](https://developers.google.com/analytics/devguides/reporting/core/v4/quickstart/service-py).

## 1.2 Quick start

This example will retrieve yesterday's amount of sessions per device category and saves it to CSV.

```python
from ezgoogleapi import analytics as ga

config = {
  'view_id': 123456789,
  'dimensions': ['Device Category'],  # or ['ga:deviceCategory']
  'metrics': ['Sessions'],  # or ['ga:sessions']
  'date_range': ga.YESTERDAY
}

key_file = 'credentials.json'

body = ga.Body(config)
query = ga.Query(body, key_file)
query.run()
query.to_csv('sessions per device.csv')
```

## 1.3 Configuring Body
The Analytics Body can be created by providing a dictionary or the path to a JSON file containing the same items e.g. 'config.json'.

It supports:
- using resource quota for Analytics 360 properties
- ordering
- filters
- segments by ID - More information [here](https://developers.google.com/analytics/devguides/reporting/core/v3/segments#byid)

It does not support:
- multiple date ranges
- dynamic segments
- cohorts, pivots, LVT, and buckets

### 1.3.1 Options
The table below lists the possible inputs for the Body object.

| Option          | Input type                          | Required |
|-----------------|-------------------------------------|----------|
| view_id         | int or str                          | yes      |
| dimensions      | list                                | yes      |
| metrics         | list                                | yes      |
| order_by        | list                                | no       |
| resource_quota  | bool, default False                 | no       |
| start           | datetime.datetime or YYYY-MM-DD str | yes*     |
| end             | datetime.datetime or YYYY-MM-DD str | yes*     |
| date_range      | list of datetime.datetime (len = 2) | yes*     |
| page_size       | int < 100000, default 1000          | no       |
| segments        | list                                | no       |
| filters         | list                                | no       |
| filter_operator | str - either AND or OR, default AND   | no       |

*Both `start` and `end` or just `date_range` must be supplied

### 1.3.2 Dimensions and metrics
You can supply `dimensions` and `metrics` by their English variable name or the API reference code. 
```python
config = {
    #...
    'dimensions': ['Page', 'ga:deviceCategory'],
    'metrics': ['Pageviews', 'ga:exits']
    #...
}
```

#### Custom dimensions and metrics
CDs and CMs by default only work by their API reference code, e.g. ga:dimension3 or ga:metric7.
To enable name conversion for custom definitions, use following code segment. It assumes that you have the correct rights to access those, otherwise will raise an Error.
```python
from ezgoogleapi import analytics as ga

keyfile = 'credentials.json'
property_id = 'UA-12345678-9'

ga.NameDatabase.add_custom_variables(keyfile, property_id)
```

### 1.3.3 Ordering
Supply the `order_by` key in the configuration dictionary to order the query. If supplied, it will assume descending order by default. To order ascending, add `&&ASC` to the variable.

```python
# descending
config = {
    #...
    'dimensions': ['Page', 'ga:deviceCategory'],
    'metrics': ['Pageviews', 'ga:exits'],
    'order_by': ['Pageviews']
    #...
}
```
```python
# ascending
config = {
    #...
    'dimensions': ['Page', 'ga:deviceCategory'],
    'metrics': ['Pageviews', 'ga:exits'],
    'order_by': ['Pageviews&&ASC']
    #...
}
```
### 1.3.4 Resource quota
Resource quotas are ignored by default, even when supplied. Only when sampling is detected by the module, resource quotas can be used.
```python
config = {
    #...
    'resource_quota': True
    #...
}
```

### 1.3.5 Dates
Date ranges can be supplied in multiple ways. The most useful and dynamic way is through datetime objects, but YYYY-MM-DD is also possible. Any dates in the future will be rejected.

#### Start and end
`start` and `end` can be `datetime.datetime` or `YYYY-MM-DD`. The datetime format is highly recommended if you want to make dynamic date ranges.

```python

from datetime import datetime, timedelta

today = datetime.now()

# get last 14 days
config = {
    #...
    'start': today - timedelta(days=14),
    'end': today - timedelta(days=1),
    #...
}

# get static date range
config = {
    #...
    'start': '2021-07-28',  # or datetime(2021, 7, 28)
    'end': '2021-08-10',  # or datetime(2021, 8, 10)
    #...
}
```

#### Built-in date ranges
The analytics module contains built-in date ranges that can most likely satisfy your needs.
Options: YESTERDAY, LAST_WEEK, LAST_7_DAYS, THIS_MONTH, LAST_MONTH, LAST_90_DAYS, THIS_YEAR, LAST_YEAR, THIS_QUARTER, LAST_QUARTER.

```python
from ezgoogleapi import analytics as ga

config = {
    #...
    'date_range': ga.LAST_MONTH
    #...
}

```

#### Date range functions
Options: weeks(), last_weeks(), last_days(),  

Date range of ISO week(s) by using the `weeks()` function. Input is `int` for a single week and `list` of 2 `int` for a week range 
```python
from ezgoogleapi import analytics as ga

# today -13 days to yesterday -> last 12 days
config = {
    #...
    'date_range': ga.last_days(12)
    #...
}


# week 12 of 2021
config = {
    #...
    'date_range': ga.weeks(12, 2021)
    #...
}

# weeks 12 to 21 of 2021 (including 21)
config = {
    #...
    'date_range': ga.weeks([12, 21], 2021)  
    #...
}

# week 42 of 2020 to the end of week 21 of 2021
config = {
    #...
    'date_range': ga.combine_ranges(ga.weeks(42, 2020), ga.weeks(21, 2021))  
    #...
}
```
By default it will assume monday as the first day of the week, but takes optional parameter `first day` e.g. sunday as the first day `weeks([12, 21], 2021, first_day='sun')`.

```python
from ezgoogleapi import analytics as ga

# first quarter of 2021
config = {
    #...
    'date_range': ga.quarter(1, 2021)  
    #...
}

# last quarter of 2020 and first quarter of 2021
config = {
    #...
    'date_range': ga.combine_ranges(ga.quarter(4, 2020), ga.quarter(1, 2021))
    #...
}
```

### 1.3.6 Page size
By default, page size is 1000. You can supply an int between 1 and 100000 to use a custom page size.
```python
config = {
    #...
    'page_size': 100000 
    #...
}
```

### 1.3.7 Segments
Segments can be supplied in the same way as the v3 API. More information [here](https://developers.google.com/analytics/devguides/reporting/core/v3/segments#byid).
```python
# two segments: by ID and a custom expression
config = {
    #...
    'segments': ['gaid::3', 'sessions::condition::ga:medium==referral']  
    #...
}
```

### 1.3.8 Filters
Filters are mostly the same as in the v3 API. More information [here](https://developers.google.com/analytics/devguides/reporting/core/v3/reference#filters).
You can use both API reference codes like `ga:deviceCategory` or the variable name `Device Category`.
- Use " " if your condition contains spaces, e.g. "Organic Search"

```python
# two segments: by ID and a custom expression
config = {
    #...
    'filters': ['ga:deviceCategory==mobile', 'ga:channelGrouping=="Organic Search"']  
    #...
}
```
### 1.3.9 Logical operator
When you supply multiple filters, the module assumes `AND` to combine them. You can override it by supplying the `filter_operator` option.
```python
# two segments: by ID and a custom expression
config = {
    #...
    'filters': ['ga:deviceCategory==mobile', 'ga:channelGrouping=="Organic Search"'],  
    'filter_operator': 'OR'
    #...
}
```

## 1.4 Preparing the Query class
The `Query` class takes two required arguments:
 - Body object
 - JSON keyfile
 
Example: page views for product pages last week, sorted by amount of page views
```python
from ezgoogleapi import analytics as ga

config = {
    'view_id': 123456789,
    'dimensions': ['Page'],
    'metrics': ['Pageviews'],
    'date_range': ga.LAST_WEEK,
    'filters': ['ga:page=@/product/'],
    'order_by': ['Pageviews']
}

keyfile = 'credentials.json'

body = ga.Body(config)
query = ga.Query(body, keyfile)
```

You can supply a function to clean up your data during the execution of queries. The function takes 1 argument, which is a pandas DataFrame and also has to return a pandas DataFrame.

- Note that column names of the DataFrame will be in API reference code, unless specified otherwise when you [run the query](#15-running-the-query).

```python
import pandas as pd
from ezgoogleapi import analytics as ga

config = {
    'view_id': 123456789,
    'dimensions': ['Page'],
    'metrics': ['Pageviews'],
    'date_range': ga.LAST_WEEK,
    'filters': ['Page=@/product/'],
    'order_by': ['Pageviews']
}

keyfile = 'credentials.json'

#function to convert string pageviews to integers
def clean_up_func(df: pd.DataFrame) -> pd.DataFrame:
    df['ga:pageviews'] = df['ga:pageviews'].apply(lambda x: int(x))
    return df


body = ga.Body(config)
query = ga.Query(body, keyfile, clean_up=clean_up_func)
```

## 1.5 Running the query
The `run()` method of the `Query` class is used to run the queries.

```python
import pandas as pd
from ezgoogleapi import analytics as ga

config = {
  # ...
}

keyfile = 'credentials.json'

body = ga.Body(config)
query = ga.Query(body, keyfile)
query.run()
```
The method accepts some optional parameters:
 - `per_day` - run query per day within the given date range to minimize sampling chance (default `True`)
 - `sampling` - define the handling of sampled data (default `'fail'`, which will raise a SamplingError). Other options are `'skip'` to ignore the data and `'save'` to keep the data. The `'save'` option adds a column displaying the sample percentage.
 - `clean_headers` - specify wether to use the API reference code or the variable names as headers (default `False`). When passing `True` and your query contains custom definitions, make sure to add them to the NameDatabase like [here](#custom-dimensions-and-metrics).

```python
from ezgoogleapi import analytics as ga

config = {
  # ...
}

keyfile = 'credentials.json'

body = ga.Body(config)
query = ga.Query(body, keyfile)
query.run(per_day=False, sampling='save', clean_headers=True)
```

## 1.6 Getting and saving the results
The results from `Query.run()` can be retrieved in three ways:
 - `Query.to_csv()` - Save to CSV
 - `Query.to_sqlite()` - Save to SQLite
 - `Query.to_dataframe()` - Return pandas DataFrame for further manipulation/analysis

Any headers containing API reference codes will be replaced by their variable name.

### 1.6.1 Save to CSV
The `Query.to_csv()` method takes the desired file name/path as an argument

```python
from ezgoogleapi import analytics as ga

config = {
  # ...
}

keyfile = 'credentials.json'

body = ga.Body(config)
query = ga.Query(body, keyfile)
query.run()
query.to_csv('example.csv')
```

### 1.6.2 Save to SQLite
The `Query.to_sqlite()` method takes 3 optional arguments.
 - `headers` - Supply your own headers. Must be `list` of the same length as the amount of columns.
 - `db_name` - Specify a name for the database. If not specified, then the query name from the
            Body object will be used. If that also isn't specified, it will fall back to Query [num], depending on the
            amount of Body instances. Ex. Query 0 for the first one.
 - `table_name` - Specify a table name for your query results. Defaults to `table_name='results'`.

```python
from ezgoogleapi import analytics as ga

config = {
  # ...
}

keyfile = 'credentials.json'

body = ga.Body(config)
query = ga.Query(body, keyfile)
query.run()
query.to_sqlite(headers=['Date', 'Device', 'Channels', 'Sessions'],
                db_name='example db',
                table_name='example table')
```
### 1.6.3 Return pandas DataFrame
For further data manipulation and analysis, it might be useful to collect the data in a DataFrame.
The method `Query.to_dataframe()` takes no arguments.

```python
from ezgoogleapi import analytics as ga

config = {
  # ...
}

keyfile = 'credentials.json'

body = ga.Body(config)
query = ga.Query(body, keyfile)
query.run()
df = query.to_dataframe()
```

# 2 BigQuery
The BigQuery module is built around the conveniently named `BigQuery` class. It depends, again, on the pandas package.
For now, it has the following functionalities:
 - Reading an existing table
 - Writing to an existing table
 - Deleting rows from an existing table
 - Creating a table with easy syntax
 - Deleting a table

## 2.1 Requirements
1. JSON key file containing the credentials for the service account, placed in the working directory - More information [here](https://support.google.com/a/answer/7378726?hl=en).
2. 2. Activated Google BigQuery API - More information [here](https://cloud.google.com/bigquery-transfer/docs/enable-transfer-service).

## 2.2 Quickstart
Read an existing BigQuery table and return it as a pandas DataFrame in 6 lines of code.

```python
from ezgoogleapi.bigquery import BigQuery

keyfile = 'credentials.json'
table_name = 'Project.Database.exampleTable'

# initialize BigQuery class 
bq = BigQuery(keyfile)

# set the current table
bq.set_table(table_name)

# return results
df = bq.read_table()
```

## 2.3 Initializing the BigQuery class
The `BigQuery` class takes only the keyfile location as an argument.

```python
from ezgoogleapi.bigquery import BigQuery

keyfile = 'credentials.json'
bq = BigQuery(keyfile)
```

## 2.4 Setting the correct table
To do anything involving tables, you need to set the table name for the BigQuery class to use.
The given table name contains the project name, database name and table name, seperated by dots.
```python
from ezgoogleapi.bigquery import BigQuery

keyfile = 'credentials.json'
table_name = 'Project.Database.exampleTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)
```

## 2.5 Reading a table
You can read a table by using the `BigQuery.read_table()` method. 
```python
from ezgoogleapi.bigquery import BigQuery

keyfile = 'credentials.json'
table_name = 'Project.Database.exampleTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)
bq.read_table()
```

This method takes 3 optional arguments:
 - `columns` - `list` of column names that need to be included in the result, if left empty all columns will be returned.
 - `condition` - SQL condition starting with `WHERE` to filter results. e.g. `WHERE some_column LIKE '%Some Value%'`.
 - `return_format` - The return format can be `'list'`, `'dict'` or `'df'` (default `df`). Option `'list'` will return
 a list of rows without headers, `'dict'` will return a list of dictionaries with the table headers as keys, `'df`' 
returns a pandas DataFrame with same formatting as your table.

```python
from ezgoogleapi.bigquery import BigQuery

keyfile = 'credentials.json'
table_name = 'Project.Database.exampleTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)

#returns a list of rows with 3 columns, where some other column is greater than 100
bq.read_table(columns=['ex_1', 'ex_2', 'ex_3'], 
              condition='WHERE ex_4 > 100', 
              return_format='list')
```

## 2.6 Inserting rows
Use the `BigQuery.insert_rows()` to insert data in an existing table. It takes the data as an argument, specified in one of the following data formats:
- a pandas DataFrame
- a list containing dictionaries with the same keys in each dictionary
- a list containing lists where the first list represents the headers and the following contain the data

Make sure any headers or column names correspond to the column names in the table you are trying to alter.

```python
from ezgoogleapi.bigquery import BigQuery
import pandas as pd

keyfile = 'credentials.json'
table_name = 'Project.Database.exampleTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)

data = pd.read_csv('some_file.csv')
bq.insert_rows(data)
```

If you try to insert more than 10000 rows, the request will be broken up into multiple request to limit the payload 
size. You can customize that number by using the `per_request` parameter. It takes an `int` between 0 and 10000. Lower means more requests, but less chance of 
errors related to the size of a single request.

```python
bq.insert_rows(data, per_request=5000)
```

## 2.7 Deleting rows
The `BigQuery.delete_row()` is used to delete rows from an existing table. It takes two optional arguments:
 - `condition` - By default, `delete_row()` will delete every row in a table. You will need to supply an SQL condition containing `WHERE` to define the scope.
 - `sure` - If no condition is supplied, you will need to pass `sure=True` to confirm you want to delete all rows in the table.

```python
from ezgoogleapi.bigquery import BigQuery

keyfile = 'credentials.json'
table_name = 'Project.Database.exampleTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)

# delete all rows
bq.delete_rows(sure=True)

# delete rows given some condition
bq.delete_rows(condition='WHERE some_column > 100')
```

## 2.8 Create a table
With the BigQuery class, you can easily create a new table.
1. set the table name for your new table
2. supply a table schema, which is at a minimum a list of column names. By default the data type will be `STRING`.

The `BigQuery.create_table()` method takes the schema as an argument.

Most simple usage to create a new table named 'newTable' with 3 columns and data type string.
```python
from ezgoogleapi.bigquery import BigQuery

keyfile = 'credentials.json'
table_name = 'Project.Database.newTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)

schema = ['ex_col1', 'ex_col2', 'ex_col3']
bq.create_table(schema)
```

### 2.8.1 Easy creation of a more complex schema
To create a schema, you can either use:
 - built-in data types
 - the `schema()` function of the bigquery module to automatically detect data types from a pandas DataFrame
```python
from ezgoogleapi.bigquery import BigQuery, SchemaTypes

keyfile = 'credentials.json'
table_name = 'Project.Database.newTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)

schema = [['ex_col1', SchemaTypes.DATETIME], 
          ['ex_col2', SchemaTypes.BOOL], 
          ['ex_col3', SchemaTypes.INT64]]
bq.create_table(schema)
```

```python
import pandas as pd
from ezgoogleapi.bigquery import BigQuery, schema

keyfile = 'credentials.json'
table_name = 'Project.Database.newTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)

df = pd.read_csv('some_file.csv')
sch = schema(df)
bq.create_table(sch)
```

## 2.9 Delete table
Deleting a table can be done by calling the `BigQuery.delete_table()` method. It takes argument `sure` as an insurance 
policy to make sure you want to delete the table. You will get a warning if you don't pass `sure=True` and the table 
won't be deleted.

```python
from ezgoogleapi.bigquery import BigQuery

keyfile = 'credentials.json'
table_name = 'Project.Database.exampleTable'

bq = BigQuery(keyfile)
bq.set_table(table_name)
bq.delete_table(sure=True)
```

## 3 Google sheets
The Google Sheets subpackage features:
 - Reading sheets
 - Writing to sheets
 - Clearing cells
 - Creating sheets

### 3.1 Requirements
1. JSON key file containing the credentials for the service account, placed in the working directory - More information [here](https://support.google.com/a/answer/7378726?hl=en).
2. Activated Google Sheets API and Drive API - More information [here](https://support.google.com/googleapi/answer/6158841?hl=en).

### 3.2 Quickstart
This example writes the result of a Google Analytics query to Google Sheets.

```python
from ezgoogleapi import analytics as ga
from ezgoogleapi import SpreadSheet

KEYFILE = 'credentials.json'

config = {
  'view_id': 123456789,
  'dimensions': ['Device Category'],
  'metrics': ['Sessions'],
  'date_range': ga.YESTERDAY
}
body = ga.Body(config)
query = ga.Query(body, KEYFILE)
query.run()

sheet = SpreadSheet(KEYFILE)  # initialize SpreadSheet class
sheet_id = sheet.create('Query result')  # create new sheet
sheet.set_sheet_id(sheet_id)  # set sheet id for following functions
sheet.append(query.to_dataframe(), 'A:G')  # append values to range A:G
```

### 3.3 Reading sheets
To read a spreadsheet, you initialize the `SpreadSheet` class with the key file as an argument and set the sheet ID.
The `SpreadSheet` class has the `.read()` method to retrieve data. Arguments:
 - Cell range (str) - The range of the cells to be retrieved, e.g. 'A:G', 'A15', '125:160', 'A100:G'
 - Optional: `tab` (str) - The name of the tab/sheet within the spreadsheet
 - Optional: `return_format` (str) - Return format, either 'list' or 'df' (default). Using 'list' will output a list of 
the rows in the supplied cell-range.

Only working with `return_format='df'`:
 - Optional: `header_range` (str) - Range of the cells that contain headers for the data, e.g. 'A1:G1'
 - Optional: `headers` (list) - List of headers to be set for the data

If no headers are supplied, the headers will be based on the range. Range 'A:D' will contain A, B, C and D as headers.


#### 3.3.1 Reading with no headers supplied
When outputting a DataFrame with no header options, the DataFrame will mimic the sheet layout. Indiviual cells and 
cell ranges can be selected easily this way. Note that `return_format='df'` is only specified for clarification.
```python
from ezgoogleapi import SpreadSheet

KEYFILE = 'credentials.json'
SHEET = '1rEval_KNrWzp-p-paYfhV2G3_bDv80bJ_qoClZBk0yE'
sheet = SpreadSheet(KEYFILE)
df = sheet.read('A15:D30', tab='Sheet2', return_format='df')
```

The output of the DataFrame will look like this. 

|    | A               | B                                   | C         |D      |
|----|-----------------|-------------------------------------|----------|----------|
|15|        |                       |      |
|16|       |                                |      |
|...|       |                     |       |      |
|29|       |                                |      |
|30|       |                                |      |

Individual cells and cell ranges can be accessed by using pandas' `.loc[rows, columns]`.

```python
from ezgoogleapi import SpreadSheet

KEYFILE = 'credentials.json'
SHEET = '1rEval_KNrWzp-p-paYfhV2G3_bDv80bJ_qoClZBk0yE'
sheet = SpreadSheet(KEYFILE)
df = sheet.read('A15:D30', tab='Sheet2', return_format='df')

B25 = df.loc[25, 'B']  # cell B25
row17 = df.loc[17, :]  # row 17
C15_C25 = df.loc[15:25, 'C']  # cell range C15-C25
B15_D25 = df.loc[15:25, 'B:D']  # cell range B15-D25
```

#### 3.3.2 Reading with custom headers
You can either set your own headers or extract headers from the data.

```python
from ezgoogleapi import SpreadSheet

KEYFILE = 'credentials.json'
SHEET = '1rEval_KNrWzp-p-paYfhV2G3_bDv80bJ_qoClZBk0yE'
sheet = SpreadSheet(KEYFILE)
headers = ['Col A', 'Col B', 'Col C', 'Col D']  # define custom headers
df = sheet.read('A15:D30', tab='Sheet2', headers=headers)  # pass headers as argument
```

You can supply a range within the data to retrieve the headers from the sheet. If the headers are also in the 
read range, the duplicate rows will be removed.

```python
from ezgoogleapi import SpreadSheet

KEYFILE = 'credentials.json'
SHEET = '1rEval_KNrWzp-p-paYfhV2G3_bDv80bJ_qoClZBk0yE'
sheet = SpreadSheet(KEYFILE)
df = sheet.read('A15:D30', tab='Sheet2', header_range='A1:D1')  # range of headers
```

### 3.4 Writing to sheets
The `SpreadSheet.append` method is used to write rows to a spreadsheet. It takes 1 argument and 3 optional keyword arguments:
 - data (pd.DataFrame or list of rows) - The data to pass to Google Sheets
 - Optional: `cell_range` (str) - If not supplied, it will base the range on the row lengths. A DataFrame with 4 columns will generate range 'A:D'.
 - Optional: `tab` (str) - The name of the tab/sheet within the spreadsheet. No supplied tab will default to the first tab in the spreadsheet.
 - Optional: `per_request` (int) - Amount of rows per request (default 10,000). If you encounter errors as a result of the large requests, you can lower the amount of rows per request. It is not recommended to use more than 10,000.

#### Usage
```python
import pandas as pd
from ezgoogleapi import SpreadSheet

data = pd.read_csv('some_file.csv')

KEYFILE = 'credentials.json'
SHEET = '1rEval_KNrWzp-p-paYfhV2G3_bDv80bJ_qoClZBk0yE'
sheet = SpreadSheet(KEYFILE)
sheet.append(data)  # automatic cell range detection
sheet.append(data, cell_range='F:J', tab='Sheet2')  # specific range of specific tab
```

### 3.5 Clearing cell ranges
The `SpreadSheet` class has a method called `clear()` to remove data from cells. You only have to supply the range and 
the `tab` (optional) to clear.

#### Usage
```python
from ezgoogleapi import SpreadSheet

KEYFILE = 'credentials.json'
SHEET = '1rEval_KNrWzp-p-paYfhV2G3_bDv80bJ_qoClZBk0yE'
sheet = SpreadSheet(KEYFILE)
sheet.clear('A2:D', tab='Sheet2')  # clears all rows from row 2 and on, for the columns A to D
```

### 3.6 Creating a spreadsheet
Using `SpreadSheet.create` with title as an argument. The method will set the newly created spreadsheet id (str) 
to `SpreadSheet.sheet_id` and prints the link. Note that you cannot open the created spreadsheet online 
without adding permission to a real account instead of a service acoount. You can pass `Permission` objects to the 
`create` method using the keyword argument `permissions`.


#### Usage - without extra permissions
```python
import pandas as pd
from ezgoogleapi import SpreadSheet

KEYFILE = 'credentials.json'
sheet = SpreadSheet(KEYFILE)
sheet.create('New Sheet')  # creates new sheet and returns the new sheet_id

df = pd.read_csv('some-file.csv')
sheet.append(df)  # write to the created sheet
```


#### Usage - with permissions
The `Permission` class is used to define the email address and desired role for a user. Role can be 'reader', 
'writer' or 'owner'. If the email address represents a group of users, you can pass `group=True`.

```python
from ezgoogleapi import Permission, SpreadSheet

KEYFILE = 'credentials.json'
sheet = SpreadSheet(KEYFILE)

permissions = Permission('someaddress123@gmail.com', 'reader')  # single user

permissions = Permission('someaddress123@gmail.com', 'reader', group=True)  # group of users

permissions = [  # multiple users
  Permission('someaddress123@gmail.com', 'reader'),
  Permission('someaddress456@gmail.com', 'writer')
]

sheet.create('New Sheet', permissions=permissions)
```

#### 3.6.1 Adding permissions to an existing sheet

```python
from ezgoogleapi import Permission, SpreadSheet

KEYFILE = 'credentials.json'
SHEET = '1rEval_KNrWzp-p-paYfhV2G3_bDv80bJ_qoClZBk0yE'
sheet = SpreadSheet(KEYFILE)
sheet.set_sheet_id(SHEET)

permissions = Permission('someaddress123@gmail.com', 'reader')

sheet.add_permissions(permissions)
```