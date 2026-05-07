from neo4j import Driver, Result 
from typing import List, Dict
import pandas as pd 
from services.random_generators import get_random_string
from config.models.instruments import InstrumentStateModel, InstrumentsStateResponseModel, InstrumentStateHistoryModel

from lib.database.abstract.Instruments import InstrumentsABC
from lib.database.abstract.Instruments import InstrumentStatesABC

import itertools

class Neo4JInstrumentStates(InstrumentStatesABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
    
    def _utils_insert_from_file(self, file_path : str =  "/Users/PParsa/Documents/GitHub/mitocube-backend/resources/maintenance/instrumentstates.txt", *args, **kwargs):
        
        instrument_states = pd.read_csv(file_path, *args, **kwargs)
        if not all(column_name in instrument_states.columns for column_name in ["tag","text","description","color"]):
            raise ValueError("The dataframe does not have all required columns. 'tag','text','description','color'")
        
        instrument_state_models = [InstrumentStateModel(**i) for i in instrument_states.to_dict(orient="records")]
        query = (
            "UNWIND $states as is_props "
            "MERGE (is:InstrumentState {tag : is_props.tag}) "
            "ON CREATE "
            "SET is.description = is_props.description, is.text = is_props.text, is.color = is_props.color, is.created_at = timestamp() "
            "ON MATCH "
            "SET is.description = is_props.description, is.text = is_props.text, is.color = is_props.color, is.modified = timestamp() "
            "RETURN count(is) "
        )
        
        r = self._driver.execute_query(query,routing_="w", states = [i_state.model_dump() for i_state in instrument_state_models])
        print(r,"Instrument States created.")
        
        
    def exists(self, tag : str) -> bool:
        ""
        query = "MATCH (is:InstrumentState {tag : $tag}) RETURN count(is) > 0"
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return r[0] if isinstance(r[0], bool) else False
        
    def get(self, tag = None) -> InstrumentStateModel:
        ""
        
        query = (
            "MATCH (is:InstrumentState {tag : $tag}) "
            "RETURN {tag : is.tag, text : is.text, description : is.description, color : is.color} "
        )
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return InstrumentStateModel(**r[0])
        
    def get_instrument_state(self, instrument_tag : str, limit : int = 1) -> List[str]:
        "Returns the state "
            
        query = (
            "MATCH (instrument:Trait {tag : $instrument_tag})<-[:HAS_TRAIT]-(a:Attribute) WHERE EXISTS {(a)-[:PART_OF]->(ag:AttributeGroup {tag : 'instrument'})} "
            "MATCH (instrument)-[r:IN_STATE]-(is:InstrumentState) "
            "RETURN is.tag ORDER BY r.created_at DESC "
        )
        
        if limit is not None:
            query += " LIMIT $limit"
            
        r = self._driver.execute_query(query,instrument_tag = instrument_tag, result_transformer_=Result.value, limit = limit)

        return r
    
    
    def get_state_durations(self, instrument_tag : str = None, state_tag : str = None, timestamp_min : float = None, timestamp_max : float = None, limit : int = None) -> List[InstrumentStateHistoryModel]:
        ""
        query = "MATCH (t:Trait)-[r:IN_STATE]->(state:InstrumentState) "
        if instrument_tag is not None:
            query += "WHERE t.tag = $instrument_tag "
            if timestamp_max is not None or timestamp_min is not None or state_tag is not None:
                query += "AND "
        elif timestamp_max is not None or timestamp_min is not None:
            query += "WHERE "
        elif state_tag is not None:
            query += "WHERE state.tag = $state_tag "
        
        if timestamp_min is not None and timestamp_max is not None:
            query += (      
                "r.created_at >= $timestamp_min AND r.created_at <= $timestamp_max ")
        elif timestamp_min is not None:
            query += (      
            "r.created_at >= $timestamp_min ")
        elif timestamp_max is not None:
            query += (      
            "r.created_at <= $timestamp_max ")

            
        query += "WITH t, state, r.tag as tag, r.created_at AS created ORDER BY created ASC " 
        
        if limit is not None:
            query += " LIMIT $limit "
        
        query += (
            "WITH COLLECT({tag : tag, instrument_tag : t.tag, state : state.tag, created_at : created}) as l  "
            "WITH [idx IN range(0, size(l)-1) |  "
            "       { "
            "           tag : l[idx].tag, "
            "           started_at : l[idx].created_at, "
            "           ended_at : l[idx+1].created_at, "
            "           instrument_tag : l[idx].instrument_tag, "
            "           state_tag : l[idx].state, "
            "           duration : (l[idx+1].created_at-l[idx].created_at) "
            "       }] AS durations "
            "RETURN durations "
        )
        
        r = self._driver.execute_query(query, instrument_tag = instrument_tag, limit = limit, routing_= "r", result_transformer_=Result.value)
        return [InstrumentStateHistoryModel(**ri) for ri in r[0]]
    
    
    def get_fractional_state_durations(self, instrument_tag : str = None, state_tag : str = None, timestamp_min : float = None, timestamp_max : float = None, limit : int = None, end_time : pd.Timestamp = None, time_period : str = 'M') -> pd.DataFrame:
        
        "" 
        
        query = "MATCH (t:Trait)-[r:IN_STATE]->(state:InstrumentState) "
        if instrument_tag is not None:
            query += "WHERE t.tag = $instrument_tag "
            if timestamp_max is not None or timestamp_min is not None or state_tag is not None:
                query += "AND "
        elif timestamp_max is not None or timestamp_min is not None:
            query += "WHERE "
        elif state_tag is not None:
            query += "WHERE state.tag = $state_tag "
                
        if timestamp_min is not None and timestamp_max is not None:
            query += (      
                "r.created_at >= $timestamp_min AND r.created_at <= $timestamp_max ")
        elif timestamp_min is not None:
            query += (      
            "r.created_at >= $timestamp_min ")
        elif timestamp_max is not None:
            query += (      
            "r.created_at <= $timestamp_max ")
            
        query += "RETURN t.tag AS instrument_tag, state.tag AS state_tag,  apoc.date.format(r.created_at, 'ms', 'yyyy-MM-dd HH:mm:ss') AS created_at ORDER BY instrument_tag, created_at "
        if limit is not None:
            query += " LIMIT $limit "
        df = self._driver.execute_query(query, instrument_tag = instrument_tag, limit = limit, routing_= "r", result_transformer_=Result.to_df)
        df = df.sort_values(["instrument_tag", "created_at"])

        # Use now if not provided
        if end_time is None:
            end_time = pd.Timestamp.utcnow().tz_convert('UTC')
            
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)

        # Sort
        df = df.sort_values(['instrument_tag', 'created_at'])

        # Compute next timestamp per instrument
        df['next_time'] = df.groupby('instrument_tag')['created_at'].shift(-1)

        # Fill last state (or single-state instruments) with current UTC time
        df['next_time'] = df['next_time'].fillna(end_time)

        # Compute duration in seconds
        df['duration'] = (df['next_time'] - df['created_at']).dt.total_seconds()

        # Remove invalid zero-length durations
        df = df[df['duration'] > 0]

        # -----------------------------
        # 4️⃣ Expand durations into monthly buckets
        # -----------------------------
        rows = []

        for _, row in df.iterrows():
            start = row['created_at']
            end = row['next_time']
            current = start

            while current < end:
                # first moment of next month
                month_end = (current.to_period(time_period) + 1).to_timestamp().tz_localize('UTC')
                slice_end = min(end, month_end)
                seconds = (slice_end - current).total_seconds()

                rows.append({
                    'instrument_tag': row['instrument_tag'],
                    'state': row['state_tag'],
                    'year': current.year,
                    'month': current.month,
                    'seconds': seconds
                })

                current = slice_end

        expanded = pd.DataFrame(rows)

        if expanded.empty:
            print("No data after expansion")
            exit()

        # Aggregate per instrument × month × state
        agg = expanded.groupby(['instrument_tag', 'year', 'month', 'state'], as_index=False)['seconds'].sum()

        
        expanded['period'] = pd.PeriodIndex(year=expanded['year'], month=expanded['month'], freq=time_period)

        agg['period'] = pd.PeriodIndex(year=agg['year'], month=agg['month'], freq=time_period)



        # -----------------------------
        # Fill missing months and states
        # -----------------------------
        all_months = pd.period_range(expanded['period'].min(), expanded['period'].max(), freq=time_period)
        instruments = expanded['instrument_tag'].unique()
        states = expanded['state'].unique()

        # Build full grid
        full_index = pd.MultiIndex.from_tuples(
            list(itertools.product(instruments, all_months, states)),
            names=['instrument_tag', 'period', 'state']
        )
        full_df = pd.DataFrame(index=full_index).reset_index()

        # Merge with actual data
        merged = full_df.merge(agg, how='left', 
                            on=['instrument_tag', 'period', 'state'])

        merged['seconds'] = merged['seconds'].fillna(0)

        # -----------------------------
        # Compute fractions per instrument × month
        # -----------------------------
        merged['fraction'] = merged.groupby(['instrument_tag', 'period'])['seconds'].transform(lambda x: x / x.sum())

        # Optional: split period into year/month columns
        merged['year'] = merged['period'].dt.year
        merged['month'] = merged['period'].dt.month
        merged['day'] = merged['period'].dt.day
        merged = merged.drop(columns='period')
        
        print(merged)
        return merged
                

                

    
    def find(self, search_string = None, limit : int = None) -> List[str]:
        
        query = "MATCH (is:InstrumentState)  " 
        
        if search_string is not None:
            query += "WHERE toLower(is.text) CONTAINS toLower($search_string) OR toLower(is.description) CONTAINS toLower($search_string) "
            
        query += "RETURN is.tag "
        
        if limit is not None:
            query += "LIMIT $limit "
            
        r = self._driver.execute_query(query, search_string = search_string, limit = limit, routing_="r", result_transformer_=Result.value) 
        return r 
        


    def insert(self, state):
        return super().insert(state)
    
    
    def set_state(self, tag : str, instrument_tag : str, comment : str = None):
        ""
        
        unique_tag = get_random_string(N = 10)
        
        query = (
            "MATCH (is:InstrumentState {tag : $tag}) "
            "MATCH (instrument:Trait {tag : $instrument_tag})<-[:HAS_TRAIT]-(a:Attribute) WHERE EXISTS {(a)-[:PART_OF]->(ag:AttributeGroup {tag : 'instrument'})} "
            "CREATE (is)<-[r:IN_STATE]-(instrument) "
            "SET r.created_at = timestamp(), r.comment = $comment, r.tag = $r_tag "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag, instrument_tag = instrument_tag, comment = comment, r_tag = unique_tag)
        

