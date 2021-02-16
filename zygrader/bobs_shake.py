"""Bob's Shake: A tool to analyze TA work statistics.

`shake` is the singular entry point to this module
"""
# TODO: run my 'history fixer' on the lock log
# (explained in a FIXME below, which should also be removed)

from collections import namedtuple
import csv
import datetime
import os
import typing

from zygrader import data, ui
from zygrader.data.lock import get_lock_log_path
from zygrader.config import preferences
from zygrader.ui.templates import filename_input


def shake():
    """Read TA work data, "shake" it, and report the shaken statistics.

    Results summarize work in grading, answering emails, and helping students.
    For each category of work, Bob's Shake reports the number of items finished
    by a TA and the total time spent on those items.

    Resulting summary statistics are written to a file chosen by the user.

    Some TA data is read from zygrader's own native lock log,
    and additional data is read from a csv file created by our help queue.

    "shaking" occurs in a series of steps, roughly:
        - user selects start and end time to include
        - user points Bob to the data from the help queue
        - data is read from zygrader's log and the queue info
        - errors encountered and corrections that need to be made
          are presented to the user
        - input data is assigned to each TA appropriately
        - each TA's events are analyzed to calculate the results summary
        - user selects an output file
        - the summary statistics are written to the file
    """
    window = ui.get_window()
    wait_popup = ui.layers.WaitPopup("Bob's Shake")

    worker = _StatsWorker()
    Step = namedtuple('Step', ['interactive', 'msg', 'func'])
    steps = [
        Step(True, None, worker.select_start_time),
        Step(True, None, worker.select_end_time),
        Step(True, None, worker.select_help_queue_data_file),
        Step(False, "Read data from the log file", worker.read_in_native_stats),
        Step(False, "Read data from help queue file",
             worker.read_in_help_queue_stats),
        Step(True, None, worker.present_queue_errors),
        Step(True, None, worker.validate_queue_names),
        Step(False, "Assign events to individual tas",
             worker.assign_events_to_tas),
        Step(False, "Analyze stats for each TA",
             worker.analyze_tas_individually),
        Step(True, None, worker.select_output_file),
        Step(False, "Write shaken stats to file", worker.write_stats_to_file)
    ]

    _WorkEvent.queue_errors = []

    for step in steps:
        if step.interactive:
            if not step.func():
                return
        else:
            wait_popup.set_message([step.msg])
            wait_popup.set_wait_fn(step.func)
            window.run_layer(wait_popup)
            if wait_popup.canceled:
                return


class _WorkEvent:
    queue_errors = []

    def __init__(self, time_stamp, event_type, student_name, ta_name, is_begin,
                 og_data, uniq_item):
        self.time_stamp = time_stamp
        self.event_type = event_type
        self.student_name = student_name
        self.ta_name = ta_name
        self.is_begin = is_begin
        self.og_data = og_data
        self.uniq_item = uniq_item

    @classmethod
    def from_native_data(cls, row):
        time_stamp_str = row[0]
        # TODO: convert to datetime.datetime.fromisoformat
        # once we are using python 3.7
        time_stamp = datetime.datetime.strptime(time_stamp_str,
                                                "%Y-%m-%dT%H:%M:%S.%f")

        # The old lock format did not have an event_type field
        # (all locks were for labs)
        is_old_format = len(row) == 5
        if is_old_format:
            row.insert(1, "LAB")

        event_type = row[1]
        student_name = row[2]
        assignment_name = row[3]
        ta_netid = row[4]

        uniq_item = event_type + student_name + assignment_name

        # FIXME: ta_netid is a lab name if student has a comma in their name
        # (this is somewhat fixed in data/lock.py by using csv to write data,
        # but old data might still have commas)
        #
        # one possible fix (and what I'm thinking I'll do) is to modify the
        # the lock log files outside of zygrader,
        # just with some separate script, to keep this area clean

        lock_type = row[5]
        is_lock = lock_type == "LOCK"

        return _WorkEvent(time_stamp, event_type, student_name, ta_netid,
                          is_lock, row, uniq_item)

    uniq_help_id = 0

    @classmethod
    def from_queue_data_start_and_end(cls, row):
        try:
            student_name = row[1]
            ta_name = row[2]

            begin_time_str = row[4]
            begin_time = datetime.datetime.strptime(begin_time_str,
                                                    "%m/%d/%Y %I:%M:%S %p")

            duration_str = row[7]
            if duration_str == "None":  # student helped themselves
                return None, None
            try:
                minute_str, second_str = duration_str.split(":")
                minutes = int(minute_str)
                seconds = int(second_str)
            except ValueError:
                cls.queue_errors.append(row)
                return None, None
            duration_delta = datetime.timedelta(minutes=minutes,
                                                seconds=seconds)

            end_time = begin_time + duration_delta

            uniq_item = f'HELP{cls.uniq_help_id}'
            cls.uniq_help_id += 1

            begin_event = _WorkEvent(begin_time, 'HELP', student_name, ta_name,
                                     True, row, uniq_item)
            end_event = _WorkEvent(end_time, 'HELP', student_name, ta_name,
                                   False, row, uniq_item)

            return begin_event, end_event
        except Exception:
            cls.queue_errors.append(row)
            return None, None

    def __str__(self):
        return (f"At {self.time_stamp} {self.ta_name} "
                f"{'began' if self.is_begin else 'finished'} "
                f"{self.student_name}'s {self.event_type}"
                f"({self.og_data})")


