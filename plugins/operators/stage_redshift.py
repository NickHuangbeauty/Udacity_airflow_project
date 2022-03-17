from airflow.models import BaseOperator
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook
from airflow.providers.postgres.hooks.postgres import PostgresHook


class StageToRedshiftOperator(BaseOperator):
    """
    Purpose:
        1. Create table: trips and stations
        2. Copy data from s3 to Redshift

    :param s3_bucket:              s3 bucket name
    :type s3_bucket                str
    :param s3_key                  log_data and song_data
    :type s3_key                   str
    :param redshift_conn_id        Redshift connection id
    :type redshift_conn_id         str
    :param table_name              Destination table name
    :type table_name               str
    :param redshift_schema         Redshift default schema
    :type redshift_schema          str
    :param copy_json_option        json format option
    :type copy_json_option         str
    """

    # Setting the task background color
    # RPG: 53, 129, 64 -> Green
    ui_color = '#358140'

    # template_fields
    template_fields = ("s3_key",)

    # truncate_table statement
    truncate_table = \
        """
        TRUNCATE TABLE {redshift_schema}.{table_name}
        """

    # copy sql statement
    copy_sql = \
        """
        COPY {table_name}
        FROM 's3://{s3_bucket}/{s3_key}'
        ACCESS_KEY_ID '{ACCESS_KEY}'
        SECRET_ACCESS_KEY '{SECRET_KEY}'
        FORMAT AS JSON '{FORMAT_JSON}'
        REGION AS '{REGIN}'
        """

    def __init__(self,
                 *,
                 s3_bucket: str = '',
                 s3_key: str = '',
                 redshift_conn_id: str = '',
                 table_name: str = '',
                 redshift_schema: str = 'public',
                 copy_json_option: str = 'auto',
                 **kwargs):
        super().__init__(**kwargs)
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.redshift_conn_id = redshift_conn_id
        self.table_name = table_name
        self.redshift_schema = redshift_schema
        self.copy_json_option = copy_json_option

    def execute(self, context) -> None:
        """
        Purpose:
            Truncate and copy data from s3 to Redshift after access Redshift.
        :param context: to read config values
        :return: None
        """

        self.log.info("Starting to set aws redshift connection")
        access_key, secret_key, redshift_hook = self.__secret_key__()

        # truncate table
        self.log.info(f"Starting to truncate table, table name: {self.table_name}!")
        self.truncate_stage_table(redshift_hook)

        # Copy data from s3 to Redshift
        self.log.info(f"Starting to copy data from S3 to Redshift table, table name: {self.table_name}!")
        self.copy_data(access_key, secret_key, redshift_hook, context)

    def __secret_key__(self):
        """
        Purpose:
            Building all access AWS and Redshift connection key and credentials.
        :return: access key, secret key and redshift hook
        """
        aws_hooks = AwsBaseHook('aws_credentials', client_type=self.redshift_conn_id)
        credentials = aws_hooks.get_credentials()
        redshift_hook = PostgresHook(postgres_conn_id=self.redshift_conn_id)
        return credentials.access_key, credentials.secret_key, redshift_hook

    def copy_data(self, access_key, secret_key, redshift_hook, context) -> None:
        """
        Purpose:
            Copy source data from s3 to redshift
            Source: 1. event data
                    2. songs data
            Destination:
                    Redshift
                    Database Name: dev
                    User: awsuser
                    Tables:
                        Stage -> 1. staging_events
                              -> 2. staging_songs
                        Fact -> songplays
                        Dimension -> 1. songs
                                  -> 2. users
                                  -> 3. time
                                  -> 4. artists
        :param access_key: access key to connect aws
        :param secret_key: secret key to connect aws
        :param redshift_hook: access Redshift by PostgresHook
        :param context:  to read config values
        :return: None
        """
        self.log.info(f"S3_key.format(**context): {self.s3_key.format(**context)}")

        s3_rendered_key = self.s3_key.format(**context)

        self.log.info("Starting to execute the copy_sql_statement process")
        copy_sql_statement = StageToRedshiftOperator.copy_sql.format(
            table_name=self.table_name,
            s3_bucket=self.s3_bucket,
            s3_key=s3_rendered_key,
            ACCESS_KEY=access_key,
            SECRET_KEY=secret_key,
            FORMAT_JSON=self.copy_json_option,
            REGIN='us-west-2'
        )
        redshift_hook.run(copy_sql_statement)

    def truncate_stage_table(self, redshift_hook):
        """
        Purpose:
            Truncate table before insert into two staging tables
        :param redshift_hook:  access Redshift by PostgresHook
        :return: None
        """
        self.log.info("Starting to execute the truncate_table_sql process")

        truncate_table_sql = StageToRedshiftOperator.truncate_table.format(
            redshift_schema=self.redshift_schema,
            table_name=self.table_name
        )
        redshift_hook.run(truncate_table_sql)