from config.enums.units import UnitsEnum 
from config.models.unit import UnitTypeInputModel
from typing import Dict  
 
def extract_user_input(userInput : Dict[UnitsEnum,UnitTypeInputModel]): 
    "Creates a list to be easily inserted into the DB"
    r = []
    for unittype, user_input in userInput.items():
        #feature 
        if isinstance(user_input.value,list):
            for v in user_input.value:
                unit_props = {
                "unittype_tag" : unittype.value,
                "unit_tag" : user_input.unit_tag, 
                "value" : v,
                        }
            r.append(unit_props)
        #others 
        else:
            unit_props = {
                "unittype_tag" : unittype.value, 
                "unit_tag" : user_input.unit_tag, 
                "value" : user_input.value,
                        }
            r.append(unit_props)
    return r 