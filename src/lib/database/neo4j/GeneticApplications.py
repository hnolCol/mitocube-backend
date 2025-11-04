from lib.database.abstract.GeneticApplications import GeneticApplicationsABC




class Neo4JGeneticApplications(GeneticApplicationsABC):
    
    def insert(self, gene_application):
        return super().insert(gene_application)
    
    def get(self, tag):
        return super().get(tag)