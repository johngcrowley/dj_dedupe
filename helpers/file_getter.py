import pandas as pd
from fuzzywuzzy import fuzz
# import nltk
# from nltk.corpus import stopwords
from collections import defaultdict 
from datetime import datetime as dt
import os

class djdisk():
    
    def __init__(self,dir='Downloads'):
        
        self.user = os.path.expanduser('~')
        self.dir= self.user + '/' + dir
        self.gowords = ['remix','clean','mashup','dirty','mix','edit']
        self.og_file_tracker_dict = {} # key is first file, values = list of tuples of dupe filenames & their file paths
        self.grouplicates = defaultdict(list) # global so we can recursively update it in process_files function?
        os.makedirs(self.user + f'/archived_duplicate_mp3s_from_{dt.now().date()}', exist_ok=True)
        # nltk.download('stopwords')
        self.archive_dir = f'archived_duplicate_mp3s_from_{dt.now().date()}'
        self.counter = 0
        self.freed = 0
        self.recursion = 0
        self.values = []
        
    def tokenize(self,filename):
        
        # stops = stopwords.words('english')    if word not in stops]
        stops = ''
        filename = filename.replace('-','_').replace('.','_') # standardize word separators
        word_list = filename.lower().split('_')
        filtered_words = '_'.join([word for word in word_list])
        return filtered_words
    
    def archive(self,filepath):

        print(filepath)
        # filename variable is tokenized key, so extract real file name from filepath and use to build archive path
        proper_file_name = filepath.rsplit('/',1)[-1]
        archive_file_path = filepath.replace(proper_file_name,f'{self.archive_dir}/{proper_file_name}')
        print('trying!!!')

        # Update counters for freed-file-space and number of transactions
        self.freed += os.path.getsize(filepath)
        self.counter += 1
        # Mv it to archive
        os.rename(filepath,archive_file_path)
        return print(f'successfully moved {proper_file_name} to archive at {self.archive_dir}')

        
    def groupup(self,filenames):
        
        # group based on the commonly occuring 'gowords' in song-titles
        grouped = {}
        for filename in filenames:
            goword = [goword for goword in self.gowords if goword in filename]
            if goword:
                grouped.setdefault(goword[0],list()).append(filename)
            else:
                grouped.setdefault('other',list()).append(filename)
                #grouped.setdefault(filename[0],list()).append(filename)
        return grouped
    
    def matcher(self,filename,values_list,round=0):
        # every round increased threshold by 10 points, final round being .95 match 
        threshold = 75 + (10 * round)  
        return [x for x in values_list if fuzz.partial_ratio(filename,x) >= threshold]
    
    def process_files(self):

        values_list = self.values_list
        # set up some sort of recursion here to trim generator values_list down during iterations?
        for filename in list(values_list):
       
            # we dont want to the file to match to itself     
            values_list.remove(filename)
            
            # call match processor
            matches = self.matcher(filename,values_list)
            if matches:
                self.grouplicates[filename] = matches
                matches.append(filename)

                self.values_list = set(values_list) - set(matches)
                if len(self.values) == (values_list):
                    print('no more matches to be found')
                    return False
                return True

    def build_dupe_pile(self):            
        
        # first, get all files in specified directory and 'tokenize' them 
        tokenized_files = []
        for file in os.listdir(self.dir):
            
            filename = file.split('.mp3')[0] # just get the name
            filepath = os.path.join(self.dir, filename + '.mp3') # hold onto this for removal
            filtered = self.tokenize(filename)
            tokenized_files.append(filtered)
            # first line of defense. if the file is EXACTLY the same after tokenization, archive it!
            try:
                self.og_file_tracker_dict[filtered] = filepath
            except:
                self.archive(filepath)
        
        # group 'em up by dj-'go' words or else as 'other'
        grouped = self.groupup(tokenized_files)
        for group,values in grouped.items():
            if len(values)>1: # if there are more than 1 file per group
                print(f'there are {len(values)} in the group {group} that need to be analyzed\n:{values}')
                
                # each group iteration, set state variable to that groups's values until False is returned
                self.values_list = values
                while self.process_files():
                    print('processing files...')
        
        # archive
        dupes = list(self.grouplicates.values())[0]
        file_path_dict = self.og_file_tracker_dict
        print(dupes)
        print(file_path_dict)
        [self.archive(filepath) for filename, filepath in file_path_dict.items() if filename in dupes]


dedupe = djdisk(dir='testfolder')
dedupe.build_dupe_pile()
