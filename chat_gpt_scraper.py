import re 
# import requests
from bs4 import BeautifulSoup
import pandas as pd 
import numpy as np 
import os
import json
import subprocess
from datetime import datetime
from config import RAW_DIR, INTERIM_DIR, PROCESSED_DIR, FINAL_DIR, DATASET, DATA_KEYWORD, CHAT_GPT_QUESTION


def remove_white_spaces(string): 
    '''
    remove all leading and trailing white spaces 
    
    Args: 
        string: string that needs to be striped e.g. "  maths  "
    
    Returns: 
        string with the leading and trailing white spaces striped e.g. "maths" 
    '''
    return re.sub(r"^\s\[", "", string.strip())


def is_unix_time(string): 
    '''
    Checks to see if a given string is unix time or not 
    
    Args: 
        String that needs to be checked 
    
    Returns: 
        Boolean value, true when it is unix time stamp, false if else 
    '''
    unix_time = re.match(r'^\d{10}\.\d+$', str(string))
    
    if unix_time: 
        return True 
    return False 

def convert_unix_time(unix_stamp): 
    """
    given unix timestamp, convert it to sth more human readable

    Args:
        unix_stamp (str): _description_

    Returns:
        str: _description_
    """
    return datetime.fromtimestamp(unix_stamp)


def find_links(which_chat): 
    '''
    go through the csv file and find the column that contains the specified type of chat links 
    
    Args: 
        which_chat: the type of chat that we want to pull from 
    
    Return: 
        pdSeries:  with the found html links 
    '''
    data = pd.read_csv(f"{RAW_DIR}/{DATASET}")
    
    # remove nas 
    filtered_links = data[data[which_chat].notna()][which_chat]
    
    # remove question & question id rows
    filtered_links = filtered_links[2:]

    # remove white spaces 
    cleaned_links = filtered_links.apply(remove_white_spaces)

    # reindex 
    final_links = cleaned_links.reset_index(drop=True)

    return final_links


def scrape_link(index, link):
    """
    Given link, scrape info and dump into an html file 

    Args: 
        link: chatgpt link that requires scraping 
        number: the order that they appear in the field where folks put in chat links on the qualtrics results file 
    """
    # TODO: guardrails for when link is invalid or null 
    command = ["curl", "-o", f"{INTERIM_DIR}/{index}_raw_output.html",  link]
    subprocess.run(command)


def retrieve_the_json_portion(file_dir, number): 
    '''
    given an html file, find the json chunk and dump it into a json file
    
    Args: 
        file_dir: path to html file
        number: index of that file 
    
    '''

    with open(file_dir, "r", encoding='utf-8') as f: 
        stuff_inside_html = f.read()
    soup = BeautifulSoup(stuff_inside_html, 'lxml')

    # get the scripts that are pushing data to the server 
    scripts = soup.find_all("script", nonce=True, string=re.compile(DATA_KEYWORD))
 
    # get the max length of the script in scripts cus thats probs the json object that we 
    # are trying to pull 
    max_length = max(len(s.get_text()) for s in scripts)

    with open(f"{PROCESSED_DIR}/{number}_json_output.json", "w", encoding = "UTF-8") as file: 
        for s in scripts:
            # if lenght is the longest, its probs the json fiile 
            if len(s.get_text()) == max_length:
                cleaned_script_text = remove_white_spaces(s.get_text())

                json_bit = extract_json_object(cleaned_script_text)

                file.write(json_bit)
                


def extract_json_object(string): 
    '''
    helper method for retrieve_the_json_portion 
    given a script within a tag, extract the json bit 
    
    Args: 
        string (str): the string with the json object that we want to extract 
        
    Return: 
        str: the content of the json file in string format
    '''
    # remove the outskirts 
    stuff_to_remove = DATA_KEYWORD + re.escape('("')
    results_wout_prefix = re.sub(re.compile(stuff_to_remove), "", string)

    suffix_pattern = re.escape(r'\n");')
    pattern = re.compile(suffix_pattern + r"$")
    results_middle = re.sub(pattern, "", results_wout_prefix)

    results_without_quotes = results_middle.replace('\\"', '"')
    results_without_quotes = results_without_quotes.replace('\\\\user\\\\', '\\\\\\\\user\\\\\\\\')
    remove_quotes_for_actual_messages = results_without_quotes.replace('\\"', '"')

    pattern_that_wraps_msgs = r'\\"'

    final_results = re.sub(re.compile(pattern_that_wraps_msgs), "", remove_quotes_for_actual_messages)

    return final_results


