import string
from os.path import commonprefix
from itertools import chain
import pandas as pd 
import numpy as np 
from typing import List, Dict
import warnings
from datetime import datetime
from config.models.submissions.runs import RunListModel, AnalyticRunModel

class RunListCreater:
    """Run List Creater Class 

    Create an analytical run list that can be used to actually start the runs in the LC-MS/MS or any other type of
    instrument. Please note that a sample and a run are not the same. If you pool for example two samples, it results
    in a single run. Therfore, you a) define a sample attribute that you can use to '''aggregate_on''' (e.g. pooling samples).
    Moreover, the sample could be fractionated by offline or online methods resulting in more runs than samples. This can
    be set up by defining ```fractionate=True``` and providing the number of fractions by the parameter ```n_fractions```. 


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
        ```
        plate = [[True, True, True],[True, True, False]]
        ```
        The plate design can be different but for each plate the number of columns must be equal throughout the rows. 

    rows_first : bool 
        If true, rows will be filled first when creating the run list (e.g. A1, A2 for sample 1 - 2 instead of A1, B1, B2)
        
    scramble : bool, default True
        Scrambles the runs in the ```RunList``` will be in random order. Usefull to avoid time batch effects by measuring for example all genotypes in a row while
        the analytical method such as LC-MS/MS performance changes over time. 
    
    scramble_across_plates : bool, default False 
        If scrambled is performance and the number of runs requires that the samples are spread over multiple plates, then the scramblin will be performed within each please (False, default)
        while if ```True``` all runs across plates are scrambled. It defaults to False since some analytical systems can only host a single well plate. 
    
    aggregate_on : str, default None
        The name of the samples attributes that should be used for aggregating the sample list on. This would mean that you can pool numerous samples together and would result in 
        less runs than samples. As an example, a SILAC based quantification experiment in proteomics could be such an example.

    fractionate : bool, default False 
        If samples are fractionated, than the number of runs is higher than the number of samples. The number of fractions can be defined using ```n_fractions``` parameter. 
    
    n_fractions : int, defualt 0 
        The number of fractions each sample is fractionated in to. As an example, if an offline fractionation is performed that results in six fractions, each sample then requires
        6 analytical runs. Please note that you can combine this with the ```aggregated_on```parameter which is allows to define a pooling of the sample. As a practical example, 
        assume that a TMT-12 plex quantification strategy is performed, hence the samples are ```aggregated_on``` the TMT-batch and then the pooled samples is fractionated via 
        offline high-pH fractionation, which results in a 24 fractions. 

    Raises
    ----------
    ValueError 
        If *aggregate_on* is not None but is not found in the sample_list pd.DataFrame as a column name.
        If the number of free_plate_positions contains less True than the number of runs. 
        If the number of columns is different for row within a plate (e.g. different length.)

    """
    def __init__(self, 
                dataset_label : str, 
                sample_list : pd.DataFrame, 
                free_plate_positions : List[List[List[bool]]],
                user_label : str,
                rows_first : bool = True,
                scramble : bool = True,
                scramble_across_plates : bool = False,
                aggregate_on : str | None = None, 
                fractionate : bool = False, 
                n_fractions : int = 0
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
        self._user_label = user_label 

        self.__check()

    def __check(self) -> None:
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



    def __assign_runs_to_plate_wells(self, run_names : List[str], aggregated_samples : List[List[int]] = []) -> pd.DataFrame:
        """
        Assignes each run to a free position in the plates.

        Parameters
        ----------
        run_names : List[str]
            The run names stored in a list 

        aggregated_samples : List[List[int]], optional
            The sample indices that were pooled for a run (if aggregated_on is not None). If an empty list is provided, the
            aggrated_samples column in the output list of dicts will be an empty list. 
        
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
                "name" : str, #the name of the run, if aggreagte_on  or fractionate is enabled, not equal to sample name
                "aggregated_samples" : list #the sample indices that were aggregated.
            }
                
            ```
                
        """
     
        index = 0
        assigned_runs = []
        for plateIdx, plate in enumerate(self._free_plate_positions):
            n_columns = len(plate[0]) #number of columns 
            n_rows = len(plate) #number of rows
            column_labels = np.arange(1,n_columns+1)
            row_labels = string.ascii_uppercase[:n_rows]

            if self._rows_first:
                for rowIdx,rows in enumerate(plate):
                    for colIdx, is_well_free in enumerate(rows):
                        if index == len(run_names):
                            break 
                        if is_well_free:
                            position_label  = f"{row_labels[rowIdx]}{column_labels[colIdx]}"
                            assigned_runs.append(
                                self.__get_run_well_assignment(
                                        plateIdx,
                                        colIdx,
                                        rowIdx,
                                        position_label,
                                        run_names[index],
                                        aggregated_samples[index] if len(aggregated_samples) else []))
                            index += 1

            else:
                for colIdx in np.arange(n_columns):
                    for rowIdx in np.arange(n_rows):
                        is_well_free : bool = plate[rowIdx][colIdx]
                        if index == len(run_names):
                            break 
                        if is_well_free:
                            position_label = f"{row_labels[rowIdx]}{column_labels[colIdx]}"
                            assigned_runs.append(
                                self.__get_run_well_assignment(
                                        plateIdx,
                                        colIdx,
                                        rowIdx,
                                        position_label,
                                        run_names[index],
                                        aggregated_samples[index] if len(aggregated_samples) else []))
                            index += 1
        
        return pd.DataFrame().from_dict(assigned_runs)
    
    def __get_run_well_assignment(self, 
                                  plateIdx : int, 
                                  colIdx : int, 
                                  rowIdx : int, 
                                  position_label : str, 
                                  name : str, 
                                  aggregated_samples : List[int]) -> Dict:
        """
        """
        return {
                    "plate_index" : plateIdx,
                    "column_index" : colIdx, 
                    "row_index" : rowIdx, 
                    "position_label" : position_label, 
                    "name" : name,
                    "aggregated_samples" : aggregated_samples
                    }

    def __get_runname_on_aggregate(self, index : int, total_runs : int, groupName : str , aggregated_samples : List[int]) -> str:
        """
        

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
        aggregated_sample_idcs = f"_samples-{'-'.join([f'{agg_sample_idx:02d}' for agg_sample_idx in aggregated_samples])}"
        return f"{today_as_string}_{self._dataset_label}_{groupName}_{aggregated_sample_idcs}_{index:0{leading_zeros}d}"
        
        
        
        # if "_" in common_prefix and len(common_prefix) > 1:
        #     # If the common prefix contains underscore
        #     # it is very likely that it should be removed. 
        #     last_underscore_position = common_prefix.rfind("_")
        #     common_prefix = common_prefix[:last_underscore_position]
        # if not common_prefix.split("_")[0].isdigit():
        #     warnings.warn('The common prefix does not start with digitals (as in a date) ... Adding today.')
        #     common_prefix = f"{today_as_string}_{common_prefix}"
        # else:
        #     #replacing date with today since the user would like to measure the samples, and the run should have the today date.
        #     common_prefix = today_as_string
        # if self._dataset_label not in common_prefix:
        #     warnings.warn('The dataset_label was not found in the common_prefix string of aggregated samples and has therefore been added.')
        #     return f"{common_prefix}_{self._dataset_label}_{index:0{leading_zeros}d}"
        
        # return f"{common_prefix}_{index:0{leading_zeros}d}"

    def __get_fraction_runs(self, run_names : List[str]) -> List[str]:
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
        leading_zeros = len(str(self._n_fractions)) if self._n_fractions >= 10 else 2
        return list(chain.from_iterable([[f"{run_name}_frac-{frac_index:0{leading_zeros}d}" for frac_index in range(1,self._n_fractions+1)] 
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
            run_names = self._sample_list.index
        elif self._aggregated_on is None and self._fractionate:
            run_names = self.__get_fraction_runs(self._sample_list.index.to_list())
            
        elif self._aggregated_on is not None:
            #groupby the sample list by the aggregate_on column => pooling 
            groupByAggregate = self._sample_list.groupby(by=self._aggregated_on, sort=False)
            aggregated_samples = [[self._sample_list.index.get_loc(sample_name) for sample_name in groupData.index] for groupName, groupData in groupByAggregate]
            run_names = [self.__get_runname_on_aggregate(n + 1, groupByAggregate.ngroups, groupName, aggregated_samples[n]) for n, (groupName, groupData) in enumerate(groupByAggregate)]
                         
            if self._fractionate:
                #if fractionated create run names with the respective fraction index 
                aggregated_samples = [[self._sample_list.index.get_loc(sample_name) for sample_name in groupData.index] for groupName, groupData in groupByAggregate for frac in range(self._n_fractions)]
                #aggregated_samples = [agg_samples * self._n_fractions for agg_samples in aggregated_samples]
                run_names = self.__get_fraction_runs(run_names)
                

        assigned_runs = self.__assign_runs_to_plate_wells(run_names,aggregated_samples)

        if self._scramble:
            #if scramble within one plate, first group by plate_index, then scramble
            if self._scramble_across_plates:
                scrambled_runs = assigned_runs.sample(frac=1.0)
            else:
                scrambled_runs = assigned_runs.groupby(by = "plate_index").apply(lambda df : df.sample(frac=1.0)).reset_index(drop=True)
            #reset_index to get the original run order 
            run_list = scrambled_runs.reset_index().to_dict(orient="records")
        else:
            run_list = assigned_runs.reset_index().to_dict(orient="records")

        runs = [AnalyticRunModel(**run, measurement_index=idx) for idx, run in enumerate(run_list)]
        return RunListModel(
            aggregated_on=self._aggregated_on,
            fractionated=self._fractionate,
            n_fractions=self._n_fractions,
            runs=runs,
            n_runs=len(runs),
            n_plates=n_plates,
            dataset_label=self._dataset_label,
            user_label=self._user_label)

    

if __name__ == "__main__":
    sample_list = pd.DataFrame({"sample" : ["a_01","a_02","a_03","a_04"], "batch" : [1,1,0,0]})
    runsList = RunListCreater("abc",sample_list,
                   #aggregate_on="batch", 
                   n_fractions=2, 
                   user_label="abac23",
                   rows_first=False,
                   scramble=False,
                   fractionate=False, 
                   free_plate_positions=[[[False, False, False],[True, True, False]],[[True, True, True,True],[True, True, False, False]]]).create()
    print(runsList)
 