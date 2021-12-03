import re, os
import logging
import lightgbm as lgb
from .learner import Learner
from pyprove import log
from .. import trains 

logger = logging.getLogger(__name__)

DEFAULTS = {
   'max_depth': 9, 
   'learning_rate': 0.2, 
   'objective': 'binary', 
   'num_round': 150,
   'num_leaves': 300,
   'min_data': 20,
   'max_bin': 255,
}

class LightGBM(Learner):

   def __init__(self, **args):
      self.params = dict(DEFAULTS)
      self.params.update(args)
      Learner.__init__(self, self.params["num_round"])

   def efun(self):
      return "EnigmaticLgb"

   def ext(self):
      return "lgb"

   def name(self):
      return "LightGBM"

   def desc(self):
      d = "lgb-t%(num_round)s-d%(max_depth)s-l%(num_leaves)s-e%(learning_rate).2f" % self.params
      if self.params["min_data"] != DEFAULTS["min_data"]:
         d += "-min%(min_data)d" % self.params
      if self.params["max_bin"] != DEFAULTS["max_bin"]:
         d += "-max%(max_bin)d" % self.params
      return d

   def __repr__(self):
      args = ["%s=%s"%(x,self.params[x]) for x in self.params]
      args = ", ".join(args)
      return "%s(%s)" % (self.name(), args)

   def readlog(self, f_log):
      if not os.path.isfile(f_log):
         return
      losses = re.findall(r'\[(\d*)\].*logloss: (\d*.\d*)', open(f_log).read())
      if not losses:
         self.stats["model.loss"] = "error"
         return
      losses = {int(x): float(y) for (x,y) in losses}
      last = max(losses)
      best = min(losses, key=lambda x: losses[x])
      self.stats["model.last.loss"] = [losses[last], last]
      self.stats["model.best.loss"] = [losses[best], best]

   def train(self, f_in, f_mod, init_model=None, handlers=None):
      (atstart, atiter, atfinish) = handlers if handlers else (None,None,None)
      (xs, ys) = trains.load(f_in)
      dtrain = lgb.Dataset(xs, label=ys, free_raw_data=(init_model is None))
      #dtrain.construct()
      pos = sum(ys)
      neg = len(ys) - pos
      self.stats["train.count"] = len(ys)
      self.stats["train.pos.count"] = int(pos)
      self.stats["train.neg.count"] = int(neg)
      self.params["scale_pos_weight"] = (neg/pos)
      #self.params["is_unbalance"] = True

      callbacks = [lambda _: atiter()] if atiter else None
      if atstart: atstart()
      #eta = self.params["learning_rate"]
      bst = lgb.train(self.params, dtrain, valid_sets=[dtrain], init_model=init_model, callbacks=callbacks) #, learning_rates=lambda iter: 0.1*(0.95**iter))
      if atfinish: atfinish()
      bst.save_model(f_mod)
      bst.free_dataset()
      bst.free_network()
      return bst

   def predict(self, f_in, f_mod):
      bst = lgb.Booster(model_file=f_mod)
      logger.debug("- loading training data %s" % f_in)
      (xs, ys) = trains.load(f_in)
      logger.debug("- predicting with lgb model %s" % f_mod)
      preds = bst.predict(xs, predict_disable_shape_check=True)
      return zip(preds, ys)

