import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.utils.task_group import TaskGroup
from airflow.operators.dummy import DummyOperator
from httpx import get

from operators import (StageToRedshiftOperator,
                       LoadFactOperator,
                       LoadDimensionOperator,
                       DataQualityOperator)

from helpers import SqlQueries

default_args = {
    'owner': 'udacity',
    'depends_on_past': False,
    'start_date': datetime(2019, 1, 12),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True
}

# Setting of configuration
S3_BUCKET = 'udacity-dend'
REDSHIFT_SCHEMA = 'public'
REDSHIFT_CONN_ID = 'redshift'
FORMAT_JSON = 's3://udacity-dend/log_json_path.json'


# Table of configuration
stage_tables = {'log_data': 'staging_events',
                'song_data': 'staging_songs'}
tables = {
    'fact_table':
        {'songplays': 'playid, start_time, userid, level, songid, artistid, sessionid, location, user_agent'},
    'dimension_table':
        {'songs': 'songid, title, artistid, year, duration',
         'users': 'userid, first_name, last_name, gender,level',
         'artists': 'artistid, name, location, lattitude, longitude',
         'time': 'start_time, hour, day, week, month , year, weekday'}
}


# This main of task DAG
with DAG('udac_example_dag',
         default_args=default_args,
         description='Load and transform data in Redshift with Airflow',
         schedule_interval='0 * * * *',
         max_active_runs=1,
         catchup=False,
         tags=['udacity_project_main_DAG']
         ) as dag:

    # First of whole ETL workflow
    start_operator = DummyOperator(
        task_id='Begin_execution'
    )

    # stage_events and stage_songs
    with TaskGroup(group_id="task_loadDataFromS3ToTrips") as task_group_StageToRedshift:
        for stage_table_source, stage_table_name in stage_tables.items():
            if stage_table_source in 'log_data':
                logging.info(f"Starting to load data from s3 to Redshift(log): {stage_table_name}")
                StageToRedshiftOperator(
                    task_id=f"Stage_{stage_table_name}",
                    s3_bucket=S3_BUCKET,
                    s3_key=stage_table_source,
                    redshift_conn_id=REDSHIFT_CONN_ID,
                    table_name=stage_table_name,
                    copy_json_option=FORMAT_JSON
                )
            else:
                logging.info(
                    f"Starting to load data from s3 to Redshift(songs): {stage_table_name}")
                StageToRedshiftOperator(
                    task_id=f"Stage_{stage_table_name}",
                    s3_bucket=S3_BUCKET,
                    s3_key=stage_table_source,
                    redshift_conn_id=REDSHIFT_CONN_ID,
                    table_name=stage_table_name
                )

    # load data from s3 and staging tables to Redshift (Fact table: songplays)
    for start_schema_table, table_columns in tables.items():
        if start_schema_table in 'fact_table':
            for fact_table in table_columns:
                logging.info(f"Loading data to dimension table: {fact_table}")
                load_fact_operator = LoadFactOperator(
                    task_id=f"load_{fact_table}_fact_table",
                    redshift_conn_id=REDSHIFT_CONN_ID,
                    table_name=fact_table,
                    column_name=table_columns[fact_table],
                    sql_statement=getattr(
                        SqlQueries, f"{fact_table}_table_insert"),
                    redshift_schema=REDSHIFT_SCHEMA,
                    is_truncate_table=True
                )

    # load data from s3 to Redshift (Dimension table: song, user, time, artist)
    with TaskGroup(group_id="task_group_Dimension_table") as task_group_Dimension_table:
        for start_schema_table, table_columns in tables.items():
            if start_schema_table == 'dimension_table':
                for dimension_table in table_columns:
                    logging.info(
                        f"Loading data to dimension table: {dimension_table}")
                    LoadDimensionOperator(
                        task_id=f"load_{dimension_table}_dim_table",
                        redshift_conn_id=REDSHIFT_CONN_ID,
                        table_name=dimension_table,
                        column_name=table_columns[dimension_table],
                        sql_statement=getattr(
                            SqlQueries, f"{dimension_table}_table_insert"),
                        redshift_schema=REDSHIFT_SCHEMA,
                        is_truncate_table=True
                    )

    # data quality
    run_quality_checks = DataQualityOperator(
        task_id="Run_data_quality_checks",
        redshift_conn_id=REDSHIFT_CONN_ID,
        table_name=[table_name for fact_dimension, table_names in tables.items() for table_name in table_names]
    )

    # end of ETL airflow
    end_operator = DummyOperator(
        task_id='Stop_execution'
    )

    # ETL workflow of Sparkify company
    start_operator >> task_group_StageToRedshift >> load_fact_operator
    load_fact_operator >> task_group_Dimension_table >> run_quality_checks >> end_operator
