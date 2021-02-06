#TODO: everything
#make an event class
#WorkEvent init doesn't work and gives all kinds of fun errors

from collections import namedtuple
import csv
import datetime
import time
import typing

from zygrader import data, ui
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
        Step(True, "select helpqueue csv",
             lambda: worker.select_help_queue_data_file()),
        Step(False, "Read data from the log file",
             lambda: worker.read_in_native_stats()),
        Step(False, "Read data from help queue file",
             lambda: worker.read_in_help_queue_stats()),
        Step(True, "validate ta names", lambda: worker.validate_queue_names()),
        Step(False, "Assign events to individual tas",
             lambda: worker.assign_events_to_tas()),
        Step(True, "Debug show events", lambda: worker.show_events()),
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
    def __init__(self, time_stamp, event_type, student_name, ta_name, is_begin,
                 og_data):
        self.time_stamp = time_stamp
        self.event_type = event_type
        self.student_name = student_name
        self.ta_name = ta_name
        self.is_begin = is_begin
        self.og_data = og_data

    @classmethod
    def from_native_data(cls, row):
        time_stamp_str = row[0]
        # TODO: convert to datetime.datetime.fromisoformat
        #   once we are using python 3.7
        time_stamp = datetime.datetime.strptime(time_stamp_str,
                                                "%Y-%m-%dT%H:%M:%S.%f")

        # The old lock format did not have an event_type field
        # (all locks were for labs)
        is_old_format = len(row) == 5
        if is_old_format:
            event_type = 'LAB'
        else:
            event_type = row[1]

        old_format_shift = 1 if is_old_format else 0
        student_name = row[2 - old_format_shift]
        ta_netid = row[4 - old_format_shift]

        # FIXME: ta_netid is a lab name if student has a comman in their name
        #  (this is somewhat fixed in data/lock.py by using csv to write data,
        #   but old data might still have commas)
        #  one possible fix (and what I'm thinking I'll do) is to modify the
        #   the lock log files outside of zygrader,
        #   just with some separate script, to keep this area clean

        lock_type = row[5 - old_format_shift]
        is_lock = lock_type == "LOCK"

        return WorkEvent(time_stamp, event_type, student_name, ta_netid,
                         is_lock, row)

    @classmethod
    def from_queue_data_start_and_end(cls, row):
        student_name = row[1]
        ta_name = row[2]
        # TODO: add netid lookup table

        begin_time_str = row[4]
        begin_time = datetime.datetime.strptime(begin_time_str,
                                                "%m/%d/%Y %I:%M:%S %p")

        duration_str = row[7]
        # duration = datetime.datetime.now()
        if duration_str == "None":  # student helped themselves
            return None, None
        try:
            duration = datetime.datetime.strptime(duration_str, "%M:%S")
        except ValueError:
            try:
                duration = datetime.datetime.strptime(duration_str, "%H:%M:%S")
            except ValueError:
                # TODO: actually log this or present a warning or soemthing
                return None, None

        duration_delta = datetime.timedelta(hours=duration.hour,
                                            minutes=duration.minute,
                                            seconds=duration.second)
        end_time = begin_time + duration_delta

        begin_event = WorkEvent(begin_time, 'HELP', student_name, ta_name, True,
                                row)
        end_event = WorkEvent(end_time, 'HELP', student_name, ta_name, False,
                              row)

        return begin_event, end_event

    def __str__(self):
        return (f"At {self.time_stamp} {self.ta_name} "
                f"{'began' if self.is_begin else 'finished'} "
                f"{self.student_name}'s {self.event_type}"
                f"({self.og_data})")


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
        self.help_events: typing.List[WorkEvent] = []

    def add_event(self, event: WorkEvent):
        self.events.append(event)
        if event.event_type == 'LAB':
            self.lab_events.append(event)
        elif event.event_type == 'EMAIL':
            self.email_events.append(event)
        elif event.event_type == 'HELP':
            self.help_events.append(event)
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
        self.help_stats = EventStreamAnalyzer()

        self.total_stats.analyze(self.events)
        self.lab_stats.analyze(self.lab_events)
        self.email_stats.analyze(self.email_events)
        self.help_stats.analyze(self.help_events)


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

        self.native_events = []
        self.queuee_events = []
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
                event = WorkEvent.from_native_data(row)
                if (event.time_stamp > self.start_time
                        and event.time_stamp < self.end_time):
                    self.native_events.append(event)

    def select_help_queue_data_file(self):
        filepath_entry = ui.layers.PathInputLayer("Help Queue Data")
        ui.get_window().run_layer(filepath_entry)
        if filepath_entry.was_canceled():
            return False
        self.help_queue_csv_filepath = filepath_entry.get_path()
        return True

    def read_in_help_queue_stats(self):
        with open(self.help_queue_csv_filepath, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if not any(row):
                    continue
                begin_event, end_event = (
                    WorkEvent.from_queue_data_start_and_end(row))
                if (begin_event and end_event
                        and begin_event.time_stamp > self.start_time
                        and end_event.time_stamp < self.end_time):
                    self.queuee_events.append(begin_event)
                    self.queuee_events.append(end_event)

    def validate_queue_names(self):
        """Make sure each TA name from the queue has a known netid"""
        window = ui.get_window()
        used_qnames = {event.ta_name for event in self.queuee_events}
        stored_tas = data.get_tas().copy()
        stored_netids = {ta.netid: ta for ta in stored_tas}
        stored_qnames = {ta.queue_name for ta in stored_tas}

        unknown_qnames = used_qnames - stored_qnames

        netid_input = ui.layers.TextInputLayer("Unknown Name in Queue Data")
        for qname in unknown_qnames:
            netid_input.set_prompt([
                f"There is no stored TA with the name {qname}.",
                f"Please enter the netid for {qname}."
            ])
            netid_input.set_text("")
            window.run_layer(netid_input)
            if netid_input.was_canceled():
                return False
            netid = netid_input.get_text()
            if netid in stored_netids:
                stored_netids[netid].queue_name = qname
            else:
                new_ta = data.model.TA(netid, qname)
                stored_netids[netid] = new_ta
                stored_tas.append(new_ta)

        data.write_tas(stored_tas)
        return True

    def assign_events_to_tas(self):
        for event in self.native_events:
            self.tas.setdefault(event.ta_netid,
                                TA(event.ta_netid)).add_event(event)
        # FIXME: Add assigning queuee events

    def analyze_tas_individually(self):
        for ta in self.tas.values():
            ta.analyze_all_events()

    def show_events(self):
        list_layer = ui.layers.ListLayer("Lab events")
        for event in self.native_events:
            list_layer.add_row_text(str(event))
        for event in self.queuee_events:
            list_layer.add_row_text(str(event))
        if not self.native_events and not self.queuee_events:
            list_layer.add_row_text("No events in that time frame")
        ui.get_window().run_layer(list_layer)
        return not list_layer.was_canceled()
