import re, os
from pyprove import expres, log
from . import models
import logging

logger = logging.getLogger(__name__)

def cef(freq, efun, fname, prio="PreferWatchlist", binary_weigths=1, threshold=0.5):
   cef = '%d*%s(%s,"%s",%s,%s)' % (freq,efun,prio,fname,binary_weigths,threshold)
   return cef

def solo(pid, name, mult=0, noinit=False, efun="Enigma", fullname=False, binary_weigths=1, threshold=0.5, prio="PreferWatchlist"):
   proto = expres.protos.load(pid)
   fname = os.path.join(models.DEFAULT_DIR, name)
   enigma = cef(1, efun, fname, prio, binary_weigths, threshold)
   eproto = "%s-H'(%s)'" % (proto[:proto.index("-H'")], enigma)
   if noinit:
      eproto = eproto.replace("--prefer-initial-clauses", "")
   if fullname:
      post = efun
      post += ("0M%s" % mult) if mult else "0"
      if noinit:
         post += "No" 
      epid = "Enigma+%s+%s+%s" % (name.replace("/","+"), pid, post)
   else:
      epid = "Enigma+%s+solo-%s" % (name.replace("/","+"), pid)
   expres.protos.save(epid, eproto)
   return epid

def coop(pid, name, freq=None, mult=0, noinit=False, efun="Enigma", fullname=False, binary_weigths=1, threshold=0.5, prio="PreferWatchlist"):
   proto = expres.protos.load(pid)
   fname = os.path.join(models.DEFAULT_DIR, name)
   post = efun
   if not freq:
      freq = sum(map(int,re.findall(r"(\d*)\*", proto)))
      post += "S"
   else:
      post += "F%s"% freq
   post += ("M%s" % mult) if mult else ""
   enigma = cef(freq, efun, fname, prio, binary_weigths, threshold)
   eproto = proto.replace("-H'(", "-H'(%s,"%enigma)
   if noinit:
      eproto = eproto.replace("--prefer-initial-clauses", "")
   if fullname:
      if noinit:
         post += "No"
      epid = "Enigma+%s+%s+%s" % (name.replace("/","+"), pid, post)
   else:
      epid = "Enigma+%s+coop-%s" % (name.replace("/","+"), pid)
   expres.protos.save(epid, eproto)
   return epid

def coop_parents(pid, name, mult=0, noinit=False, efun="Enigma", fullname=False):
   proto = expres.protos.load(pid)
   fname = os.path.join(models.DEFAULT_DIR, name)
   eproto = proto.replace("-H'(", "--filter-generated-clauses=\"%s\" -H'" % fname)
   if noinit:
      eproto = eproto.replace("--prefer-initial-clauses", "")
   if fullname:
      post = efun
      post += ("0M%s" % mult) if mult else "0"
      if noinit:
         post += "No" 
      epid = "Enigma+%s+%s+%s" % (name.replace("/","+"), pid, post)
   else:
      epid = "Enigma+%s+coop-f-%s" % (name.replace("/","+"), pid)
   expres.protos.save(epid, eproto)
   return epid

def solo_parents_and_selection(pid, name, s_name, mult=0, noinit=False, efun="Enigma", fullname=False, binary_weigths=1, threshold=0.5, prio="PreferWatchlist"):
   proto = expres.protos.load(pid)
   fname = os.path.join(models.DEFAULT_DIR, name)
   fsname = os.path.join(models.DEFAULT_DIR, s_name)
   enigma = cef(1, efun, fsname, prio, binary_weigths, threshold)
   eproto = "%s--filter-generated-clauses=\"%s\" -H'(%s)'" % (proto[:proto.index("-H'")], fname, enigma)
   if noinit:
      eproto = eproto.replace("--prefer-initial-clauses", "")
   if fullname:
      post = efun
      post += ("0M%s" % mult) if mult else "0"
      if noinit:
         post += "No" 
      epid = "Enigma+%s+%s+%s" % (name.replace("/","+"), pid, post)
   else:
      epid = "Enigma+%s+solo-sf-%s" % (name.replace("/","+"), pid)
   expres.protos.save(epid, eproto)
   return epid

def coop_parents_and_selection(pid, name, s_name, freq=None, mult=0, noinit=False, efun="Enigma", fullname=False, binary_weigths=1, threshold=0.5, prio="PreferWatchlist"):
   proto = expres.protos.load(pid)
   fname = os.path.join(models.DEFAULT_DIR, name)
   fsname = os.path.join(models.DEFAULT_DIR, s_name)
   post = efun
   if not freq:
      freq = sum(map(int,re.findall(r"(\d*)\*", proto)))
      post += "S"
   else:
      post += "F%s"% freq
   post += ("M%s" % mult) if mult else ""
   enigma = cef(freq, efun, fsname, prio, binary_weigths, threshold)
   eproto = proto.replace("-H'(", "--filter-generated-clauses=\"%s\" -H'(%s," % (fname, enigma))
   if noinit:
      eproto = eproto.replace("--prefer-initial-clauses", "")
   if fullname:
      post = efun
      post += ("0M%s" % mult) if mult else "0"
      if noinit:
         post += "No" 
      epid = "Enigma+%s+%s+%s" % (name.replace("/","+"), pid, post)
   else:
      epid = "Enigma+%s+coop-sf-%s" % (name.replace("/","+"), pid)
   expres.protos.save(epid, eproto)
   return epid


def build(model, learner, pids=None, refs=None, parents=False, **others):
   refs = refs if refs else pids
   logger.info("- creating Enigma strategies for model %s" % model)
   logger.debug("- base strategies: %s" % refs)
   efun = learner.efun()
   new = []
   for ref in refs:   
      if parents:
          s_model = models.name(learner=learner, parents=False, **others)
          #coop_f = coop_parents(ref, model, mult=0, noinit=True, efun=efun)
          solo_sf = solo_parents_and_selection(ref, model, s_model, mult=0, noinit=True, efun=efun)
          #coop_sf = coop_parents_and_selection(ref, model, s_model, mult=0, noinit=True, efun=efun)
          new.extend([#coop_f, 
                      solo_sf, 
                      #coop_sf
                      ])
      else: 
          solo_s = solo(ref, model, mult=0, noinit=True, efun=efun)
          #coop_s = coop(ref, model, mult=0, noinit=True, efun=efun)
          new.extend([solo_s, 
                      #coop_s
                      ])
      
   logger.debug(log.lst("- %d new strategies:"%len(new), new))
   return new

