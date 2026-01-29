


def process_info(html_file): 
    """
    given an html file in the raw file directory, pull out the chat content and meta data, 
    put the data in their respective columns and dump results in a csv file
    in the interim directory

    html_file: the path of the parsed html file in the raw dir. that requires processing

    """
    # TODO: loop to number the files using f string 
    with open("results_from_html.csv", "w", encoding= "UTF-8") as file: 
        find_title(html_file)
        find_text(html_file)
        find_time()


def find_title(html_file): 
    """
    goes into the provided html file and find the title of the chat 

    html_file: the file that requires info extraction 

    return: string that gets the tile of teh 
    """

    with open(raw_file_path, "r") as file: 
        for line in file: 
            if "<title>" in line: 
                line += 1
                print(line)


def get_stuff_btw_tags(file_path, tag): 
    """
    get info between the first instance of the specified tags  

    return: the info wedged between the opening and closing tag with the same 
    """
    opening_tag = f"<{tag} [^>]*>"
    closing_tag = f"</{tag}>" 
    with open(file_path, "r") as file: 
        for line in file: 
            # find the opening tag 
            if opening_tag in line: 
                # get the info wedged between the opening_tag and the closing one, regardless of diffreent lines 
                tag_content = ""
                return tag_content



def find_text(raw_file_path): 
    """
    find the text field that the user put into the chat

    raw_file_path: the raw file path w the text that requires pulling 
    return: the string with the user prompt 
    """
    # find script tag
    with open(raw_file_path, 'r') as file:
        for line in file:
            # TODO: regex it so that there can be anything in nonce" 
            # looks like a chat specific code though? pls get more chats to double check 
            if "<script nonce=" in line: 
                line += 1
                if "window.__reactRouterContext.streamController.enqueue(" in line: 
                    # TODO: print from that line 
                    print(line)


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
    