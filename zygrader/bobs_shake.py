#TODO: everything
#make an event class

import csv
def start():
    pass
class work_event:
    def __init__(self, row):
        pass
        #I haven't figured out how to store the row's fields into variablesrow_field = next(row)

def read_in_stats(file_name):
    """takes in a csv file and goes through it, using each row to make an event"""
    with open(file_name, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            event = work_event(row)
            events.append(event) #if event type is LAB:
events = []
mappedEvents = {}