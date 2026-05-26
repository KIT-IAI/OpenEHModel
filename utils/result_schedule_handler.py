from functools import reduce
import os

class ResultScheduleHandler():
    '''
    This class handles the result schedule of the energy hub.

    Attributes:
        schedule_filename (str): The filename of the schedule file.
        file (file): The file object used to write the schedule data.
        first_line (bool): A flag indicating whether the first line has been written to the file.

    Methods:
        write_day(schedule: list): Writes a day's schedule to the file.
        read_day(day: int): Reads the schedule for a specific day.

    '''

    def __init__(self, schedule_filename: str, array_delimiter: chr = ';', value_delimiter: chr = ',') -> None:
        self.__schedule_filename = schedule_filename
        self.__file = open(schedule_filename, "w+")
        self.__first_line = True
        self.__array_delimiter = array_delimiter
        self.__value_delimiter = value_delimiter
        self.__days = []

    def write_day(self, schedule):
        if self.__first_line:
            self.__file.write(reduce(lambda x, y: f"{x}{self.__array_delimiter}{y}", list(schedule.keys())))
            self.__file.write("\n")
            self.__first_line = False
        self.__file.write(reduce(lambda x, y: f"{x}{self.__array_delimiter}{y}", [reduce(lambda x, y: f"{x}{self.__value_delimiter}{y}", [v for v in comp_sched]) for comp_sched in schedule.values()]))
        self.__file.write("\n")

    def read_file(self):
        keys = self.__file.readline().split(self.__array_delimiter)
        for line in self.__file:
            values = line.split(self.__array_delimiter)
            self.__days.append({keys[i]: [float(v) for v in values[i].split(self.__value_delimiter)] for i in range(len(keys))})

    def get_day(self, day: int):
        pass