class Neo4JInstruments(InstrumentsABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
        
    def get_types(self, limit: int = 50) -> List[dict]:
        """Returns all the instrument type tags with their display text"""
        query = (
            "MATCH (ag:AttributeGroup)<-[:PART_OF]-(a:Attribute) "
            "WHERE ag.tag = 'instrumenttype' "
            "RETURN {tag: a.tag, text: a.text} "
            "LIMIT $limit"
        )
        
        instrument_types = self._driver.execute_query(
            query, 
            routing_="r",
            result_transformer_=Result.value, 
            limit=limit
        )
        
        return instrument_types


    def get(self, instrument_type: str = None, tags: List[str] = None) -> List[dict]:
        """Returns instruments with tag and text"""
        
        query = (
            "MATCH (ag:AttributeGroup)<-[:PART_OF]-(a:Attribute) WHERE ag.tag = 'instrument' "
        )
        
        if instrument_type is not None:
            query += "AND EXISTS {(:AttributeGroup {tag : 'instrumenttype'})<-[:PART_OF]-(a_type:Attribute)-[:IS_CHILD]->(a) WHERE a_type.tag = $instrument_type} "
        
        query += "MATCH (a)-[:HAS_TRAIT]->(t:Trait) RETURN {tag: t.tag, text: t.text} "

        r = self._driver.execute_query(
            query, 
            routing_="r", 
            result_transformer_=Result.value, 
            instrument_type=instrument_type
        )
        
        return r
        
    def get_samples_by_instrument(self, tags: List[str]) -> Dict:
        ""
        
        query = (
            "MATCH (av:AttributeValue) "
            "WHERE av.tag in $tags "
            "MATCH (av)<-[:HAS_ATTRIBUTE_VALUE]-(submission:Submission)-[:HAS_SAMPLE]->(sample:Sample) "
            "WHERE EXISTS {(sample)-[:QUANTIFIED]->(:Protein)} "
            "RETURN av.tag as instrument_tag, submission.tag as submission_tag, count(sample) as sample_count"
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, tags=tags)
        
        return r 
        
        
    def get_counts_by_instrument_and_attribute(self, attribute_tags : List[str], tags : List[str] = None):
        "" 
        query = (
            "MATCH (instrument:AttributeValue)-[:HAS_VALUE]-(a:Attribute) "
            "WHERE a.tag = 'att_ms' "
        )
        
        if tags is not None:
            query += "AND instrument.tag in $tags "
            
        query += (
            "MATCH (instrument)<-[:HAS_ATTRIBUTE_VALUE]-(submission:Submission) "
            "MATCH (submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a2:Attribute)-[:HAS_TRAIT]->(av:Trait) "
            "WHERE a2.tag in $attribute_tags "
            "MATCH (submission)-[:HAS_SAMPLE]->(sample:Sample) "
            "RETURN instrument.tag as instrument_tag, a2.tag as attribute_tag, av.tag as trait_tag, submission.tag as submission_tag, count(sample) as sample_count "
        )
        
        
        r = self._driver.execute_query(query, routing_="r",result_transformer_=Result.data, tags = tags, attribute_tags = attribute_tags)
        
        return r 
    
    def costs(self, instrument_tag  : str = None, timestamp_min : float = None, timestamp_max : float = None) -> float:
        """ Returns sum costs of maintenance events for a specific instrument"""

        query = "MATCH (me:MaintenanceEvent)<-[r:HAS_EVENT]-(t:Trait) "
        if any([instrument_tag is not None, timestamp_min is not None, timestamp_max is not None]):
            query += "WHERE "
            
            if instrument_tag  is not None:
                query += " t.tag = $instrument_tag  AND EXISTS {(ag:AttributeGroup)<-[:PART_OF]-(a:Attribute)-[:HAS_TRAIT]->(t) WHERE ag.tag = 'instrument'} "
            
            if timestamp_min is not None:
                if instrument_tag is not None:
                    query += "AND "
                query += "me.created_at >= $timestamp_min "
            if timestamp_max is not None:
                if instrument_tag is not None or timestamp_min is not None:
                    query += "AND "
                query += "me.created_at <= $timestamp_max "
        
        query += "RETURN sum(me.costs)"
        
        r = self._driver.execute_query(query, 
                                       instrument_tag  = instrument_tag , 
                                       timestamp_max = timestamp_max,
                                       timestamp_min = timestamp_min,
                                       routing_= "r", 
                                       result_transformer_ = Result.value)
        if len(r) == 0: return None # No maintenance events found for instrument tag.
        return r[0]