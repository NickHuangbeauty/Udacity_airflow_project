from distutils.util import execute
import json
from airflow.models import BaseOperator
from airflow.providers.postgres.operators.postgres import PostgresHook

# Expected Result for checking my data pipeline process is successful or not.
expected_count = \
'''
{
    "songplays": 0,
    "songs": 0,
    "users": 0,
    "time": 0,
    "artists": 0
}
'''

class DataQualityOperator(BaseOperator):
    """
    Purpose:
        Data quality
    BaseOperator
        Inherit class BaseOperator
    :param redshift_conn_id    Redshift connection id
    :type redshift_conn_id     str
    :param table_name          tables_string: including tables, columns
    :type table_name           string
    :param redshift_schema     default is public
    :type redshift_schema      str
    """

    # Setting the task background color
    # RPG: 137, 218, 89 -> Green
    ui_color = '#89DA59'

    def __init__(self,
                 *,
                 redshift_conn_id: str = '',
                 table_name: str = '',
                 redshift_schema: str = 'public',
                 **kwargs
                 ):
        super().__init__(**kwargs)
        self.redshift_conn_id = redshift_conn_id
        self.table_name = table_name
        self.redshift_schema = redshift_schema

    def execute(self, context) -> None:
        """
        Purpose:
            1. Access Redshift and passed it in data_quality_check function
            2. execute data quality check function
        :param context: to read config values
        :return: None
        """
        self.log.info("Starting to access Redshift")
        redshift_hook = PostgresHook(postgres_conn_id=self.redshift_conn_id)

        self.log.info("Starting to data quality check")
        self.data_quality_check(redshift_hook)

    def execute_query(self, redshift_hook, table_name, condation):
        # Method 2
        return redshift_hook.get_records(
            f"SELECT COUNT(*) FROM {table_name} WHERE {condation} IS NULL"
        )

    def data_quality_check(self, redshift_hook):
        """
        Purpose:
            count all tables records for checking data quality
        :param redshift_hook: Access redshift by PostgresHook
        :return: None
        """
        # Convert data to json format
        excepted_result = json.loads(expected_count)
        actual_results = json.loads(self.table_name)

        # for checking  passed in data structure.
        # self.log.info(f"This is data: {self.table_name}")
        # self.log.info(f"This is data type: {type(self.table_name)}")
        # self.log.info(f"This is 'converted' data: {actual_results}")
        # self.log.info(f"This is 'converted' data type: {type(actual_results)}")

        # Data check for fact table: songplays
        for fact_table in actual_results["fact_table"]:
            fact_actual_results = self.execute_query(
                redshift_hook, fact_table['table_name'], fact_table['columns'][0].split(",")[0])

            if len(fact_actual_results[0]) < 1:
                raise ValueError(
                    f"Data quality check failed. {self.redshift_schema}.{fact_table['table_name']} returned no results")

            if fact_actual_results[0][0] != excepted_result[f"{fact_table['table_name']}"]:
                raise ValueError(
                    f"This test {fact_table['table_name']} failed. Result is {fact_actual_results[0]} and excepted result is {excepted_result['songplays']}")

        # Data check for dimension table: songs, artists, users, time
        for dimension in actual_results["dimension_table"]:
            dimension_actual_results = self.execute_query(
                redshift_hook, dimension['table_name'], dimension['columns'][0].split(",")[0])

            if len(dimension_actual_results[0]) < 1:
                raise ValueError(
                    f"Data quality check failed. {self.redshift_schema}.{fact_table['table_name']} returned no results")

            if dimension_actual_results[0][0] != excepted_result[f"{dimension['table_name']}"]:
                raise ValueError(
                    f"This test {dimension['table_name']} failed. Result is {dimension_actual_results[0]} and excepted result is {excepted_result['songplays']}")
