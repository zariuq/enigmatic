from multiprocessing import Pool, Manager
from progress.bar import FillingSquaresBar as Bar
import subprocess
from pyprove import expres, eprover
import os
import traceback
import re

pat1 = re.compile("parent1 (cnf.*\)\.) #")
pat2 = re.compile("parent2 (cnf.*\)\.) #")

def extract_parents(result):
    parents = []
    for clause in result:
        tmp = clause[:clause.index('#')]
        parent1 = pat1.search(clause)
        if parent1:
            parents.append(parent1.group(1))
        else:
            parents.append(tmp)
        parent2 = pat2.search(clause)
        if parent2:
            parents.append(parent2.group(1))
        else:
            parents.append(tmp)
    return parents

def proofstate(f_dat, f_pos, f_neg, hashing=None):
   offset = 3 * hashing if hashing else 0
   def parse(clause):
      vector_end = clause.rindex("processedvector") - 1 if "processedvector" in clause else -1
      clause = clause[clause.rindex("proofvector")+12:vector_end].rstrip(",\n").strip().split(",")
      clause = [x.split("(")[0].split(":") for x in clause if x]
      if not hashing:
         clause = ["$%s/%s"%tuple(x) for x in clause if x]
      else:
         clause = [(offset + int(x[0]), x[1]) for x in clause if x]
         clause = ["%s:%s"%tuple(x) for x in clause if x]
      return " ".join(clause)
   dat = open(f_dat).read().strip().split("\n")
   dat = [x for x in dat if x]
   i = 0
   for pos in open(f_pos):
      dat[i] += " "+parse(pos)
      i += 1
   for neg in open(f_neg):
      dat[i] += " "+parse(neg)
      i += 1
   if i != len(dat):
      raise Exception("File %s does not match files %s and %s!" % (f_dat,f_pos,f_neg))
   open(f_dat, "w").write("\n".join(dat))

def processsedstate(f_dat, f_pos, f_neg, hashing=None):
   offset = 2 * hashing if hashing else 0
   def parse(clause):
      if "processedvector" in clause:
          clause = clause[clause.rindex("processedvector")+15:].rstrip(",\n").strip().split(",")
          clause = [x.split(":") for x in clause if x]
          if not hashing:
             clause = ["&%s/%s"%tuple(x) for x in clause if x] # I hope this & isn't used elsewhere...
          else:

             clause = [(offset + int(x[0]), x[1]) for x in clause if x]
             clause = ["%s:%s"%tuple(x) for x in clause if x]
          return " " + " ".join(clause)
      else:
          return ""
   dat = open(f_dat).read().strip().split("\n")
   dat = [x for x in dat if x]
   i = 0
   for pos in open(f_pos):
      dat[i] += parse(pos)
      i += 1
   for neg in open(f_neg):
      dat[i] += parse(neg)
      i += 1
   if i != len(dat):
      raise Exception("File %s does not match files %s and %s!" % (f_dat,f_pos,f_neg))
   open(f_dat, "w").write("\n".join(dat))

def prepare2(job):
   queue = job[7]
   try:
      prepare1(job)
   except:
      print("Error: "+traceback.format_exc())
   queue.put(job[2])

