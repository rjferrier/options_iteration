from options_array import OptionsArray, OptionsArrayException
from unit_options_node import UnitOptionsNode


class UnitOptionsArray(OptionsArray):
    """
    This is OptionsArray decoupled from the OptionsNode and
    ArrayNodeInfo implementations for unit testing purposes.
    """
    def create_options_node(self, arg1={}, arg2={}, name_format='{}'):
        return UnitOptionsNode(arg1, arg2, name_format=name_format,
                               array_name=self.name)

    def create_node_info(self, index):
        "Throwaway implementation."
        return ':'.join((self.name, str(self.nodes[index])))
