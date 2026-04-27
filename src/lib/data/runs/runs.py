import string
import warnings
from itertools import chain
from datetime import datetime

import pandas as pd 
import numpy as np 
from typing import List, Dict, Any

from config.models.submissions.runs import RunListModel, AnalyticRunModel, RunListResponseModel
from config.models.user import UserModel
from services.date import validate_date_string
from services.random_generators import get_random_string

class RunListCreator:
    """
    Run List Creator Class 

    Create an analytical run list that can be used to actually start the runs in the LC-MS/MS or any other type of
    instrument. Please note that a sample and a run are not the same. If you pool for example two samples, it results
    in a single run. Therefore, you a) define a sample attribute that you can use to ``aggregate_on`` (e.g. pooling samples).
    Moreover, the sample could be fractionated by offline or online methods resulting in more runs than samples. This can
    be set up by defining ``fractionate=True`` and providing the number of fractions by the parameter ``n_fractions``. 

    Parameters
    ----------

    dataset_label : str 
        An unique identifier for the data set. 

    sample_list : pd.DataFrame
        The sample list in which the sample names are the index of the data frame and the columns contain the samples attributes.
        Should be obtained using the MCDataset.getSamplesAttributes() function. 

    aggregated_on : str, optional 
        A column name that is used to aggregate the sample list on. This happens if samples can be pooled, when using SILAC or TMT or easiTAG for protein quantification. 

    free_plate_positions : list[list[list[bool]]]
        List of plates (for example 96, 384) indicating which positions are free using bools. Each plate is again a list
        of lists (row1, row2, row3) where each row (column1, column 2). A 2 x 3 plate with the last well blocked would be:
        ``
        plate = [[True, True, True],[True, True, False]]
        ``
        The plate design can be different but for each plate the number of columns must be equal throughout the rows. 

    rows_first : bool 
        If true, rows will be filled first when creating the run list (e.g. A1, A2 for sample 1 - 2 instead of A1, B1, B2)
        
    scramble : bool, default True
        Scrambles the runs in the ``RunList`` will be in random order. Useful to avoid time batch effects by measuring for example all genotypes in a row while
        the analytical method such as LC-MS/MS performance changes over time. 
    
    scramble_across_plates : bool, default False 
        If scrambled is performance and the number of runs requires that the samples are spread over multiple plates, then the scrambling will be performed within each please (False, default)
        while if ``True`` all runs across plates are scrambled. It defaults to False since some analytical systems can only host a single well plate. 
    
    aggregate_on : str, default None
        The tag of the samples attributes that should be used for aggregating the sample list on. This would mean that you can pool numerous samples together and would result in 
        less runs than samples. As an example, a SILAC based quantification experiment in proteomics could be such an example.

    fractionate : bool, default False 
        If samples are fractionated, than the number of runs is higher than the number of samples. The number of fractions can be defined using ``n_fractions`` parameter. 
    
    n_fractions : int, default 0 
        The number of fractions each sample is fractionated in to. As an example, if an offline fractionation is performed that results in six fractions, each sample then requires
        6 analytical runs. Please note that you can combine this with the ``aggregated_on``parameter which is allows to define a pooling of the sample. As a practical example, 
        assume that a TMT-12 plex quantification strategy is performed, hence the samples are ``aggregated_on`` the TMT-batch and then the pooled samples is fractionated via 
        offline high-pH fractionation, which results in a 24 fractions. 

    add_user_initials : bool, default True
        Adds the initials (e.g. first two characters) of the firstname and lastname to each runname to indicate in the raw/run nanme who created (and started) the run. 
        The resulting run name will be {YYYYMMDD}_{dataset_label}_{user_initials}_....

    Raises
    ----------
    ValueError 
        If *aggregate_on* is not None but is not found in the sample_list pd.DataFrame as a column name.
    ValueError 
        If the number of free_plate_positions contains less True than the number of runs. 
    ValueError
        If the number of columns is different for row within a plate (e.g. different length.)

    """
    def __init__(self, 
                dataset_label : str, 
                sample_list : pd.DataFrame, 
                free_plate_positions : List[List[List[bool]]],
                user : UserModel,
                rows_first : bool = True,
                scramble : bool = True,
                scramble_across_plates : bool = False,
                aggregate_on : str | None = None, 
                fractionate : bool = False, 
                n_fractions : int = 0,
                add_user_initials : bool = True
                ) -> None:
        
        self._dataset_label = dataset_label 
        self._sample_list = sample_list 
        self._aggregated_on = aggregate_on
        self._fractionate = fractionate 
        self._n_fractions = n_fractions
        self._rows_first = rows_first
        self._scramble = scramble
        self._scramble_across_plates = scramble_across_plates
        self._free_plate_positions = free_plate_positions 
        self._user = user
        self._add_user_initials = add_user_initials

        self._check()

    def _check(self) -> None:
        """
        Check user input and raise ValueErrors if parameters do not fit.
        
        Raises
        ----------
        ValueError 
            - If *aggregate_on* is not None but is not found in the sample_list pd.DataFrame as a column name.
            - If the number of free_plate_positions contains less True than the number of runs. 
            - If the number of columns is different for row within a plate (e.g. different length.)
            - If fractionate is enabled, but n_fractions is either not an integer or it is below or equal 0.

        """
        if self._aggregated_on is not None and self._aggregated_on not in self._sample_list.columns:
            raise ValueError("'aggregated_on' is provided but not found in the sample_list dataframe.")
        if self._fractionate and not isinstance(self._n_fractions,int):
            raise ValueError("'fractionate' was enabled, but the number of 'n_fractions' is not an int.")
        if self._fractionate and self._n_fractions <= 0:
            raise ValueError("'fractionate' was enabled, but the number of 'n_fractions' is equal or smaller 0.")
        if not all(validate_date_string(sample_name.split("_",maxsplit=1)[0]) for sample_name in self._sample_list.index):
            raise ValueError("The index of the sample_list must be sample names and it must lead with a date_string in format %Y%m%d")

        #check if number of columns is equal throughout all rows in a plate 
        if not (all(all(len(row) == len(plate_positions[0]) for row in plate_positions) for plate_positions in self._free_plate_positions)):
            raise ValueError("Each item list in free_plate_positions must have the same length (e.g. number of columns.).")

        if self._aggregated_on is not None:
            unique_values_to_aggregate_on = self._sample_list.loc[:,self._aggregated_on].unique()
            self._number_samples = unique_values_to_aggregate_on.size
        else:
            self._number_samples = self._sample_list.index.size
        if self._fractionate:
            #if sample are fractionated, multiply each sample with n_fractions
            self._number_samples = self._number_samples * self._n_fractions

        #check if enough space on plates 
        free_wells_per_plate = [np.sum(plate) for plate in self._free_plate_positions]
        free_wells_total = np.sum(free_wells_per_plate)
        if free_wells_total < self._number_samples: 
            raise ValueError(f"Number of free wells in plate positions ({free_wells_total}) is smaller than the number of runs ({self._number_samples}).")


    def _assign_runs_to_plate_wells(self, run_names : List[str], aggregated_samples : List[List[int]] = []) -> pd.DataFrame:
        """
        Assigns each run to a free position in the plates.

        Parameters
        ----------
        run_names : List[str]
            The run names stored in a list 

        aggregated_samples : List[List[int]], optional
            The sample indices that were pooled for a run (if aggregated_on is not None). If an empty list is provided, the
            aggregated_samples column in the output list of dicts will be an empty list. 
        
        Returns
        -------
        pd.DataFrame
            Data Frame of the assigned runs to plate wells. Contains the following columns and types. 
            ```
            {
                "plate_index" : int, #the plate index if multiple are required
                "column_index" : int, #the column index inferred from 'free_plate_positions'
                "row_index" : int, #the row index inferred from 'free_plate_positions'
                "position_label" : str, #position label such as A1 for row_index = 0 and column_index = 0 
                "name" : str, #the name of the run, if aggregate_on  or fractionate is enabled, not equal to sample name
                "aggregated_samples" : list #the sample indices that were aggregated.
            }
            ```
                
        """
     
        index = 0
        assigned_runs = []
        for plate_index, plate in enumerate(self._free_plate_positions):
            n_columns = len(plate[0]) #number of columns 
            n_rows = len(plate) #number of rows
            column_labels = np.arange(1,n_columns+1)
            row_labels = string.ascii_uppercase[:n_rows]

            if self._rows_first:
                for row_index,rows in enumerate(plate):
                    for column_idx, is_well_free in enumerate(rows):
                        if index == len(run_names):
                            break 
                        if is_well_free:
                            position_label  = f"{row_labels[row_index]}{column_labels[column_idx]}"
                            assigned_runs.append(
                                self._get_run_well_assignment(
                                        plate_index,
                                        column_idx,
                                        row_index,
                                        position_label,
                                        run_names[index],
                                        aggregated_samples[index] if len(aggregated_samples) else []))
                            index += 1

            else:
                for column_idx in np.arange(n_columns):
                    for row_index in np.arange(n_rows):
                        is_well_free : bool = plate[row_index][column_idx]
                        if index == len(run_names):
                            break 
                        if is_well_free:
                            position_label = f"{row_labels[row_index]}{column_labels[column_idx]}"
                            assigned_runs.append(
                                self._get_run_well_assignment(
                                        plate_index,
                                        column_idx,
                                        row_index,
                                        position_label,
                                        run_names[index],
                                        aggregated_samples[index] if len(aggregated_samples) else []))
                            index += 1
        
        return pd.DataFrame().from_dict(assigned_runs)
    
    def _get_run_well_assignment(self, 
                                  plate_index : int, 
                                  column_idx : int, 
                                  row_index : int, 
                                  position_label : str, 
                                  name : str, 
                                  aggregated_samples : List[int]) -> Dict[str,Any]:
        """
        Creates a dictionary that is used to save a run. 

        Parameters
        ----------
        plate_index : int 
            The index of the plate. The plate is defined by its free positions. 
            Also the dimensions are inferred from there.
        column_index : int 
            The column index on the plate. 
        row_index : int
            The row index on the plate. 
        position_label : str 
            The position label. row_index = 0 and column_index = 1 equals 'A2', row_index=2, column_index = 0 equals 'C0'. 
        name : str 
            The run name. Note that the run is prefixed by the label which is generated here.
            A unique identifier to faciliate searching and data storage. 
        aggregated_samples : List[int]
            A list of samples indices that are pooled for this analytical run. 

        Returns
        -------
        dict 
            The run parameters.
            ```
            {
                "plate_index" : int,
                "column_index" : int, 
                "row_index" : int, 
                "position_label" : str, 
                "name" : str,
                "label" : str,
                "aggregated_samples" : List[int]
            }
            ```
        """
        run_label = get_random_string(N=4)
        return {
                    "plate_index" : plate_index,
                    "column_index" : column_idx, 
                    "row_index" : row_index, 
                    "position_label" : position_label, 
                    "name" : f"{name}_{run_label}",
                    "label" : run_label,
                    "aggregated_samples" : aggregated_samples
                    }

    def _get_runname_on_aggregate(self, index : int, total_runs : int, groupName : str , aggregated_samples : List[int]) -> str:
        """
        Generates the name if aggregation/pooling is enabled. 

        Parameters
        ----------
        index : int 
            The index of the pooled run. 
        total_runs : int
            The number of the total number of runs after aggregating (pooling). 

        Returns
        -------
        str
            The run name of a pooled list of samples. 

        """
        today_as_string = datetime.today().strftime('%Y%m%d')
        leading_zeros = len(str(total_runs)) if total_runs >= 10 else 2
        sample_idces = [f'{agg_sample_idx:0{leading_zeros}d}' for agg_sample_idx in aggregated_samples]
        aggregated_sample_idcs = f"samples-{'-'.join(sample_idces) if len(sample_idces) < 5 else len(sample_idces)}"
        if self._add_user_initials:
            user_initials = f"{self._user.firstname[:2]}{self._user.lastname[:2]}"
            return f"{today_as_string}_{self._dataset_label}_{user_initials}_{index:0{leading_zeros}d}_{groupName.replace(' ','-')}_{aggregated_sample_idcs}"
        else:
            return f"{today_as_string}_{self._dataset_label}_{index:0{leading_zeros}d}_{groupName.replace(' ','-')}_{aggregated_sample_idcs}"
        

    def _get_fraction_runs(self, run_names : List[str]) -> List[str]:
        """
        Repeats the run names by self.n_fractions and adds a -frac-{frac-index} 
        to each run name. 

        Parameters
        ----------
        run_names : List[str]
            The run names. 

        Returns
        -------
        List[str]
            The run names in a list of size self._n_fractions *  len(run_names). 
        """
        today_as_string = datetime.today().strftime('%Y%m%d')
        leading_zeros = len(str(self._n_fractions)) if self._n_fractions >= 10 else 2
        if self._add_user_initials:
            user_initials = f"{self._user.firstname[:2]}{self._user.lastname[:2]}"
            return list(chain.from_iterable([[f"{today_as_string}_{self._dataset_label}_{user_initials}_{run_name.split('_',maxsplit=2)[-1]}_frac-{frac_index:0{leading_zeros}d}" for frac_index in range(1,self._n_fractions+1)] 
                                                for run_name in run_names]))
        else:
            return list(chain.from_iterable([[f"{today_as_string}_{self._dataset_label}_{run_name.split('_',maxsplit=2)[-1]}_frac-{frac_index:0{leading_zeros}d}" for frac_index in range(1,self._n_fractions+1)] 
                                                for run_name in run_names]))


    def create(self) -> RunListModel:
        """
        Creates a Runlist based on the init parameters. 
        
        Returns
        -------
        RunListModel
            The created run list as a pydantic RunListModel.
        """
        n_plates = len(self._free_plate_positions) 
        aggregated_samples = []
        if self._aggregated_on is None and not self._fractionate:
            #sample  names equal run names 
            #TO DO : maxsplit=2 - dangerous for changing the file name creating method.. 
            #find another solution here. 
            today_as_string = datetime.today().strftime('%Y%m%d')
            if self._add_user_initials:
                user_initials = f"{self._user.firstname[:2]}{self._user.lastname[:2]}"
                run_names = [f"{today_as_string}_{self._dataset_label}_{user_initials}_{sample_name.split('_',maxsplit=2)[-1]}" for sample_name in self._sample_list.index]
            else:
                run_names = [f"{today_as_string}_{self._dataset_label}_{sample_name.split('_',maxsplit=2)[-1]}" for sample_name in self._sample_list.index]
        elif self._aggregated_on is None and self._fractionate:
            run_names = self._get_fraction_runs(self._sample_list.index.to_list())
            
        elif self._aggregated_on is not None:
            #groupby the sample list by the aggregate_on column => pooling 
            groupByAggregate = self._sample_list.groupby(by=self._aggregated_on, sort=False)
            aggregated_samples = [[self._sample_list.index.get_loc(sample_name) for sample_name in groupData.index] for _, groupData in groupByAggregate]
            run_names = [self._get_runname_on_aggregate(n + 1, groupByAggregate.ngroups, groupName, aggregated_samples[n]) for n, (groupName, _) in enumerate(groupByAggregate)]
                         
            if self._fractionate:
                #if fractionated create run names with the respective fraction index 
                aggregated_samples = [[self._sample_list.index.get_loc(sample_name) for sample_name in groupData.index] for _, groupData in groupByAggregate for frac in range(self._n_fractions)]
                #aggregated_samples = [agg_samples * self._n_fractions for agg_samples in aggregated_samples]
                run_names = self._get_fraction_runs(run_names)
        
        #finally assign ach run to a plate run 
        assigned_runs = self._assign_runs_to_plate_wells(run_names,aggregated_samples)
       # run_idces = assigned_runs.index.tolist()
        if self._scramble:
            #if scramble within one plate, first group by plate_index, then scramble
            if self._scramble_across_plates:
                scrambled_runs = assigned_runs.sample(frac=1.0)
            else:
                scrambled_runs = assigned_runs.groupby(by = "plate_index").apply(lambda df : df.sample(frac=1.0)).reset_index(drop=True)
            #reset_index to get the original run order 
            run_list = scrambled_runs.reset_index(drop=True).to_dict(orient="records")
        else:
            run_list = assigned_runs.reset_index(drop=True).to_dict(orient="records")

        runs = [AnalyticRunModel(**run, measurement_index=idx, index=idx) for idx, run in enumerate(run_list)]
        return RunListModel(
            aggregated_on=self._aggregated_on,
            fractionated=self._fractionate,
            n_fractions=self._n_fractions,
            runs=runs,
            scrambled=self._scramble,
            scrambled_across_plates=self._scramble_across_plates,
            n_runs=len(runs),
            n_plates=n_plates,
            dataset_label=self._dataset_label,
            user_tag=self._user.tag,
            )

    
if __name__ == "__main__":
    sample_list = pd.DataFrame({"sample" : ["a_01","a_02","a_03","a_04"], "batch" : [1,1,0,0]})
    runsList = RunListCreator("abc",sample_list,
                   #aggregate_on="batch", 
                   n_fractions=2, 
                   user_tag="abac23",
                   rows_first=False,
                   scramble=False,
                   fractionate=False, 
                   free_plate_positions=[[[False, False, False],[True, True, False]],[[True, True, True,True],[True, True, False, False]]]).create()
    print(runsList)
 