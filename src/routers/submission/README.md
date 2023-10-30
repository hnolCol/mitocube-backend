

```python
class NewSubmission(BaseModel):
    """Add a submission"""
    sampleNames : List[str]
    collaborators : List[PublicUser]
    attributeTable : List[Dict[str,List[Attribute]]]
    metatext : Dict[str,str]
    label : str = Field(...,min_length=10, max_length=10)
    title : str 
    datasetAttributeValues : Dict[str,List[Attribute]]
    datasetAttributes : List[Attribute]
    samplesAttributes : List[Dict]

##Example+

```