import os

BASE_DIR = os.getcwd()


class SamplingError(Exception):
    def __init__(self, percentage, csv):
        self.percentage = round(percentage * 100, 1)
        csv_string = ''
        if csv:
            csv_string = f' and results untill now have been saved to {BASE_DIR + "/partial_results.csv"}'
        self.message = f'Sampling detected in results ({self.percentage}%) and sampling is set to \'fail\'\n. ' \
                       f'Execution of queries is stopped{csv_string}. If you want to continue when sampling is ' \
                       f'encountered, then use the option sampling=\'skip\' to only save results without sampling or ' \
                       f'sampling=\'save\' to keep all the results.'
        super().__init__(self.message)


class InvalidRangeError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class InvalidKeyFileError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class NotAuthorizedError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)