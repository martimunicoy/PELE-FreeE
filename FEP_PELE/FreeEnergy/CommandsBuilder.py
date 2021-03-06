# -*- coding: utf-8 -*-


# FEP_PELE imports
from .Constants import COMMAND_NAMES_DICT
from .CommandTypes.LambdasSampling import LambdasSampling
from .CommandTypes.dECalculation import dECalculation
from .CommandTypes.SerialdECalculation import SerialdECalculation
from .CommandTypes.ExponentialAveraging import ExponentialAveraging
from .CommandTypes.UnbounddECalculation import UnbounddECalculation
from .CommandTypes.SolvationFreeEnergyCalculation \
    import SolvationFreeEnergyCalculation


# Script information
__author__ = "Marti Municoy"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Marti Municoy"
__email__ = "marti.municoy@bsc.es"


class CommandsBuilder(object):
    def __init__(self, settings):
        self.settings = settings
        self.commands_names = settings.command_names

    def createCommands(self):
        commands = []
        for command_name in self.commands_names:
            command = self.getCommandFromName(command_name)
            commands.append(command)

        return commands

    def getCommandFromName(self, command_name):
        if (command_name == COMMAND_NAMES_DICT["LAMBDAS_SAMPLING"]):
            return LambdasSampling(self.settings)
        elif (command_name == COMMAND_NAMES_DICT["DE_CALCULATION"]):
            return dECalculation(self.settings)
        elif (command_name == COMMAND_NAMES_DICT["SERIAL_DE_CALCULATION"]):
            return SerialdECalculation(self.settings)
        elif (command_name == COMMAND_NAMES_DICT["EXPONENTIAL_AVERAGING"]):
            return ExponentialAveraging(self.settings)
        if (command_name == COMMAND_NAMES_DICT["UNBOUND_DE_CALCULATION"]):
            return UnbounddECalculation(self.settings)
        elif (command_name == COMMAND_NAMES_DICT[
                "SOLVATION_FREE_ENERGY_CALCULATION"]):
            return SolvationFreeEnergyCalculation(self.settings)
        else:
            print("Command {} not recogniced".format(command_name))
            exit(1)
