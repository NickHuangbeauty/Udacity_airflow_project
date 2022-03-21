from airflow.providers.postgres.operators.postgres import PostgresHook
from airflow.models import BaseOperator

class LoadDimensionOperator(BaseOperator):
    """
    Purpose:
        Load data from stage and fact tables.
    BaseOperator
        Inherit class BaseOperator
    :param redshift_conn_id   Redshift connection id
    :type redshift_conn_id    str
    :param table_name         four dimension tables: songs, time, users, artise
    :type table_name          str
    :param column_names       each of dimension table's columns
    :type column_names        str
    :param sql_statement      for inserting  into
    :type sql_statement       str
    :param redshift_schema    Redshift schema: public (default)
    :type redshift_schema     str
    :param is_truncate_table  truncate table or not (default is False)
    :type is_truncate_table   boolean
    """
    # Setting the task background color
    # RPG: 128, 189, 158 -> Green
    ui_color = '#80BD9E'

    template_fields = ("sql_statement",)

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
                 redshift_schema: str = "",
                 is_truncate_table: bool = False,
                 **kwargs):
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
            1. Access Redshift by Postgreshook
            2. Execute load dimension table function to load data from two stage tables and one fact table.
        :param context: to read config values
        :return: None
        """
        redshift_hook = PostgresHook(postgres_conn_id=self.redshift_conn_id)

        self.load_dimension_table(redshift_hook, context)

    def load_dimension_table(self, redshift_hook, context) -> None:
        """
        Purpose:
            1. Loading data from stage and fact table
                - Stage table: stage_event, stage_song
                - Fact table: songplays
            2. truncate_table parameter default is false
                - if it's passed a True parameter, then execute truncate table sql statement.
        :param redshift_hook:
            access Redshift by PostgresHook
        :return: None
        """
        if self.is_truncate_table:
            # Log information
            self.log.info(f"Starting to truncate {self.table_name}")
            # Execute truncate table
            truncate_dimension_table = LoadDimensionOperator.truncate_table.format(
                redshift_schema=self.redshift_schema,
                table_name=self.table_name
            )
            redshift_hook.run(truncate_dimension_table)

        # Inert into data
        # Log information
        self.log.info(f"Starting to insert {self.table_name}")

        sql_statement_render = self.sql_statement.format(**context)
        
        # Execute insert table
        insert_dimension_data = LoadDimensionOperator.insert_table.format(
            redshift_schema=self.redshift_schema,
            table_name=self.table_name,
            column_names=self.column_names[0],
            source_sql_statemnet=sql_statement_render
        )
        redshift_hook.run(insert_dimension_data)