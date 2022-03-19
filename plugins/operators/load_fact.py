from airflow.models import BaseOperator
from airflow.providers.postgres.operators.postgres import PostgresHook

# from helpers.sql_queries import SqlQueries

class LoadFactOperator(BaseOperator):
    """
    Purpose:
        Load stage table data to fact table
    BaseOperator
        Inherit class BaseOperator
    :param redshift_conn_id     Redshift connection id
    :type redshift_conn_id      str
    :param table_name           fact table name
    :type table_name            str
    :param column_names         column name of fact table
    :type column_names          str
    :param sql_statement        insert into sql statement
    :type sql_statement         str
    :param redshift_schema      default is public
    :type redshift_schema       str
    :param is_truncate_table    default is False
    :type is_truncate_table     boolean
    """

    # Setting the task background color
    # RPG: 249, 136, 102 -> Orange
    ui_color = '#F98866'
    
    # template_fields
    template_fields = ("sql_statement", )

    truncate_table = \
        """
        TRUNCATE TABLE "{redshift_schema}"."{table_name}"
        """

    insert_table = \
        """
        INSERT INTO "{redshift_schema}"."{table_name}" ({column_names})\n {source_sql_statemnet}
        """

    def __init__(self,
                 *,
                 redshift_conn_id: str = "",
                 table_name: str = "",
                 column_names: str = "",
                 sql_statement: str = "",
                 redshift_schema: str = "public",
                 is_truncate_table: bool = False,
                 **kwargs) -> None:
        super().__init__(**kwargs)
        self.redshift_conn_id = redshift_conn_id
        self.table_name = table_name
        self.column_names = column_names
        self.sql_statement = sql_statement
        self.redshift_schema = redshift_schema
        self.is_truncate_table = is_truncate_table

    def execute(self, context) -> None:
        """
        Purpose:
            1. Access Redshift by PostgresHook
            2. truncate_table parameter default is false
                - if it's passed a True parameter, then execute truncate table sql statement.
        :param context: to read config values
        :return: None
        """

        redshift_hook = PostgresHook(postgres_conn_id=self.redshift_conn_id)

        self.load_songplays_fact_table(redshift_hook, context)

    def load_songplays_fact_table(self, redshift_hook, context) -> None:
        """
        Purpose:
            1. Loading data from stage table
                - stage table: stage_event, stage_song
            2. truncate_table parameter default is false
                - if it's passed a True parameter, then executed truncate_table sql statement.
        :param redshift_hook: access Redshift by PostgresHook
        :return: None
        """
        if self.is_truncate_table:
            # Log information
            self.log.info(f"Starting to truncate {self.table_name}")
            # Execute truncate table
            truncate_fact_table = LoadFactOperator.truncate_table.format(
                redshift_schema=self.redshift_schema,
                table_name=self.table_name
            )
            redshift_hook.run(truncate_fact_table)

        # Insert into data
        self.log.info(f"Starting to insert {self.table_name}")
        
        sql_statement_render = self.sql_statement.format(**context)

        # Execute insert table
        insert_fact_data = LoadFactOperator.insert_table.format(
            redshift_schema=self.redshift_schema,
            table_name=self.table_name,
            column_names=self.column_names[0],
            source_sql_statemnet=sql_statement_render
        )
        redshift_hook.run(insert_fact_data)
