import abc


class Agent(abc.ABC):

    @abc.abstractmethod
    def invoke(self, *args, **kwargs):
        pass
