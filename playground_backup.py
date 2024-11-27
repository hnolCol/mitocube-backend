from __future__ import annotations

from abc import abstractmethod
from typing import Type, Self, Dict

# from datetime import datetime, timedelta
# from typing import List, Dict, Self  # , Any
# from deprecated import deprecated

import lib.data as dlib

db: dlib.ABCDatabase = dlib.ABCDatabase.get_class()

ds: dlib.ABCDatabase = dlib.ABCDataset.get_class()

at: dlib.ABCAttribute = dlib.ABCAttribute.get_class()

tr: dlib.ABCTrait = dlib.ABCTrait.get_class()

attributes = at.get_all_attributes()
print(attributes)

traits = tr.get_all_traits()
print(traits)

for db_id, trait in traits.items():
    print(trait.get_full_tag())

print(db.query_trait_ids(trait_query="heart",
                         trait_tags=["att_tissue:muscle"]))

traits[367].get_full_tag()

db: dlib.ABCDatabase = dlib.ABCDatabase.get_class()
ids, labels = db.query_datasets_ids(query = "CLPB", limit_to_n = 42, limit_offset=0)

print(db.query_datasets_ids(query = "JC15", limit_to_n = 42, limit_offset=0))
print(db.query_datasets_ids(feature_keys = ["A2A484"], limit_to_n = 42, limit_offset=0))

# print(db.query_datasets_ids(trait_tags = ["att_organ:heart"], limit_to_n = 42, limit_offset=13))
# print(db.query_datasets_ids(trait_ids = [42, 69], limit_to_n = 42, limit_offset=13))
# print(db.query_datasets_ids(states = [1,2,3], trait_ids = [42, 69], feature_keys = ["BCL2", "sdkjflsd"], limit_to_n = 42, limit_offset=13))  # ToDO: states not working


print(" > This is the End <")
