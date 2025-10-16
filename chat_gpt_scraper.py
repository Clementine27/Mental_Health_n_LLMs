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



def find_links(which_chat): 
    '''
    go through the csv file and find the column that contains the specified type of chat links 
    
    Args: 
        which_chat: the type of chat that we want to pull from 
    
    Return: 
        a Series with the found html links 
    '''
    data = pd.read_csv(f"{RAW_DIR}/{DATASET}")
    
    # Initial cleaning of responses 
    # read file 
    filtered_links = data[data[which_chat].notna()][which_chat]
    
    # remove question row
    filtered_links = filtered_links[1:]

    filtered_links = filtered_links.apply(remove_white_spaces)

    #TODO: make this not hard coded
    final_links = filtered_links.iloc[1::2].reset_index(drop=True)

    return final_links.dropna()


def link_scraper(index, link):
    """
    given link, creates a beautiful soup object and dump content into an html file 

    Args: 
        link: chatgpt link that requires scraping 
        number: the order that they appear in the field where folks put in chat links on the qualtrics results file 
    """
    # TODO: guardrails for when link is invalid or null 
    command = ["curl", "-o", f"{INTERIM_DIR}/{index}_raw_output.html",  link]
    subprocess.run(command)

    # with open(f"{INTERIM_DIR}/{index}_raw_output.html", "w", encoding = "UTF-8") as file: 
    #     file.write(response.text)


def retrieve_the_json_portion(file_dir, number): 
    '''
    given a soup object, find the json chunk and then save it to a seperate file 
    
    Args: 
        file_dir: 
        number: 
    
    '''

    with open(file_dir, "r", encoding='utf-8') as f: 
        stuff_inside_html = f.read()
    soup = BeautifulSoup(stuff_inside_html, 'lxml')

    # get the scripts that are pushing data to the server 
    scripts = soup.find_all("script", nonce=True, string=re.compile(DATA_KEYWORD))
 
    # get the max length of the script in scripts cus thats probs the json object that we 
    # are trying to pull 
    max_length = max(len(s.get_text()) for s in scripts)

    # TODO: make this loop-compatible
    with open(f"{PROCESSED_DIR}/{number}_json_output.json", "w", encoding = "UTF-8") as file: 
        for s in scripts:
            # if lenght is the longest, its probs the json fiile 
            if len(s.get_text()) == max_length:
                cleaned_script_text = remove_white_spaces(s.get_text())

                json_bit = extract_json_object(cleaned_script_text)

                file.write(json_bit)
                


