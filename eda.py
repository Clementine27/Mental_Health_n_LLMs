import pandas as pd 
import numpy as np 
from config import RAW_DIR, INTERIM_DIR, PROCESSED_DIR, FINAL_DIR, DATASET 

def read_data(): 
    data = pd.read_csv(f"{RAW_DIR}/{DATASET}")

    df = pd.DataFrame(data)
    df.head()


if __name__ == "__main__": 
    read_data()