def _sandwiches(outer_pair, inner_pair):
    outer_begin, outer_end = outer_pair
    inner_begin, inner_end = inner_pair
    return (outer_begin.time_stamp < inner_begin.time_stamp
            and outer_end.time_stamp > inner_end.time_stamp)


class _EventStreamStats:
    REAL_WORK_THRESHOLD = datetime.timedelta(seconds=15)

    def __init__(self):
        self.total_time = datetime.timedelta()
        self.total_num_closed = 0
        self.worked_event_pairs = []

    def analyze(self, events: typing.List[_WorkEvent]):
        if not events:
            return
        # events from queue data might not be sorted
        sorted_events = sorted(events, key=lambda event: event.time_stamp)

        # maps from uniq_item key to begin event for that item
        # until the close event is encountered
        open_items = dict()
        open_close_pairs = []

        for event in sorted_events:
            if event.is_begin:
                if event.uniq_item not in open_items:
                    open_items[event.uniq_item] = event
            else:
                if event.uniq_item in open_items:
                    open_close_pairs.append(
                        (open_items[event.uniq_item], event))
                    del open_items[event.uniq_item]

        # if an item was both locked and unlocked while another item was open,
        # then it doesn't count, so we remove sandwiched items
        new_worked_event_pairs = []
        for open_close_pair in open_close_pairs:
            if not any(
                    map(lambda outer: _sandwiches(outer, open_close_pair),
                        open_close_pairs)):
                open_event, close_event = open_close_pair
                time_spent = close_event.time_stamp - open_event.time_stamp
                if time_spent > _EventStreamStats.REAL_WORK_THRESHOLD:
                    new_worked_event_pairs.append(open_close_pair)
                    self.total_time += time_spent

        self.worked_event_pairs = sorted(
            self.worked_event_pairs + new_worked_event_pairs,
            key=lambda p: (p[0].time_stamp, p[1].time_stamp))

        self.total_num_closed = len(self.worked_event_pairs)


class _TA:
    def __init__(self, netid):
        self.netid = netid
        self.lab_events: typing.List[_WorkEvent] = []
        self.email_events: typing.List[_WorkEvent] = []
        self.help_events: typing.List[_WorkEvent] = []

    def add_event(self, event: _WorkEvent):
        if event.event_type == 'LAB':
            self.lab_events.append(event)
        elif event.event_type == 'EMAIL':
            self.email_events.append(event)
        elif event.event_type == 'HELP':
            self.help_events.append(event)
        else:
            raise ValueError(
                f"Unknown event type '{event.event_type}' encountered")

    def analyze_all_events(self):
        self.lab_stats = _EventStreamStats()
        self.email_stats = _EventStreamStats()
        self.help_stats = _EventStreamStats()

        self.lab_stats.analyze(self.lab_events)
        self.email_stats.analyze(self.email_events)
        self.help_stats.analyze(self.help_events)


