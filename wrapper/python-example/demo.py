#!/usr/bin/python
import sys
import numpy as np
import scipy.sparse
# append the path to xgboost, you may need to change the following line
# alternatively, you can add the path to PYTHONPATH environment variable
sys.path.append('../')
import xgboost as xgb

### simple example
# load file from text file, also binary buffer generated by xgboost
dtrain = xgb.DMatrix('agaricus.txt.train')
dtest = xgb.DMatrix('agaricus.txt.test')

# specify parameters via map, definition are same as c++ version
param = {'bst:max_depth':2, 'bst:eta':1, 'silent':1, 'objective':'binary:logistic' }

# specify validations set to watch performance
evallist  = [(dtest,'eval'), (dtrain,'train')]
num_round = 2
bst = xgb.train(param, dtrain, num_round, evallist)

# this is prediction
preds = bst.predict(dtest)
labels = dtest.get_label()
print ('error=%f' % (  sum(1 for i in range(len(preds)) if int(preds[i]>0.5)!=labels[i]) /float(len(preds))))
bst.save_model('0001.model')
# dump model
bst.dump_model('dump.raw.txt')
# dump model with feature map
bst.dump_model('dump.nice.txt','featmap.txt')

# save dmatrix into binary buffer
dtest.save_binary('dtest.buffer')
bst.save_model('xgb.model')
# load model and data in 
bst2 = xgb.Booster(model_file='xgb.model')
dtest2 = xgb.DMatrix('dtest.buffer')
preds2 = bst2.predict(dtest2)
# assert they are the same
assert np.sum(np.abs(preds2-preds)) == 0

###
# build dmatrix from scipy.sparse
print ('start running example of build DMatrix from scipy.sparse')
labels = []
row = []; col = []; dat = []
i = 0
for l in open('agaricus.txt.train'):
    arr = l.split()
    labels.append( int(arr[0]))
    for it in arr[1:]:
        k,v = it.split(':')
        row.append(i); col.append(int(k)); dat.append(float(v))
    i += 1
csr = scipy.sparse.csr_matrix( (dat, (row,col)) )
dtrain = xgb.DMatrix( csr )
dtrain.set_label(labels)
evallist  = [(dtest,'eval'), (dtrain,'train')]
bst = xgb.train( param, dtrain, num_round, evallist )

print ('start running example of build DMatrix from numpy array')
# NOTE: npymat is numpy array, we will convert it into scipy.sparse.csr_matrix in internal implementation,then convert to DMatrix
npymat = csr.todense()
dtrain = xgb.DMatrix( npymat)
dtrain.set_label(labels)
evallist  = [(dtest,'eval'), (dtrain,'train')]
bst = xgb.train( param, dtrain, num_round, evallist )

###
# advanced: cutomsized loss function
# 
print ('start running example to used cutomized objective function')

# note: for customized objective function, we leave objective as default
# note: what we are getting is margin value in prediction
# you must know what you are doing
param = {'bst:max_depth':2, 'bst:eta':1, 'silent':1 }

# user define objective function, given prediction, return gradient and second order gradient
# this is loglikelihood loss
def logregobj(preds, dtrain):
    labels = dtrain.get_label()
    preds = 1.0 / (1.0 + np.exp(-preds))
    grad = preds - labels
    hess = preds * (1.0-preds)
    return grad, hess

# user defined evaluation function, return a pair metric_name, result
# NOTE: when you do customized loss function, the default prediction value is margin
# this may make buildin evalution metric not function properly
# for example, we are doing logistic loss, the prediction is score before logistic transformation
# the buildin evaluation error assumes input is after logistic transformation
# Take this in mind when you use the customization, and maybe you need write customized evaluation function
def evalerror(preds, dtrain):
    labels = dtrain.get_label()
    # return a pair metric_name, result
    # since preds are margin(before logistic transformation, cutoff at 0)
    return 'error', float(sum(labels != (preds > 0.0))) / len(labels)

# training with customized objective, we can also do step by step training
# simply look at xgboost.py's implementation of train
bst = xgb.train(param, dtrain, num_round, evallist, logregobj, evalerror)

###
# advanced: start from a initial base prediction
#
print ('start running example to start from a initial prediction')
# specify parameters via map, definition are same as c++ version
param = {'bst:max_depth':2, 'bst:eta':1, 'silent':1, 'objective':'binary:logistic' }
# train xgboost for 1 round
bst = xgb.train( param, dtrain, 1, evallist )
# Note: we need the margin value instead of transformed prediction in set_base_margin
# do predict with output_margin=True, will always give you margin values before logistic transformation
ptrain = bst.predict(dtrain, output_margin=True)
ptest  = bst.predict(dtest, output_margin=True)
dtrain.set_base_margin(ptrain)
dtest.set_base_margin(ptest)

print ('this is result of running from initial prediction')
bst = xgb.train( param, dtrain, 1, evallist )