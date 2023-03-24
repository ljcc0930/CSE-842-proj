from .GA import GA,GA_l1
from .RL import RL
from .FT import FT,FT_l1
from .fisher import fisher,fisher_new
from .retrain import retrain
from .impl import load_unlearn_checkpoint, save_unlearn_checkpoint
from .Wfisher import Wfisher
def raw(data_loaders, model, criterion, args):
    pass


def get_unlearn_method(name):
    """ method usage:

    function(data_loaders, model, criterion, args)"""
    if name == "raw":
        return raw
    elif name == "RL":
        return RL
    elif name == "GA":
        return GA
    elif name == "FT":
        return FT
    elif name == "FT_l1":
        return FT_l1
    elif name == "fisher":
        return fisher
    elif name == "retrain":
        return retrain
    elif name== "fisher_new":
        return fisher_new
    elif name == "wfisher":
        return Wfisher
    elif name == "GA_l1":
        return GA_l1
    else:
        raise NotImplementedError(f"Unlearn method {name} not implemented!")