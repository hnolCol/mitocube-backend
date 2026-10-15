from abc import ABC, abstractmethod

from config.models.Impressum import ImpressumModel, ImpressumUpdateModel


class ImpressumABC(ABC):

    @abstractmethod
    def get(self) -> ImpressumModel | None: ...

    @abstractmethod
    def update(self, impressum : ImpressumUpdateModel, user_tag : str) -> ImpressumModel: ...
