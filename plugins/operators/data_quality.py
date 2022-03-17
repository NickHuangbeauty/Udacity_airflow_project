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
    :param redshift_schema     default is public
    :type redshift_schema      str
    """

    # Setting the task background color
    # RPG: 137, 218, 89 -> Green
    ui_color = '#89DA59'
    
    expected_of_data_quality = {
        {'check_sql': "SELECT COUNT(*) FROM users WHERE userid is null", 'expected_result': 0},
        {},
        {},
        {}
    }


    def __init__(self,
                 *,
                 redshift_conn_id: str = '',
                 table_name: dict = '',
                 redshift_schema: str = 'public',
                 **kwargs
                 ):
        super().__init__(**kwargs)
        self.redshift_conn_id = redshift_conn_id,
        self.table_name = table_name,
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

    def data_quick_demo(self, redshift_hook, context):
        """
        Purpose:
            Create a expected result for mapping Actually Result of Query!!
        """
        mappings =  {{"songplays": "songplay_id", "count": 0},
                     {"songs": "song_id", "count": 0},
                     {"artists": "artist_id", "count": 0},
                     {"time": "start_time", "count": 0},
                     {"users": "userid", "count": 0},}
        
        
        
        general_result = """
            SELECT COUNT(*) FROM {table_name} WHERE {songplay_id} IS NULL == {count}
        """
        

    def data_quality_check(self, redshift_hook):
        """
        Purpose:
            count all tables records for checking data quality
        :param redshift_hook: Access redshift by PostgresHook
        :return: None
        """
        check = []
        for t in self.table_name:
            for each_table in t:
                table_record = redshift_hook.get_records(
                    f"SELECT COUNT(*) FROM {self.redshift_schema}.{each_table}")
                
                self.log.info(f"What's the table_record ? {table_record}")
                
                query_for_check = {
                    'query': f"SELECT count(*) FROM {each_table}", 'expected_result': f"{table_record}"}

                if len(table_record) < 1 or len(table_record[0]) < 1 or table_record[0][0] < 1:
                       raise ValueError(f"Data quality check failed. {self.redshift_schema}.{each_table} returned no results")

                check.append(query_for_check)

        self.log.info(f"Check data quality: {check}")