def extract_json_object(string): 
    '''
    given a script within a tag, extract the json bit 
    
    Args: 
        string: the string with the json object that we want to extract 
        
    Return: 
        the content of the json file in string format
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


def extract_info_from_json(file_path): 
    """
    extract every information from a given json path 
    
    Args:
        file_path (_type_): _description_
        
    Returns: 
        long form dataframe 
    """

    
    with open(file_path, "r", encoding='utf-8', errors='strict') as f:
        data = json.load(f)

    
    rows = []

    title_index = data.index("title")
    title = data[title_index+1]
    
    create_time = 0 
    update_time = 0
    i = 0 
    while i < len(data): 
        if is_unix_time(data[i]) and create_time == 0 : 
            create_time = convert_unix_time(data[i])
        elif is_unix_time(data[i]) and update_time == 0:     
            update_time = convert_unix_time(data[i])
            i = data.index(data[i])
            
        elif is_unix_time(data[i]) and extract_msg(data[i], data) :  
            timestamp =  data[i]
            msgs = extract_msg(timestamp, data) 
            rows.append([title, 
                         create_time, 
                         update_time,
                        #  TODO make this more robust
                         "ChatGPT" if i % 2 == 1 else "User", 
                         convert_unix_time(timestamp), 
                         msgs])
        i +=1 
    
    df = pd.DataFrame(rows, columns=['title', 'create_time', "update_time", 'role', 'timestamp', 'message'])
    
    return df 
    


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
    return datetime.fromtimestamp(unix_stamp)

def extract_msg(unix_stamp, data): 
    """
    given unix stamp and the json list, find the index of the unix stamp and 
    then  find the next instances of strings until we encounter another number or {} object
    Args:
        unix_stamp (_type_): _description_
        data (_type_): _description_
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
        # # have not entered string yet 
        # if entered_string == False: 
        #     curr_index += 1 
        # # found string but its not a messgae
        # elif isinstance(data[curr_index], str) and not isinstance(data[curr_index -1], list):
        #     return 
        # # start of the messages 
        # elif isinstance(data[curr_index], str) and isinstance(data[curr_index -1], list):
        #     strings.append(data[curr_index + 1])  
        #     entered_string = True 
        #     curr_index += 1
        # # continue getting messages once entered
        # elif isinstance(data[curr_index], str) and entered_string == True: 
        #     strings.append(data[curr_index])  
        #     curr_index += 1
        # # have already entered string and the next bits are not strings 
        # elif entered_string == True and not isinstance(data[curr_index], str):
        #     return
    
    # if strings: 
    #     return strings[-1]  
    
if __name__ == "__main__": 
    # get all the html links from the raw data file 
    html_links = find_links(CHAT_GPT_QUESTION)

    # for every links found, scrape the link for the file structure and output in interim the results 
    for index, links in html_links.items(): 
        link_scraper(index, links)
    print("Done parsing links")

    # for every html file in interim, extract relevant json object then ouput in processed
    order_of_file = 0 
    for file in os.listdir(INTERIM_DIR):
        file_path = os.path.join(INTERIM_DIR, file)
        retrieve_the_json_portion(file_path, order_of_file)
        order_of_file += 1 
    print("Done converting to JSON files")
    
    # for every json file in processed, extract relevant info then ouput in csv format in final
    final_order = 0 
    for file in os.listdir(PROCESSED_DIR):
        file_path = os.path.join(PROCESSED_DIR, file)
        results = extract_info_from_json(file_path)
        results.to_csv(f"{FINAL_DIR}/{final_order}_extracted_chat.csv", index=False)
        
        final_order += 1 
   
    print("Done extracting information from JSON files")







# def process_info(html_file): 
#     """
#     given an html file in the raw file directory, pull out the chat content and meta data, 
#     put the data in their respective columns and dump results in a csv file
#     in the interim directory

#     html_file: the path of the parsed html file in the raw dir. that requires processing

#     """
#     # TODO: loop to number the files using f string 
#     with open("results_from_html.csv", "w", encoding= "UTF-8") as file: 
#         find_title(html_file)
#         find_text(html_file)
#         find_time()


# def find_title(html_file): 
#     """
#     goes into the provided html file and find the title of the chat 

#     html_file: the file that requires info extraction 

#     return: string that gets the tile of teh 
#     """

#     with open(raw_file_path, "r") as file: 
#         for line in file: 
#             if "<title>" in line: 
#                 line += 1
#                 print(line)


# def get_stuff_btw_tags(file_path, tag): 
#     """
#     get info between the first instance of the specified tags  

#     return: the info wedged between the opening and closing tag with the same 
#     """
#     opening_tag = f"<{tag} [^>]*>"
#     closing_tag = f"</{tag}>" 
#     with open(file_path, "r") as file: 
#         for line in file: 
#             # find the opening tag 
#             if opening_tag in line: 
#                 # get the info wedged between the opening_tag and the closing one, regardless of diffreent lines 
#                 tag_content = ""
#                 return tag_content



# def find_text(raw_file_path): 
#     """
#     find the text field that the user put into the chat

#     raw_file_path: the raw file path w the text that requires pulling 
#     return: the string with the user prompt 
#     """
#     # find script tag
#     with open(raw_file_path, 'r') as file:
#         for line in file:
#             # TODO: regex it so that there can be anything in nonce" 
#             # looks like a chat specific code though? pls get more chats to double check 
#             if "<script nonce=" in line: 
#                 line += 1
#                 if "window.__reactRouterContext.streamController.enqueue(" in line: 
#                     # TODO: print from that line 
#                     print(line)

