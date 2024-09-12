
from typing import List, Dict 

from lib.data.database.abstract.Database import DatabaseABC 

from lib.data.database.neo4j.Proteomes import Neo4JProteomes
from lib.data.database.neo4j.Attributes import Neo4JAttributes
from lib.data.database.neo4j.Dataset import Neo4JDataset
from lib.data.database.neo4j.Filters import Neo4JFilter
from lib.data.database.neo4j.Submission import Neo4JSubmissionFilter, Neo4JSubmissions
from lib.data.database.neo4j.Meta import Neo4JMetaHandler
from lib.data.database.neo4j.Users import Neo4JUser
from lib.data.database.neo4j.Features import Neo4JFeatures
from lib.data.database.neo4j.Genotypes import Neo4JGenotype
from lib.data.database.neo4j.News import Neo4JNews
from lib.data.database.Neo4JDatabase import Neo4JFactory, Neo4JConnection, Neo4JConstructor


from config.models.submissions.submissions import DatasetSubmissionModel

import pandas as pd 
class MCNeo4JDatabase(DatabaseABC):
    
    
    def __init__(self):
        
        self.connection = Neo4JConnection()
        self._driver = self.connection.driver
        self.factory = Neo4JFactory(driver=self.connection.driver)
        self.constructor = Neo4JConstructor(driver=self.connection.driver)
        self.attributes = Neo4JAttributes(driver=self.connection.driver)
        self.meta = Neo4JMetaHandler(driver=self.connection.driver, attributes=self.attributes)
        self.datasets = Neo4JDataset(driver=self.connection.driver, meta=self.meta)
        
        self.users = Neo4JUser(driver=self.connection.driver)
        self.features = Neo4JFeatures(driver=self.connection.driver)
        self.filters = Neo4JFilter(driver=self.connection.driver)
        #self.calcs = Neo4JCalculations(driver=self.connection.driver, feature=self.features)
        self.submission_filter = Neo4JSubmissionFilter(driver=self.connection.driver)
        self.genotypes = Neo4JGenotype(driver=self.connection.driver)
        self.proteomes = Neo4JProteomes(driver = self.connection.driver)
        self.submissions = Neo4JSubmissions(driver = self.connection.driver, meta=self.meta)
        self.news = Neo4JNews(driver=self.connection.driver)
        
        #checks if all is correctly defined 
        super(MCNeo4JDatabase, self).__init__()
        
        #self.proteomes.get()
        
        #self.constructor._add_states()
        #self.constructor._add_user_roles()
        self.constructor.set_up_attributes()
        

    def get_feature_data(self, tag : str) -> List[Dict]:
        """Returns the feature (protein) data
        by its tag.

        Parameters
        ----------
        tag : str
            The feature tag 

        Returns
        -------
        List[Dict]
            The data 
            TODO: Define model on how the data should be returned ! 
        """
        
        
    
        

DB = MCNeo4JDatabase()