def _select_time(title: str, default_time: datetime.time):
    time_selector = ui.layers.DatetimeSpinner(title)
    time_selector.set_quickpicks([(59, 59), (0, 0)])
    initial_time = datetime.datetime.combine(datetime.datetime.today(),
                                             default_time)
    time_selector.set_initial_time(initial_time)
    ui.get_window().run_layer(time_selector, "Bob's Shake")

    return (None if time_selector.canceled else time_selector.get_time())


class _StatsWorker:
    def __init__(self):
        self.native_events = []
        self.queuee_events = []
        self.tas: typing.Dict[str, _TA] = dict()

    def select_start_time(self):
        self.start_time = _select_time(
            "Start Time", datetime.time(hour=0, minute=0, second=0))
        return self.start_time

    def select_end_time(self):
        self.end_time = _select_time(
            "End Time", datetime.time(hour=23, minute=59, second=59))
        return self.end_time

    def read_in_native_stats(self):
        """goes through zygrader's lock log, using each row to make an event"""
        file_name = get_lock_log_path()
        with open(file_name, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                event = _WorkEvent.from_native_data(row)
                if (event.time_stamp > self.start_time
                        and event.time_stamp < self.end_time):
                    self.native_events.append(event)

    def select_help_queue_data_file(self):
        filepath_entry = ui.layers.PathInputLayer("Help Queue Data")
        filepath_entry.set_prompt([
            "Enter the path to the queue data",
            "(you should have copy-pasted the data from the queue into a file)",
            ""  # empty line
        ])
        ui.get_window().run_layer(filepath_entry)
        if filepath_entry.canceled:
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
                    _WorkEvent.from_queue_data_start_and_end(row))
                if (begin_event and end_event
                        and begin_event.time_stamp > self.start_time
                        and end_event.time_stamp < self.end_time):
                    self.queuee_events.append(begin_event)
                    self.queuee_events.append(end_event)

    def present_queue_errors(self):
        error_rows = _WorkEvent.queue_errors
        if not error_rows:
            return True

        path_input = ui.layers.PathInputLayer("Queue Data Errors")
        path_input.set_prompt([
            "There were some queue data entries that caused errors.",
            "Select a file to write them to so that"
            " you can manually adjust the stats for them.",
            "",  # empty line
            "If you find common errors, please open an issue on the"
            " github repo, or talk to a maintainer directly.",
            ""  # empty line
        ])
        default_path = os.path.join(preferences.get("output_dir"),
                                    "bad-queue-data.csv")
        path_input.set_text(default_path)
        ui.get_window().run_layer(path_input)
        if path_input.canceled:
            return False

        with open(path_input.get_path(), "w", newline="") as out_file:
            writer = csv.writer(out_file)
            writer.writerows(error_rows)

        return True

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
            if netid_input.canceled:
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
            self.tas.setdefault(event.ta_name,
                                _TA(event.ta_name)).add_event(event)

        tas = data.get_tas()
        lookup = {ta.queue_name: ta.netid for ta in tas}
        for event in self.queuee_events:
            netid = lookup[event.ta_name]
            self.tas.setdefault(netid, _TA(netid)).add_event(event)

    def analyze_tas_individually(self):
        for ta in self.tas.values():
            ta.analyze_all_events()

    def select_output_file(self):
        default_output_path = os.path.join(preferences.get("output_dir"),
                                           "shaken-stats.csv")
        path = filename_input(purpose="the shaken stats",
                              text=default_output_path)
        if path is None:
            return False
        self.output_path = path
        return True

    def write_stats_to_file(self):
        with open(self.output_path, "w", newline="") as out_file:
            writer = csv.writer(out_file)
            writer.writerow([
                "Netid", "Grading Count", "Grading Time", "Email Count",
                "Email Time", "Help Count", "Help Time"
            ])
            writer.writerows([[
                netid, ta.lab_stats.total_num_closed, ta.lab_stats.total_time,
                ta.email_stats.total_num_closed, ta.email_stats.total_time,
                ta.help_stats.total_num_closed, ta.help_stats.total_time
            ] for netid, ta in self.tas.items()])
