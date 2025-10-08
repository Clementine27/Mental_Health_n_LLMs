import re 
import requests
from bs4 import BeautifulSoup
import pandas as pd 
import numpy as np 
import os


data_keyword = "window.__reactRouterContext.streamController.enqueue"

def clean_up_text(string): 
    return re.sub(r"\s+", "", string.strip())

def normalise_text(string): 
    return re.escape(string)




def find_links(): 
    '''
    go through the csv file and find the column that contains the chatgpt links 

    return the series with the found html links 
    '''

    data = pd.read_csv("data/raw/dataset.csv")
    # initial cleaning of responses 
    filtered_links = data[data["1_LLM_S_2"].notna()]["1_LLM_S_2"]

    filtered_links = filtered_links[1:]

    filtered_links = filtered_links.apply(clean_up_text)

    #TODO: make this not hard coded
    final_links = filtered_links.iloc[1::2].reset_index(drop=True)

    return final_links

      

def link_scraper(index, link):
    """
    given link, creates a beautiful soup object and dump content into an html file 

    link: chatgpt link that requires scraping 
    number: the order that they appear in the field where folks put in chat links on the qualtrics results file 
    """
    # TODO: guardrails for when link is invalid or null 
    
    response = requests.get(link)

    soup = BeautifulSoup(response.text, 'html.parser')


    with open(f"data/interim/{index}_raw_output.html", "w", encoding = "UTF-8") as file: 
        file.write(str(soup.prettify()))

    print("Done parsing links")


def retrieve_the_json_portion(): 
    '''
    given a html file, find the json chunk and then save it to a seperate file 
    '''
    # TODO: make this a loop so that it does it for every file in a subdirectory 
    with open("data/interim/0_raw_output.html", "r", encoding='utf-8') as f: 
        stuff_inside_html = f.read()
    soup = BeautifulSoup(stuff_inside_html, 'lxml')

    # get the scripts that are pushing data to the server 
    scripts = soup.find_all("script", nonce=True, string=re.compile(data_keyword))
 
    # get the max length of the script in scripts cus thats probs the json object that we 
    # are trying to pull 
    max_length = max(len(s.get_text()) for s in scripts)

    with open(f"data/processed/0_json_output.json", "w", encoding = "UTF-8") as file: 
        for s in scripts:
            if len(s.get_text()) == max_length:
                cleaned_script_text = clean_up_text(s.get_text())

                normalised_text = normalise_text(cleaned_script_text)

                # TODO 
                json_bit = extract_json_object(normalised_text)
                file.write(cleaned_script_text + "\n\n\n")


    print("Done converting to JSON files")


def extract_json_object(string): 
    '''
    given a script within a tag, extract the json bit 
    '''
    # TODO DE-HARDCODE BRO
    # the 3 is for ("[ 

    json_bit = string[len(data_keyword) + 3:]
    
    return json_bit





if __name__ == "__main__": 
    # get all the html links from the raw data file 
    html_links = find_links()

    # for every links found, scrape the link for the file structure and output in interim the results 
    for index, links in html_links.items(): 
        link_scraper(index, links)


    # TODO: for loop to apply retrieve the json portion apply to all files in interim 
    # for file in os.listdir("data/interim/"):
    #     with open(file, "r", encoding='utf-8') as f: 
    #         stuff_inside_html = f.read()
    #         soup = BeautifulSoup(stuff_inside_html, 'html.parser')
    #         retrieve_the_json_portion(soup)

    retrieve_the_json_portion()







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

