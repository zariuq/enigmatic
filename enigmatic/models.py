import os, shutil
import json
from multiprocessing import Process, Manager
from pathlib import Path
import logging

from . import trains, protos, enigmap
from pyprove import expres, log

DEFAULT_NAME = "Enigma"
DEFAULT_DIR = os.getenv("ENIGMA_ROOT", DEFAULT_NAME)

logger = logging.getLogger(__name__)

#<<<<<<< HEAD
#def name(bid, limit, dataname, features, learner, parents=False, **others):
#   if parents: #others.get("parents", False):
#       return "%s/%s-%s/%s/%s/%s" % ("parents", bid.replace("/","-"), limit, dataname, features, learner.desc())
#   return "%s-%s/%s/%s/%s" % (bid.replace("/","-"), limit, dataname, features, learner.desc())

def name(learner, parents=False, **others):
   others = dict(others, learner=learner)
   if parents:
       return os.path.join("parents", trains.name(**others), learner.desc())       
   return os.path.join(trains.name(**others), learner.desc())

def path(**others):
   return os.path.join(DEFAULT_DIR, name(**others))

def pathfile(f_file, **others):
   return os.path.join(path(**others), f_file)

def filename(learner, part=None, **others):
   model = name(learner=learner, **others)
   f_file = "model.%s" % learner.ext()
   if part is not None:
      f_file = os.path.join("part%03d"%part, f_file)
   f_mod = pathfile(f_file, learner=learner, **others)
   return f_mod

def batchbuilds(f_in, f_mod, learner, options, **others):
   n = 0
   f_part = None
   f_log = None
   def nextbatch():
      nonlocal n, f_part, f_log
      n += 1
      f_part = trains.filename(part=n, **others)
      f_log = filename(learner=learner, part=n, **others) + ".log"
   nextbatch()
   while trains.exist(f_part) or os.path.isfile(f_part):
      #learner.params["learning_rate"] = learner.params["learning_rate"]*0.1
      logger.info("- next batch build with %s" % f_part)
      os.system('mkdir -p "%s"' % os.path.dirname(f_log))
      f_piece = filename(learner=learner, part=n-1, **others)
      shutil.copy(f_mod, f_piece)
      p = Process(target=learner.build, args=(f_part,f_mod,f_log,options,f_mod))
      p.start()
      p.join()
      nextbatch()

def build(learner, f_in=None, f_test=None, split=False, debug=[], options=[], **others):
   others = dict(others, learner=learner, split=split, debug=debug, options=options)
   f_in = f_in if f_in else trains.filename(part=0, **others)
   if split and not f_test:
      f_test = trains.filename(part=0, f_name="test.in", **others)
   model = name(**others)
   logger.info("+ building model %s" % model)
   logger.info("- building with %s" % f_in)
   f_mod = filename(**others)
   os.system('mkdir -p "%s"' % os.path.dirname(f_mod))
   enigmap.build(**others)
   #learner.params["num_feature"] = enigmap.load(learner=learner, **others)["count"]
   new = protos.build(model, **others)
   if os.path.isfile(f_mod) and not "force" in debug:
      logger.debug("- skipped building model %s" % f_mod)
      return new

   f_log = filename(part=0, **others) + ".log"
   os.system('mkdir -p "%s"' % os.path.dirname(f_log))
   p = Process(target=learner.build, args=(f_in,f_mod,f_log,options,None,f_test))
   p.start()
   p.join()

       # Create a symlink to the data folder.  Especially useful for looping.
   if others.get("parents", False):
     s_dir = Path(os.path.join(DEFAULT_DIR, "parent_model"))
     if s_dir.is_symlink():
         s_dir.unlink()
     s_dir.symlink_to(Path(model))

   batchbuilds(f_in, f_mod, **others)
   statistics(f_in, f_mod, f_log, **others) # Possibly related to code in pyprove.  On hold. 
   return new

def statistics(f_in, f_mod, f_log, learner, split, debug, **others):
   others = dict(others, learner=learner, split=split, debug=debug)
   f_stats = "%s-stats.json" % f_log
   stats = json.load(open(f_stats))
   if "acc" in debug:
      ret = accuracy(learner, f_in, f_mod)
      stats["train.acc"] = ret["acc"]
      f_test = trains.filename(f_name="test.in", part=0, **others)
      if split and (os.path.isfile(f_test) or trains.exist(f_test)):
         ret = accuracy(learner, f_test, f_mod)
         stats["test.acc"] = ret["acc"]
         stats["test.counts"] = ret["counts"]
   with open(f_stats,"w") as f: json.dump(stats, f, indent=3, sort_keys=True)
   logger.info(log.data("- training statistics: ", stats))

''' # Outdated gentle-merge
def loop(pids, results, nick, **others):
   print(others.keys()) # Is this some typo? print(others["others"].keys())
   others["dataname"] += "/" + nick
   trains.build(pids=pids, **others)
   newp = build(pids=pids, **others)
   newr = expres.benchmarks.eval(pids=newp, **others)
   pids.extend(newp)
   results.update(newr)
   return newp
'''

def loop1(nick, pids, results, dataname, options=[], **others):
   others = dict(others, pids=pids, results=results, options=options, dataname=os.path.join(dataname,nick))
   trains.build(**others)
   newp = build(**others)
   if "loop-coop-only" in options:
      newp = [p for p in newp if "coop" in p]
   newr = expres.benchmarks.eval(**dict(others, pids=newp))
   pids.extend(newp)
   results.update(newr)
   
   return newp

def loops(iters=6, results={}, **others):
   others = dict(others, results=results)
   results.update(expres.benchmarks.eval(**others))
   for n in range(iters):
      loop1("loop%02d"%n, **others)
      
#Important to note that the parents model is not a new strategy!
#However the parents model's model can be reliably accessed via the symlink
#And, okay, many more convenient personal options (to the extent this shouldn't be in the 'repo' :-p
def loop_parents(pids, results, nick, parents="merge", fid1=None, fid2=None, learner1=None, learner2=None, **others):
   #print(others.keys()) # Is this some typo? print(others["others"].keys())
   others["dataname"] += "/" + nick
   
   others["parents"] = None
   others["features"] = fid1 if fid1 else others["features"]
   others["learner"] = learner1 if learner1 else others["learner"]
   trains.build(pids=pids, **others)
   newp = build(pids=pids, **others)
   
   # Allows the aboven Selector to be passed to the Filter (superseded by "eref")
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
   return dict(ret)