def create_csv_files(file_path, order_of_file): 
    """
    given json file path n order of file,
    extracts important information and outputs csv file
    
    Args:
        file_path (os.path): path to json file 
        order_of_file (int): how to number the resulting file 
  
    """

    # load json file 
    with open(file_path, "r", encoding='utf-8', errors='strict') as f:
        data = json.load(f)

    # initialise df 
    rows = []
    
    # meta data stuff 
    title = ""
    create_time = 0 
    update_time = 0

    # go through the json list 
    for i in range(0,len(data)-1, 1): 
        if isinstance(data[i], str) and "title" in data[i]: 
            title = data[i+1]
            continue
        if not is_unix_time(data[i]): 
            continue 

        timestamp = data[i]
        # extract file create time 
        if create_time == 0 : 
            create_time = convert_unix_time(timestamp)
            continue 
            
        # extract file latest update time 
        elif update_time == 0:     
            update_time = convert_unix_time(timestamp)
            continue 
    
        # extract timestamp + message 
        
        # if there is a timestamp right afterwards, probs a chatgpt response 
        elif i + 1 < len(data) and is_unix_time(data[i+1]): 
            timestamp =  data[i+1]
            sender = "chatgpt"
        
        # if there is not, check if gibberish. 
        elif not check_if_chat_message(timestamp, data): 
            continue

        # if not, then update sender
        else: 
            sender = classify_sender(timestamp, data)

        message = extract_msg(timestamp, data) 

        rows.append([title, 
                        create_time, 
                        update_time,
                        sender, 
                        convert_unix_time(timestamp), 
                        message])
    
    df = pd.DataFrame(rows, columns=['title', 'create_time', "update_time", 'sender', 'timestamp', 'message'])
    df.to_csv(f"{FINAL_DIR}/{order_of_file}_extracted_chat.csv", index=False)

def classify_sender(unix_stamp, data): 
    """
    helper method for create_csv_files
    given unix stamp and the json list, figure out who sent message 
    Args:
        unix_stamp (float): an unix timestamp 
        data (list): the json file 

    Returns: 
        str: chatgpt/user 
    """
    # TODO: stuff
    return "user" 
    
def check_if_chat_message(unix_stamp, data): 
    """
    helper method for create_csv_files
    given unix stamp and the json list, figure out if it is gibberish or chat message
    Args:
        unix_stamp (float): an unix timestamp 
        data (list): the json file 

    Returns: 
        True if it is a valid chat message
        False otherwise  
    """
    # TODO :s s
    return True 

def extract_msg(unix_stamp, data): 
    """
    helper method for create_csv_files
    given unix stamp and the json list, extract chat message
    Args:
        unix_stamp (float): an unix timestamp 
        data (list): the json file 

    Returns: 
        message
    """
    curr_index = data.index(unix_stamp) + 1
    strings = []
    
    entered_string = False 
    while curr_index < len(data):
        curr_element = data[curr_index]
        if isinstance(curr_element, str):
            strings.append(curr_element)  
            curr_index += 1
        elif not strings: 
            curr_index += 1 
        else: 
            curr_index = len(data)

    return strings[-1] 
       
if __name__ == "__main__": 

    # get all the html links from the raw data file 
    html_links = find_links(CHAT_GPT_QUESTION)

    # for every links found, scrape the link for the file structure and output in interim the results 
    for index, links in html_links.items(): 
        scrape_link(index, links)
    print("Done creating HTML files")

    # for every html file in interim, extract relevant json object then ouput in processed
    for file in os.listdir(INTERIM_DIR):
        order_of_file = file[0] 
        file_path = os.path.join(INTERIM_DIR, file)
        retrieve_the_json_portion(file_path, order_of_file)
    print("Done converting to JSON files")
    
    # for every json file in processed, extract relevant info then ouput in csv format in final
    final_order = 0 
    for file in os.listdir(PROCESSED_DIR):
        order_of_file = file[0] 
        file_path = os.path.join(PROCESSED_DIR, file)
        create_csv_files(file_path, order_of_file)    
    print("Done creating final CSV files")



