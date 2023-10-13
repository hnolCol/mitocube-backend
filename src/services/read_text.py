
import pandas as pd 

def tsv_string_to_dataframe(bytes : bytes, 
                encoding : str = "utf-8", 
                headers : bool = True, 
                lineSplit : str = "\n", 
                cellSplit : str = "\t") -> pd.DataFrame:
    """Transforms bytes input using an encoding into a pandas dataframe."""
    plainText = bytes.decode(encoding)
    lines = plainText.split(lineSplit)
    if headers:
        columnNames = lines[0].split(cellSplit)
        del lines[0]
    dataArray = [line.split(cellSplit) for line in lines if len(line) > 0]

    return pd.DataFrame(dataArray,columns=columnNames)