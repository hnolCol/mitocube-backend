from abc import ABC, abstractmethod
from config.models.Policy import PolicyModel, PolicyUpdateModel, PolicyStatusModel


class PolicyABC(ABC):

    @abstractmethod
    def get(self) -> PolicyModel | None: ...

    @abstractmethod
    def update(self, policy : PolicyUpdateModel, user_tag : str) -> PolicyModel: ...

    @abstractmethod
    def agree(self, user_tag : str) -> bool: ...

    @abstractmethod
    def get_status(self, user_tag : str) -> PolicyStatusModel: ...