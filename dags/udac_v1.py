import json
import logging
from datetime import datetime, timedelta

from airflow.models import DAG
from airflow.utils.task_group import TaskGroup
from airflow.operators.dummy import DummyOperator

from operators import (StageToRedshiftOperator,
                       LoadFactOperator,
                       LoadDimensionOperator,
                       DataQualityOperator)

from helpers import SqlQueries

default_args = {
    'owner': 'udacity',
    'depends_on_past': False,
    'start_date': datetime(2019, 1, 12),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'email_on_retry': False
}

# Setting of configuration
S3_BUCKET = 'udacity-dend'
REDSHIFT_SCHEMA = 'public'
REDSHIFT_CONN_ID = 'redshift'
FORMAT_JSON = 's3://udacity-dend/log_json_path.json'


# Table of configuration
tables_string = \
    '''
{
          "stage_tables": [
            {
                "log_data": "staging_events",
                "song_data": "staging_songs"
            }
          ],
          "fact_table": [
              {
                  "table_name": "songplays",
                  "columns": ["playid, start_time, userid, level, songid, artistid, sessionid, location, user_agent"]
              }
          ],
          "dimension_table": [
              {
                  "table_name": "songs",
                  "columns": ["songid, title, artistid, year, duration"]
              },
              {
                  "table_name": "users",
                  "columns": ["userid, first_name, last_name, gender, level"]
              },
              {
                  "table_name": "time",
                  "columns": ["start_time, hour, day, week, month, year, weekday"]
              },
              {
                  "table_name": "artists",
                  "columns": ["artistid, name, location, lattitude, longitude"]
              }
          ]
}
'''


# Load data from json format string
data = json.loads(tables_string)

# Tis is the main of task DAG
with DAG('udac_new_v1_dag',
         default_args=default_args,
         description='Load and transform data in Redshift with Airflow',
         schedule_interval='0 * * * *',
         max_active_runs=1,
         catchup=False,
         tags=['test_v1']
         ) as dag:

    # First of whole ETL workflow
    start_operator = DummyOperator(
        task_id='Begin_execution'
    )

    # stage_events and stage_songs
    # task_udac_new_v1_dag_loadDataFromS3ToTrips
    with TaskGroup(group_id="task_StageToRedshift") as task_group_StageToRedshift:
        for stage_table in data["stage_tables"]:
            for source_data, stageing_table in stage_table.items():
                if source_data in 'log_data':

                    logging.info(
                        f"Starting to load data from s3 to Redshift(log): {stageing_table}")

                    process_stage_log_tables = StageToRedshiftOperator(
                        task_id=f"Stage_{stageing_table}",
                        s3_bucket=S3_BUCKET,
                        s3_key=source_data,
                        redshift_conn_id=REDSHIFT_CONN_ID,
                        table_name=stageing_table,
                        copy_json_option=FORMAT_JSON
                    )
                else:
                    logging.info(
                        f"Starting to load data from s3 to Redshift(songs): {stageing_table}")

                    process_stage_songs_tables = StageToRedshiftOperator(
                        task_id=f"Stage_{stageing_table}",
                        s3_bucket=S3_BUCKET,
                        s3_key=source_data,
                        redshift_conn_id=REDSHIFT_CONN_ID,
                        table_name=stageing_table
                    )

    # load data from s3 and staging tables to Redshift (Fact table: songplays)
    for fact_table in data["fact_table"]:
        # Display executing log
        # songplays
        logging.info(f"Loading data to fact table: {fact_table['table_name']}")
        # Building a load fact operator of DAG task
        process_load_fact_operator = LoadFactOperator(
            task_id=f"load_{fact_table['table_name']}_fact_table",
            redshift_conn_id=REDSHIFT_CONN_ID,
            table_name=fact_table['table_name'],
            column_names=fact_table['columns'],
            sql_statement=getattr(
                SqlQueries, f"{fact_table['table_name']}_table_insert"),
            redshift_schema=REDSHIFT_SCHEMA,
            is_truncate_table=True
        )

    # load data from s3 to Redshift (Dimension table: song, user, time, artist)
    # task_udac_new_v1_dag_group_Dimension_table
    with TaskGroup(group_id="task_Dimension_table") as task_group_Dimension_table:
        for dimension_table in data["dimension_table"]:

            logging.info(
                f"Loading data to dimension table: {dimension_table['table_name']}")

            process_dimension_tables = LoadDimensionOperator(
                task_id=f"load_{dimension_table['table_name']}_dim_table",
                redshift_conn_id=REDSHIFT_CONN_ID,
                table_name=dimension_table['table_name'],
                column_names=dimension_table['columns'],
                sql_statement=getattr(
                    SqlQueries, f"{dimension_table['table_name']}_table_insert"),
                redshift_schema=REDSHIFT_SCHEMA,
                is_truncate_table=True
            )

    # data quality
    run_quality_checks = DataQualityOperator(
        task_id="Run_data_quality_checks",
        redshift_conn_id=REDSHIFT_CONN_ID,
        table_name=tables_string
    )

    # end of ETL airflow
    end_operator = DummyOperator(
        task_id='Stop_execution'
    )

    # ETL workflow of Sparkify company
    start_operator >> task_group_StageToRedshift >> process_load_fact_operator
    process_load_fact_operator >> task_group_Dimension_table >> run_quality_checks >> end_operator
