import os
import json
from multiprocessing import Process, Manager
#from pathlib import Path
import logging

from . import trains, protos, enigmap
from pyprove import expres, log

DEFAULT_NAME = "Enigma"
DEFAULT_DIR = os.getenv("ENIGMA_ROOT", DEFAULT_NAME)

logger = logging.getLogger(__name__)

def name(bid, limit, dataname, features, learner, parents=False, **others):
   if parents:
       return "%s/%s-%s/%s/%s/%s" % ("parents", bid.replace("/","-"), limit, dataname, features, learner.desc())
   return "%s-%s/%s/%s/%s" % (bid.replace("/","-"), limit, dataname, features, learner.desc())

def path(**others):
   return os.path.join(DEFAULT_DIR, name(**others))

def pathfile(f_file, **others):
   return os.path.join(path(**others), f_file)

def filename(learner, **others):
   #model = name(learner=learner, **others)
   f_file = "model.%s" % learner.ext()
   f_mod = pathfile(f_file, learner=learner, **others)
   return f_mod

def build(learner, debug=[], options=[], **others):
   f_in = os.path.join(trains.path(**others), "train.in") 
   model = name(learner=learner, **others)
   logger.info("+ building model %s" % model)
   f_mod = filename(learner=learner, **others)
   os.system('mkdir -p "%s"' % os.path.dirname(f_mod))
   enigmap.build(learner=learner, debug=debug, **others)
   #learner.params["num_feature"] = enigmap.load(learner=learner, **others)["count"]
   
   new = protos.build(model, learner=learner, debug=debug, **others)
   if os.path.isfile(f_mod) and not "force" in debug:
      logger.debug("- skipped building model %s" % f_mod)
      #return new
      
   else:
       f_log = pathfile("train.log", learner=learner, **others)
       #learner.build(f_in, f_mod, f_log)
       p = Process(target=learner.build, args=(f_in,f_mod,f_log,options))
       p.start()
       p.join()
   
    # Create a symlink to the data folder. 
   #if others.get("parents", False):
   #  s_dir = Path(os.path.join(DEFAULT_DIR, "parent_model"))
   #  if s_dir.is_symlink():
   #      s_dir.unlink()
   #  s_dir.symlink_to(Path(model))

   return new

def loop(pids, results, nick, **others):
   print(others.keys())
   others["dataname"] += "/" + nick
   trains.build(pids=pids, **others)
   newp = build(pids=pids, **others)
   newr = expres.benchmarks.eval(pids=newp, **others)
   pids.extend(newp)
   results.update(newr)
   return newp

def loop_parents(pids, results, nick, parents="merge", fid1=None, fid2=None, learner1=None, learner2=None, **others):
   others["dataname"] += "/" + nick
   
   others["parents"] = None
   others["features"] = fid1 if fid1 else others["features"]
   others["learner"] = learner1 if learner1 else others["learner"]
   trains.build(pids=pids, **others)
   newp = build(pids=pids, **others)
   
   # Allows the above Selector to be passed to the Filter (superseded by "eref")
   others["eref2"] = os.path.join(DEFAULT_DIR, name(**others))
   
   others["parents"] = parents
   others["features"] = fid2 if fid2 else others["features"]
   others["learner"] = learner2 if learner2 else others["learner"]
   trains.build(pids=pids, **others)
   newp += build(pids=pids, **others)
   
   newr = expres.benchmarks.eval(pids=newp, **others)
   pids.extend(newp)
   results.update(newr)
   
   return newp

def accuracy(learner, f_in, f_mod):
   manager = Manager()
   ret = manager.dict()
   p = Process(target=learner.accuracy, args=(f_in,f_mod,ret))
   p.start()
   p.join()
   return ret["acc"]

