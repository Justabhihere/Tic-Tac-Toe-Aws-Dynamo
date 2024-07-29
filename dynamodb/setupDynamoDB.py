import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from urllib2 import urlopen
import json

def getDynamoDBConnection(config=None, endpoint=None, port=None, local=False, use_instance_metadata=False):
    if local:
        # Connect to local DynamoDB
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url='http://{}:{}'.format(endpoint, port)
        )
    else:
        try:
            session = boto3.Session()  # Create a session to use the default profile or environment variables
            dynamodb = session.resource('dynamodb')
        except NoCredentialsError:
            print("No AWS credentials found.")
            raise
        except PartialCredentialsError:
            print("Incomplete AWS credentials.")
            raise
        except Exception as e:
            print("Error connecting to DynamoDB: {}".format(e))
            raise

    return dynamodb

def createGamesTable(dynamodb):
    try:
        # Create the DynamoDB client
        client = dynamodb.meta.client

        # Define the global secondary indexes
        global_indexes = [
            {
                'IndexName': 'HostId-StatusDate-index',
                'KeySchema': [
                    {'AttributeName': 'HostId', 'KeyType': 'HASH'},
                    {'AttributeName': 'StatusDate', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                }
            },
            {
                'IndexName': 'OpponentId-StatusDate-index',
                'KeySchema': [
                    {'AttributeName': 'OpponentId', 'KeyType': 'HASH'},
                    {'AttributeName': 'StatusDate', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                }
            }
        ]

        # Create the table
        table = dynamodb.create_table(
            TableName='Games',
            KeySchema=[
                {'AttributeName': 'GameId', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'GameId', 'AttributeType': 'S'},
                {'AttributeName': 'HostId', 'AttributeType': 'S'},
                {'AttributeName': 'OpponentId', 'AttributeType': 'S'},
                {'AttributeName': 'StatusDate', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            },
            GlobalSecondaryIndexes=global_indexes
        )

        # Wait until the table exists
        table.meta.client.get_waiter('table_exists').wait(TableName='Games')

        print("Table {} created.".format(table.table_name))
        return table

    except Exception as e:
        print("Error creating table: {}".format(e))
        raise
