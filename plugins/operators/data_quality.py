from airflow.models import BaseOperator
from airflow.providers.postgres.operators.postgres import PostgresHook



class DataQualityOperator(BaseOperator):
    """
    Purpose:
        Data quality
    BaseOperator
        Inherit class BaseOperator
    :param redshift_conn_id    Redshift connection id
    :type redshift_conn_id     str
    :param table_name          fact and dimension's table name
    :type table_name           list
    """

    # Setting the task background color
    # RPG: 137, 218, 89 -> Green
    ui_color = '#89DA59'

    def __init__(self,
                 *,
                 redshift_conn_id: str = '',
                 table_name: list = '',
                 **kwargs
                 ):
        super().__init__(**kwargs)
        self.redshift_conn_id = redshift_conn_id,
        self.table_name = table_name

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

    def data_quality_check(self, redshift_hook):
        """
        Purpose:
            count all tables records for checking data quality
        :param redshift_hook: Access redshift by PostgresHook
        :return: None
        """
        for table in self.table_name:
            table_record = redshift_hook.get_records(f"SELECT COUNT(*) FROM {table}")

            if len(table_record) < 1 or len(table_record[0]) < 1 or table_record[0][0] < 1:
                raise ValueError(f"Data quality check failed. {table} returned no results")