def prepare1(job):
   (bid,pid,problem,limit,version,force,hashing,queue) = job


   result = None
   #result = rkeys[(bid,pid,problem,limit)]
   f_pos = expres.results.path(bid, pid, problem, limit, ext="pos")
   f_neg = expres.results.path(bid, pid, problem, limit, ext="neg")
   if force or (not (os.path.isfile(f_pos) and os.path.isfile(f_neg))):
      f_ppos = expres.results.path(bid, pid, problem, limit, ext="ppos")
      f_pneg = expres.results.path(bid, pid, problem, limit, ext="pneg")
      os.system("mkdir -p %s" % os.path.dirname(f_pos))
      #os.system("mkdir -p %s" % os.path.dirname(f_neg)) # In our case, they're always the same
      result = expres.results.load(bid, pid, problem, limit, trains=True, proof=True)
      pos_parents = extract_parents(result["POS"])
      neg_parents = extract_parents(result["NEG"])
      if force or not os.path.isfile(f_pos):
         open(f_pos, "w").write("\n".join(result["POS"]))
      if force or not os.path.isfile(f_neg):
         open(f_neg, "w").write("\n".join(result["NEG"]))
      if force or not os.path.isfile(f_ppos):
         open(f_ppos, "w").write("\n".join(pos_parents))
      if force or not os.path.isfile(f_pneg):
         open(f_pneg, "w").write("\n".join(neg_parents))
      # extract additional positive samples from the proof
      #f_sol = expres.results.path(bid, pid, problem, limit, ext="sol")
      #open(f_sol, "w").write("\n".join(result["PROOF"]))
      #f_prf = expres.results.path(bid, pid, problem, limit, ext="prf")
      #prf = open(f_prf, "w")
      #subprocess.call(["eprover", "--free-numbers", "--cnf", f_sol], stdout=prf)
      ##subprocess.call(["eprover", "--free-numbers", "--cnf", "--no-preprocessing", f_sol], stdout=prf)
      #prf.close()
      #os.system("cat %s | grep '^cnf' >> %s" % (f_prf, f_pos))

   f_dat = expres.results.path(bid, pid, problem, limit, ext="in" if hashing else "pre")
   if force or not os.path.isfile(f_dat):
      f_cnf = expres.benchmarks.path(os.path.join(bid,"cnf"), problem)
      if not os.path.isfile(f_cnf):
        f_problem = expres.benchmarks.path(bid, problem)
        open(f_cnf, "wb").write(eprover.runner.cnf(f_problem))

      f_map = expres.results.path(bid, pid, problem, limit, ext="map")

      #os.system("mkdir -p %s" % os.path.dirname(f_dat)) # Again, always the same as .pos/.neg, so currently unnecessary system calls
      #os.system("mkdir -p %s" % os.path.dirname(f_map))
      out = open(f_dat, "w")
      if not hashing:
         subprocess.call(["enigma-features", "--free-numbers", "--enigma-features=%s"%version, \
            f_pos, f_neg, f_cnf], stdout=out)
            #stdout=out, stderr=subprocess.STDOUT)
      else:
         subprocess.call(["enigma-features", "--free-numbers", "--enigma-features=%s"%version, \
            "--feature-hashing=%s"%hashing, "--enigmap-file=%s"%f_map, f_pos, f_neg, f_cnf], stdout=out)

      out.close()
      if "W" in version:
         proofstate(f_dat, f_pos, f_neg, hashing)
      if "p" in version: # TODO: make proofstate and processedstate compatible with each other
         processsedstate(f_dat, f_pos, f_neg, hashing)

def prepare(rkeys, version, force=False, cores=1, hashing=None):
   pool = Pool(cores)
   m = Manager()
   queue = m.Queue()
   jobs = [rkey+(version,force,hashing,queue) for rkey in rkeys]
   bar = Bar("[1/3]", max=len(jobs), suffix="%(percent).1f%% / %(elapsed_td)s / ETA %(eta_td)s")
   bar.start()
   res = pool.map_async(prepare2, jobs, chunksize=1)
   todo = len(jobs)
   while todo:
      queue.get()
      todo -= 1
      bar.next()
   bar.finish()
   pool.close()
   pool.join()

def translate(f_cnf, f_conj, f_out):
   "deprecated?"

   out = open(f_out, "w")
   if not f_conj:
      subprocess.call(["enigma-features", "--free-numbers", f_cnf], stdout=out)
   else:
      f_empty = "empty.tmp"
      os.system("rm -fr %s" % f_empty)
      os.system("touch %s" % f_empty)
      subprocess.call(["enigma-features", "--free-numbers", f_cnf, f_empty, f_conj], \
         stdout=out)
         #stdout=out, stderr=subprocess.STDOUT)
      os.system("rm -fr %s" % f_empty)
   out.close()

def make(rkeys, out=None, hashing=None):
   dat = []
   bar = Bar("[2/3]", max=len(rkeys), suffix="%(percent).1f%% / %(elapsed_td)s / ETA %(eta_td)s")
   bar.start()
   for (bid, pid, problem, limit) in rkeys:
      f_dat = expres.results.path(bid, pid, problem, limit, ext="in" if hashing else "pre")
      if out:
         tmp = open(f_dat).read().strip()
         if tmp:
            out.write(tmp)
            out.write("\n")
      else:
         dat.extend(open(f_dat).read().strip().split("\n"))
      bar.next()
   bar.finish()
   return dat if not out else None
