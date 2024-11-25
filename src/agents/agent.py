import abc


class Agent(abc.ABCMeta):

    @abc.abstractmethod
    def invoke(self, *args, **kwargs):
        pass
