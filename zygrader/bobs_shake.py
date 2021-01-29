#TODO: everything
#make an event class
#WorkEvent init doesn't work and gives all kinds of fun errors

from collections import namedtuple
import csv
import datetime
import time
import typing

from zygrader import ui
from zygrader.data.lock import get_lock_log_path


def start():
    #call get get_lock_log_path()
    window = ui.get_window()
    wait_popup = ui.layers.WaitPopup("Bob's Shake")

    worker = StatsWorker()
    Step = namedtuple('Step', ['interactive', 'msg', 'func'])
    steps = [
        Step(True, "start time", lambda: worker.select_start_time()),
        Step(True, "end time", lambda: worker.select_end_time()),
        Step(False, "Read data from the log file",
             lambda: worker.read_in_native_stats()),
        Step(True, "Debug show events", lambda: worker.show_events()),
        Step(False, "Assign events to individual tas",
             lambda: worker.assign_events_to_tas())
    ]

    for step in steps:
        if step.interactive:
            if not step.func():
                return
        else:
            wait_popup.set_message([step.msg])
            wait_popup.set_wait_fn(step.func)
            window.run_layer(wait_popup)
            if wait_popup.was_canceled():
                return


class WorkEvent:
    def __init__(self, row):
        time_stamp_str = row[0]
        # TODO: convert to datetime.datetime.fromisoformat
        #   once we are using python 3.7
        self.time_stamp = datetime.datetime.strptime(time_stamp_str,
                                                     "%Y-%m-%dT%H:%M:%S.%f")

        # The old lock format did not have an event_type field
        # (all locks were for labs)
        is_old_format = len(row) == 5
        if is_old_format:
            self.event_type = 'LAB'
        else:
            self.event_type = row[1]

        old_format_shift = 1 if is_old_format else 0
        self.student_name = row[2 - old_format_shift]
        self.lab_name = row[3 - old_format_shift]
        self.ta_netid = row[4 - old_format_shift]

        lock_type = row[5 - old_format_shift]
        self.is_lock = lock_type == "LOCK"

    def __str__(self):
        return (f"At {self.time_stamp} {self.ta_netid} "
                f"{'' if self.is_lock else 'un'}locked "
                f"{self.student_name}'s {self.event_type}"
                f"{f' {self.lab_name}' if self.event_type == 'LAB' else ''}")


class EventStreamAnalyzer:
    def __init__(self):
        self.total_time = 0
        self.total_num_openclosed = 0
        self.num_unique_openclosed = 0

    def analyze(events: typing.List[WorkEvent]):
        pass


class TA:
    def __init__(self, netid):
        self.netid = netid
        self.events: typing.List[WorkEvent] = []
        self.lab_events: typing.List[WorkEvent] = []
        self.email_events: typing.List[WorkEvent] = []

    def add_event(self, event: WorkEvent):
        self.events.append(event)
        if event.event_type == 'LAB':
            self.lab_events.append(event)
        elif event.event_type == 'EMAIL':
            self.email_events.append(event)
        else:
            raise ValueError(
                f"Unknown event type '{event.event_type}' encountered")

    def deduplicate_pairprogrammed_grading(self):
        pass

    def analyze_all_events(self):
        self.deduplicate_pairprogrammed_grading()

        self.total_stats = EventStreamAnalyzer()
        self.lab_stats = EventStreamAnalyzer()
        self.email_stats = EventStreamAnalyzer()

        self.total_stats.analyze(self.events)
        self.lab_stats.analyze(self.lab_events)
        self.email_stats.analyze(self.email_events)


class StudentAssignment:
    def __init__(self, student, lab):
        student_name = student
        lab_name = lab

    def __lt__(self, other_assignment):
        if (self.student_name == other_assignment.student_name):
            return self.lab_name < other_assignment.lab_name
        return self.student_name < other_assignment.student_name


def select_time(title: str):
    time_selector = ui.layers.DatetimeSpinner(title)
    time_selector.set_quickpicks([(59, 59), (0, 0)])
    ui.get_window().run_layer(time_selector, "Bob's Shake")

    return (None if time_selector.was_canceled() else time_selector.get_time())


class StatsWorker:
    def __init__(self):
        """This is supposed to clear the bob's output before
         we start writing all the event to it again"""
        debug_output = open("bobsOutput.txt", 'w')
        print("", file=debug_output)
        debug_output.close()

        self.events = []
        self.tas: typing.Dict[str, TA] = dict()

    def select_start_time(self):
        self.start_time = select_time("Start Time")
        return self.start_time

    def select_end_time(self):
        self.end_time = select_time("End Time")
        return self.end_time

    def debug_grading(self, print_message):
        """This is for debugging purposes. It will write out whatever you pass to it
        to a file called bobsOutput.txt which is saved in your home directory. There
         is no visual indication that you wrote to this file, so just check it with cat"""
        debug_output = open("bobsOutput.txt", 'a')
        print(print_message, file=debug_output)
        debug_output.close()

    def read_in_native_stats(self):
        """goes through zygrader's lock log, using each row to make an event"""
        file_name = get_lock_log_path()
        # self.debug_grading(file_name)
        with open(file_name, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                event = WorkEvent(row)
                if (event.time_stamp > self.start_time
                        and event.time_stamp < self.end_time):
                    self.events.append(event)
        # FIXME: Remove this arbitrary sleep (used for debugging)
        time.sleep(1)

    def assign_events_to_tas(self):
        for event in self.events:
            self.tas.setdefault(event.ta_netid,
                                TA(event.ta_netid)).add_event(event)

        # FIXME: Remove this arbitrary sleep (used for debugging)
        time.sleep(1)

    def analyze_tas_individually(self):
        for ta in self.tas.values():
            ta.analyze_all_events()

    def show_events(self):
        list_layer = ui.layers.ListLayer("Lab events")
        for event in self.events:
            list_layer.add_row_text(str(event))
        ui.get_window().run_layer(list_layer)
        return not list_layer.was_canceled()
