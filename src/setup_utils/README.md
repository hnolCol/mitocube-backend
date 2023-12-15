# Utility functions to initiate the backend

Utility function that should be called on initiation of the web server backend. 


# Proteome AnnotationSettings

In order to retrieve the uniprot proteome annotations, please follow these steps:

- Enter all uniport proteome id (upid, example: UP000000437) in the files BaseSettings: /config/settings/proteomes/annotationsettings.py 
- A Proteome is defined by a BaseModel and requires the following information.

```python

class Proteome(BaseModel):

    upid : str 
    domain : List[str] = []
    name : str 

```

