from __future__ import annotations
from abc import abstractmethod
from datetime import timedelta

from typing import Self

import lib.data as dlib

# from config import get_system_settings
from lib.designpatterns import ExpiringValue

class ABCStatDatabaseError(dlib.ABCDataError):
    pass

class CachedStatDatabase(dlib.ABCStatDatabase):

    def __init__(self):
        # def dofu(): return Self.determine_n_submissions()  # Fixme: Does not work, solution to define module function, and always grap the singleton object... can one not directly call function from here?
        # Question: Why can i not call self._determine_n_submissions() here? Within that function it stucks at getting the connection courser from the pool PostgreSQLConnection
        self.__cached_n_submissions = ExpiringValue[int](expireTime = timedelta(minutes = 5), value = None,  # ToDo: Make time configurable
                                                         updateProcess = lambda : 42)  # lambda : self._determine_n_submissions())  # lambda : 42)  #self: self._determine_n_submissions())  # Fixme: Does not work, AttributeError: determine_n_submissions
                                                         # updateProcess = Self._determine_n_submissions.__func__
                                                         # open.__get__(object)
                                                         # updateProcess = self._determine_n_submissions)  # Fixme: Does not work

        self.__cached_n_active_datasets = ExpiringValue[int](expireTime = timedelta(minutes = 5), value = None,
                                                             updateProcess = lambda : 42)  # self._determine_n_submissions())

        self.__cached_n_pg_features = ExpiringValue[int](expireTime = timedelta(minutes = 5), value = None,
                                                         updateProcess = lambda : 42)  # self._determine_n_submissions())

        self.__cached_n_genotypes = ExpiringValue[int](expireTime = timedelta(minutes = 5), value = None,
                                                       updateProcess = lambda : 42)  # self._determine_n_submissions())

        self.__cached_n_active_users = ExpiringValue[int](expireTime = timedelta(minutes = 5), value = None,
                                                          updateProcess = lambda : 42)  # self._determine_n_submissions())

    @staticmethod
    @abstractmethod
    def _determine_n_submissions() -> int:  # Move definition to ABCDatabase
        pass

    @staticmethod
    @abstractmethod
    def _determine_n_active_datasets() -> int:  # Move definition to ABCDatabase
        pass

    @staticmethod
    @abstractmethod
    def _determine_n_pg_features() -> int:  # Move definition to ABCDatabase
        pass

    @staticmethod
    @abstractmethod
    def _determine_n_genotypes() -> int:  # Move definition to ABCDatabase
        pass

    @staticmethod
    @abstractmethod
    def _determine_n_active_users() -> int:  # Move definition to ABCDatabase
        pass

    def get_n_submissions(self) -> int:  # Move definition to ABCDatabase
        return self.__cached_n_submissions.get()

    def get_n_active_datasets(self) -> int:  # Move definition to ABCDatabase
        return self.__cached_n_active_datasets.get()

    def get_n_pg_features(self) -> int:  # Move definition to ABCDatabase
        return self.__cached_n_pg_features.get()

    def get_n_genotypes(self) -> int:  # Move definition to ABCDatabase
        return self.__cached_n_genotypes.get()

    def get_n_active_users(self) -> int:  # Move definition to ABCDatabase
        return self.__cached_n_active_users.get()
