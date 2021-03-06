import pandas as pd
from fuzzywuzzy import fuzz
from collections import defaultdict 
from datetime import datetime as dt
import os
import re

class djdisk():
    
    def __init__(self,dir='Downloads',thresh=75):
        
        self.thresh = thresh
        self.user = os.path.expanduser('~') #pulls windows/mac user i.e. "/User/<your_name>/"
        self.dir = dir #will have to be root or full path from root provided
        self.cwd = self.user + '/' + self.dir
        self.gowords = ['remix','clean','mashup','dirty','mix','edit','bounce','radio','version']
        self.og_file_tracker_dict = {} #dict of all tokenized-file names (k) and their filepaths (v)
        self.match_dict = defaultdict(list) 
        os.makedirs(self.user + f'/archived_duplicate_mp3s_from_{dt.now().date()}', exist_ok=True) #create if not
        self.values_list = [] # global attr so we can recursively update it in process_files function
        self.archive_dir = self.user + f'/archived_duplicate_mp3s_from_{dt.now().date()}'
        self.recursion = 0
        self.counter = 0 
        self.freed = 0
        self.round = 0
    
    def gather_mp3_files(self):            
        
        # first, get all files in specified directory and 'tokenize' them 
        tokenized_files = []
        for file in os.listdir(self.cwd):

            # just get the name
            if '.mp3' in file:

                filename = file.split('.mp3')[0]
                filepath = os.path.join(self.cwd, filename + '.mp3') # hold onto this for removal
                os.chdir(self.cwd)
                
                filtered = self.tokenize(filename)
                tokenized_files.append(filtered)

                # first line of defense. if the file is EXACTLY the same after tokenization, archive it!
                if self.og_file_tracker_dict.get(filtered):
                    print(f'early duplicate found: removing {filepath}')
                    self.archive(filepath)
                else:
                    self.og_file_tracker_dict[filtered] = filepath

        # group 'em up by dj-'go' words or else as 'other'
        grouped = self.groupup(tokenized_files)
        for group,values in grouped.items():
            
            # if there are more than 1 file per group
            if len(values) > 1: 
                
                # each group iteration, set state variable to that groups's values until False is returned
                print(f'there are {len(values)} in the group {group} that need to be analyzed')
                self.values_list = values
                self.recursion = 0
                while self.process_files():
                    print(f'processing files for {group}. round {self.recursion}...')
                print('all done')
        
        # archive
        dupes = list(self.match_dict.values())
        print(f'\nduplicates are: {dupes}\n')
        file_path_dict = self.og_file_tracker_dict
        [self.archive(filepath) for filename, filepath in file_path_dict.items() for dupe in dupes if filename in dupe]

        
    def tokenize(self,filename):
        
        filename = filename.replace('-','_').replace('.','_') # standardize word separators
        filename = re.sub('([\d+])(.*)?','',filename)
        word_list = filename.lower().split('_')
        filtered_words = '_'.join([word for word in word_list])
        return filtered_words
    
    def rm_goword(self,filename,goword):
        return filename.replace(goword,'')
    
    def report(self):

        print(f'Total number of duplicate .mp3 files detected: {self.counter}')
        print(f'Total number of bytes freed {self.freed}')
        print(f'Files safely archived to {self.archive_dir} -- staged for deletion by user')
    
    def archive(self,filepath):

        # filename variable is tokenized key, so extract real file name from filepath and use to build archive path
        proper_file_name = filepath.rsplit('/',1)[-1]
        archive_file_path = self.archive_dir + '/' + proper_file_name

        # Update counters for freed-file-space and number of transactions
        self.freed += os.path.getsize(filepath)
        self.counter += 1

        # Mv it to archive
        os.chdir(self.cwd)
        os.rename(filepath,archive_file_path)
        print(f'successfully moved {proper_file_name} to archive at {self.archive_dir}')
        return self.report()

        
    def groupup(self,filenames):
        
        # group based on the commonly occuring 'gowords' in song-titles
        grouped = {}
        for filename in filenames:
            goword = [goword for goword in self.gowords if goword in filename]
            if goword:
                # Trim out 'goword' so we don't consider that part of its match within that group
                grouped.setdefault(goword[0],list()).append(self.rm_goword(filename,goword[0]))
            else:
                grouped.setdefault('other',list()).append(filename)
        return grouped
    
    def matcher(self,filename,values_list):

        # optionarl KWARG 'round' in case we want to run a .ratio and run iterations of matches
        threshold = self.thresh + (10 * self.round) # every round increased threshold by 10 points, final round being .95 match 

        matches = []
        for x in values_list:
            partialratio = fuzz.partial_ratio(filename,x)
            if partialratio >= threshold:
                print(f'partial ratio between {filename} and {x} is {fuzz.partial_ratio(filename,x)}\n')
                print(f'REG ratio between {filename} and {x} is {fuzz.ratio(filename,x)}\n')
                print(f'token sort ratio between {filename} and {x} is {fuzz.token_sort_ratio(filename,x)}\n')
                reg_ratio = fuzz.ratio(filename,x)
                token_sort = fuzz.token_sort_ratio(filename,x)
                if abs(token_sort - reg_ratio) <= 10 and abs(token_sort - partialratio) <= 10 and abs(reg_ratio - partialratio) <= 10:
                    print("triple gate passed. appending match.")
                    matches.append(x)
        return matches
    
    def process_files(self):
        
        self.recursion +=1
        print(f'current values_list = {self.values_list}\n')
        
        # isolate old self.values_list to new variable to compare at end of f(x)
        curr_iters_values_list = self.values_list

        # every time this is called, self.values_list has been updated at bottom of this function
        for filename in list(curr_iters_values_list):
            
            print(f'checking all matches against {filename}')
            # we dont want to the file to match to itself (need to keep at least 1)
            buffer = curr_iters_values_list
            buffer.remove(filename)
            # call match processor (above method)
            matches = self.matcher(filename,buffer)
            
            if matches:

                # if its not an empty list, update our match_dict with filename (k) and its list of duplicates (v)
                self.match_dict[filename] = matches
                # we don't want to process that file again.
                matches.append(filename)
                # update global attr // perform set operation to whittle down our 'values_list' pool that we iterate through next f(x) call
                self.values_list = set(curr_iters_values_list) - set(matches)
                return True                
        

# ---- Initiate Program Here for now ------
thresh = 70
dedupe = djdisk(thresh=thresh)
dedupe.gather_mp3_files()
