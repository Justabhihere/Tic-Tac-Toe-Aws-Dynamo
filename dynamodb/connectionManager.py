import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from setupDynamoDB import getDynamoDBConnection, createGamesTable

class ConnectionManager:

    def __init__(self, mode='service', config=None, endpoint=None, port=None, use_instance_metadata=''):
        self.dynamodb = getDynamoDBConnection(config=config, endpoint=endpoint, port=port, local=(mode == 'local'), use_instance_metadata=use_instance_metadata)
        self.gamesTable = None
        self.setupGamesTable()

    def setupGamesTable(self):
        try:
            # Retrieve the table if it exists
            self.gamesTable = self.dynamodb.Table('Games')
            self.gamesTable.load()  # Load the table metadata to check if it exists
        except self.dynamodb.meta.client.exceptions.ResourceNotFoundException:
            # Table does not exist; create it
            self.gamesTable = createGamesTable(self.dynamodb)

    def getGamesTable(self):
        if self.gamesTable is None:
            self.setupGamesTable()
        return self.gamesTable

    def createGamesTable(self):
        self.gamesTable = createGamesTable(self.dynamodb)

    def checkIfTableIsActive(self):
        try:
            self.getGamesTable()  # Ensure the table is loaded
            return self.gamesTable.table_status == 'ACTIVE'
        except Exception as e:
            print("Error checking table status: {}".format(e))
            return False
