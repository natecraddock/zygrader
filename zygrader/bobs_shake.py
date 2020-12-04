#TODO: everything
#make an event class
#WorkEvent init doesn't work and gives all kinds of fun errors

import csv
from zygrader.data.lock import get_lock_log_path


def start():
    #call get get_lock_log_path()
    test = GradingStatsWorker()
    log_file = get_lock_log_path()
    test.read_in_stats(log_file)


class GradingStatsWorker:
    def __init__(self):
        """This is supposed to clear the bob's output before
         we start writing all the event to it again"""
        debug_output = open("bobsOutput.txt", 'w')
        print("", file=debug_output)
        debug_output.close()

    def debug_grading(self, print_message):
        """This is for debugging purposes. It will write out whatever you pass to it
        to a file called bobsOutput.txt which is saved in your home directory. There
         is no visual indication that you wrote to this file, so just check it with cat"""
        debug_output = open("bobsOutput.txt", 'a')
        print(print_message, file=debug_output)
        debug_output.close()

    class WorkEvent:
        def __init__(self, row):
            """This isn't working for some reason. 
            Maybe has to do with accessing out of range -GK"""


            """this is me debugging whether it gets these attributs. It successfully gets time_stamp"""
            time_stamp = row[0]
            debug_output = open("bobsOutput.txt", 'a')
            print(time_stamp, file=debug_output)
            debug_output.close()
            event_type = row[1]
            '''student_name = row[2]
            lab_name = row[3]
            ta_netid = row[4]
            lock_type = row[5]'''


        def is_lock(self):
            return self.lock_type == "LOCK"

    class StudentAssignment:
        def __init__(self, student, lab):
            student_name = student
            lab_name = lab

        def __lt__(self, other_assignment):
            if (self.student_name == other_assignment.student_name):
                return self.lab_name < other_assignment.lab_name
            return self.student_name < other_assignment.student_name

    def read_in_stats(self, file_name):
        """takes in a csv file and goes through it, using each row to make an event"""
        self.debug_grading(file_name)
        with open(file_name, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                event = GradingStatsWorker.WorkEvent(row)
                #self.debug_grading(row)
                ''' this doesn't work
                if (event.event_type == "LAB"):
                    GradingStatsWorker.events.append(event)
                    '''
                    

    events = []
    mappedEvents = {}