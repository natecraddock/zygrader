#TODO: everything
#make an event class

import csv


def start():
    pass


class grading_stats_worker:
    class work_event:
        def __init__(self, row):
            time_stamp = row[0]
            event_type = row[1]
            student_name = row[2]
            lab_name = row[3]
            ta_netid = row[4]
            lock_type = row[5]

        def is_lock(self):
            return self.lock_type == "LOCK"

    class student_assignment:
        def __init__(self, student, lab):
            student_name = student
            lab_name = lab

        def __lt__(self, other_assignment):
            if (self.student_name == other_assignment.student_name):
                return self.lab_name < other_assignment.lab_name
            return self.student_name < other_assignment.student_name

    def read_in_stats(file_name):
        """takes in a csv file and goes through it, using each row to make an event"""
        with open(file_name, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                event = grading_stats_worker.work_event(row)
                if (event.event_type == "LAB"):
                    grading_stats_worker.events.append(event)

    events = []
    mappedEvents = {}