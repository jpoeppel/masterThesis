#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 12 10:56:19 2015
Action model that separates actuators from simple objects.
All object changes can only be induced by actuators!

For now (12.8) assume, that object's static properties can only be changed directly
by actuators (no sliding etc after contact is broken)

Idea for multiple objects: For gate function: Start from actuator and only consider 
objects that are changed to have a potential influence on other objects.

@author: jpoeppel
"""

import numpy as np
from numpy import round as npround
#from sklearn import neighbors
from sklearn import svm
from sklearn.linear_model import Perceptron
from sklearn.linear_model import SGDClassifier
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.naive_bayes import MultinomialNB



import common
from common import NUMDEC
#from topoMaps import ITM
from network import Node
from itm import ITM
import copy

GREEDY_TARGET = True

HARDCODEDGATE = True
HARDCODEDACTUATOR = True

USE_DYNS = False

#mask = np.array([3,4,5,7,8,10,11])
mask = np.array([0,1,2,3,4,5,6,7,8,9,10,11,12])

class Object(object):
    
    def __init__(self):
        self.id = 0
        self.vec = np.array([])
        self.lastVec = np.array([])
        self.predVec= np.array([])
        
        
                
    def getRelVec(self, other):
        """
            Computes the relative (interaction) vector of the other object with respect
            to the own reference frame.
        """
        vec = np.zeros(13)
        vec[0] = self.id
        vec[1] = other.id
        if USE_DYNS:
            vec[2], vec[3] = common.computeDistanceClosing(self.id, self.vec[0:3],self.vec[4:7], 
                        self.vec[3], other.id, other.vec[0:3], other.vec[4:7], other.vec[3])
            vec[4:7], vec[7:10], vec[10:13] = common.relPosVel(self.vec[0:3], self.vec[4:7], self.vec[3], other.vec[0:3], other.vec[4:7])
        else:
            vec[2], vec[3] = common.computeDistanceClosing(self.id, self.vec[0:3],self.vec[0:3]-self.lastVec[0:3], 
                        self.vec[3], other.id, other.vec[0:3], other.vec[0:3]-other.lastVec[0:3], other.vec[3])
            vec[4:7], vec[7:10], vec[10:13] = common.relPosVel(self.vec[0:3], self.vec[0:3]-self.lastVec[0:3], self.vec[3], other.vec[0:3], other.vec[0:3]-other.lastVec[0:3])
        
#        vec[10] = np.dot(np.linalg.norm(vec[4:7]), np.linalg.norm(vec[7:10]))
        return vec
        
    def getGlobalPosVel(self, localPos, localVel):
        return common.globalPosVel(self.vec[0:3], self.vec[3], localPos, localVel)
                
                
    def getLocalChangeVec(self, post):
        res = np.copy(post.vec)
        res -= self.vec
        if USE_DYNS:
            res[0:3], res[4:7] = common.relPosVelChange(self.vec[3], res[0:3], res[4:7])
        else:
            res[0:3], v =  common.relPosVelChange(self.vec[3], res[0:3], np.zeros(3))
        return res

    def predict(self, predictor, other):
        resO = copy.deepcopy(self)
#        print "object before: ", resO.vec[1:4]
#        print "relVec: ", self.getRelVec(other)[4:7]
        pred = predictor.predict(self.getRelVec(other)[mask])
#        pred = predictor.test(self.getRelVec(other))
        if USE_DYNS:
            pred[0:3], pred[4:7] = common.globalPosVelChange(self.vec[3], pred[0:3], pred[4:7])
        else:
            pred[0:3], v = common.globalPosVelChange(self.vec[3], pred[0:3], np.zeros(3))
#        print "prediction for o: {}: {}".format(self.id, pred)
        self.predVec = self.vec + pred#*1.5 #interestingly enough, *1.5 improves prediction accuracy quite a lot
        resO.vec = np.round(self.predVec, common.NUMDEC)
        resO.lastVec = np.copy(self.vec)
#        print "resulting object: ", resO.vec[1:4]
        return resO
        
        
        
    def update(self, newO):
        self.lastVec = np.copy(self.vec)
        self.vec = np.copy(newO.vec)
        
    def circle(self, otherObject):
        """
            Function to return an action that would circle the other object around 
            itself.
            
            Parameters
            ----------
            otherObject: Object
            
            returns: np.ndarray
                Action vector for the actuator for the next step
        """
        
        relVec = self.getRelVec(otherObject)
        dist = relVec[2]
        relPos = otherObject.vec[0:3] - self.vec[0:3]
        relPos[2] = 0
        if dist < 0.03:
            return 0.5*relPos/np.linalg.norm(relPos)
        elif dist > 0.05:
            return -0.5*relPos/np.linalg.norm(relPos)
        else:
            tangent = np.array([-relPos[1], relPos[0], 0.0])
            return 0.5*tangent/np.linalg.norm(tangent)
        
        return np.array([0.0,0.0,0.0])
        
    def __repr__(self):
        return "{}".format(self.id)
        
    def getKeyPoints(self):
        WIDTH = {15: 0.25, 8: 0.025} #Width from the middle point
        DEPTH = {15: 0.05, 8: 0.025} #Height from the middle point
        p1x = WIDTH[self.id]
        p2x = -p1x
        p1y = DEPTH[self.id]
        p2y = -p1y
        ang = self.vec[3]
        c = np.cos(ang)
        s = np.sin(ang)
        p1xn = p1x*c -p1y*s + self.vec[1]
        p1yn = p1x*s + p1y*c + self.vec[2]
        p2xn = p2x*c - p2y*s + self.vec[1]
        p2yn = p2x*s + p2y*c + self.vec[2]
        return np.array([np.copy(self.vec[0:3]), np.array([p1xn,p1yn,self.vec[2]]), np.array([p2xn,p2yn,self.vec[2]])])
        
    def compare(self, other):
        assert self.id == other.id, "Should only compare the same objects not {} and {}".format(self.id, othe.id)
        sKeyPoints = self.getKeyPoints()
        oKeyPoints = other.getKeyPoints()
        return sum(np.linalg.norm(sKeyPoints-oKeyPoints,axis=1))/3.0
        
    @classmethod
    def parse(cls, m):
        res = cls()
        res.id = m.id 
        if USE_DYNS:
            res.vec = np.zeros(7)
#            res.vec[0] = m.id
            res.vec[0] = npround(m.pose.position.x, NUMDEC) #posX
            res.vec[1] = npround(m.pose.position.y, NUMDEC) #posY
            res.vec[2] = npround(m.pose.position.z, 2) #posZ
            res.vec[3] = npround(common.quaternionToEuler(np.array([m.pose.orientation.x,m.pose.orientation.y,
                                                m.pose.orientation.z,m.pose.orientation.w])), NUMDEC)[2] #ori
            res.vec[4] = npround(m.linVel.x, NUMDEC) #linVelX
            res.vec[5] = npround(m.linVel.y, NUMDEC) #linVelY
            res.vec[6] = 0.0 #linVelZ
        
#            res.vec[8] = npround(m.angVel.z, NUMDEC) #angVel
        else:
            res.vec = np.zeros(4)
#            res.vec[0] = m.id
            res.vec[0] = npround(m.pose.position.x, NUMDEC) #posX
            res.vec[1] = npround(m.pose.position.y, NUMDEC) #posY
            res.vec[2] = npround(m.pose.position.z, 2) #posZ
            res.vec[3] = npround(common.quaternionToEuler(np.array([m.pose.orientation.x,m.pose.orientation.y,
                                                m.pose.orientation.z,m.pose.orientation.w])), NUMDEC)[2] #ori
        res.lastVec = np.copy(res.vec)
        return res

class Actuator(Object):
    
    def __init__(self):
        Object.__init__(self)
        self.predictor = ITM()
        if USE_DYNS:
            self.vec = np.zeros(9)
        else:
            self.vec = np.zeros(5)
        pass
    
    def predict(self, action):
#        res = copy.deepcopy(self)
        res = Actuator()
        res.id = self.id
        self.predVec = np.copy(self.vec)
#        res.vec[5:8] = action #Set velocity
        if USE_DYNS:
            self.predVec[4:7] = action
        else:
            pass
        #Hardcorded version
        if HARDCODEDACTUATOR:
#            res.vec[1:4] += 0.01*action
            self.predVec[0:3] += 0.01*action
        else:
            #Only predict position
            p = self.predictor.predict(action)
            self.predVec[0:3] += p
#            res.vec[1:4] += p
        res.lastVec = np.copy(self.vec)
        res.vec = np.round(self.predVec, common.NUMDEC)
        return res
            
    def update(self, newAc, action, training = True):
        self.lastVec = self.vec
#        self.predictor = newAc.predictor
        if training:
            if HARDCODEDACTUATOR:
                pass
            else:
                pdif = newAc.vec[0:3]-self.vec[0:3]
#                self.predictor.train(Node(0, wIn=action, wOut=pdif))
                self.predictor.update(action, pdif, etaOut=0.0)
        self.vec = np.copy(newAc.vec)
        
    @classmethod
    def parse(cls, protoModel):
        res = super(Actuator, cls).parse(protoModel)
#        res.vec[8] = 0.0 #Fix angular velocity
        return res
    
class WorldState(object):
    
    def __init__(self):
        self.actuator = Actuator()
        self.objectStates = {}
        
    def parseModels(self, models):
        for m in models:
            if m.name == "ground_plane" or "wall" in m.name or "Shadow" in m.name:
                continue
            else:
                if m.name == "gripper":
                    ac = Actuator.parse(m)
                    self.actuator = ac
                else:
                    tmp = Object.parse(m)               
                    self.objectStates[tmp.id] = tmp
        
    def parse(self, gzWS):
        self.parseModels(gzWS.model_v.models)                
    
class Classifier(object):
    
    def __init__(self):
#        self.clas = neighbors.KNeighborsClassifier(n_neighbors=2, weights='uniform')
#        self.clas = svm.SVC()
#        self.clas = Perceptron()
#        self.clas = SGDClassifier()
#        self.clas = PassiveAggressiveClassifier()
        self.clas = ITM()
        self.isTrained = False
#        self.inputs = []
#        self.targets = []
        
    def train(self, o1vec, avec, label):
        if HARDCODEDGATE:
            pass
        else:
#            self.inputs.append(np.concatenate((o1vec,avec)))
#            self.targets.append(label)
#            if max(self.targets) > 0:
#            self.clas.partial_fit(np.concatenate((o1vec,avec)), np.array([label]), np.array([0,1]))
#            self.clas.partial_fit(o1vec[[2,3,7,8,9]], np.array([label]), np.array([0,1])) #Test to ignore action, since it is applied to object2 calculating ovec
            self.clas.update(o1vec[[2,3,7,8,9]], np.array([label]))
            self.isTrained = True
    
    def test(self, ovec, avec):
#        print "closing: {}, dist: {}".format(ovec[3], ovec[2])
        if HARDCODEDGATE:
            if ovec[3] <= -100*ovec[2]:
#                print "Change: closing: {}, dist: {}, relVel: {}".format(ovec[3], ovec[2], ovec[7:10])
                return 1
            else:
                if ovec[3] == 0 and np.linalg.norm(ovec[7:10]) < 0.001 and ovec[2] < 0.05: #Todo remove distance from this
#                    print "Change: closing: {}, dist: {}, relVel: {}".format(ovec[3], ovec[2], ovec[7:10])
                    return 1    
                else:
#                    print "no Change: closing: {}, dist: {}, relVel: {}".format(ovec[3], ovec[2], ovec[7:10])
                    return 0
        else:
#            if len(self.targets) > 0 and max(self.targets) > 0:
            if self.isTrained:
#                return self.clas.predict(np.concatenate((ovec,avec)))[0]
#                return self.clas.predict(ovec[[2,3,7,8,9]])[0] #Same as above in training
                pred = self.clas.test(ovec[[2,3,7,8,9]], testMode=0)
                return pred
            else:
                return 0
    
    
class GateFunction(object):
    
    def __init__(self):
        self.classifier = Classifier()
        
        pass
    
    def test(self, o1, o2, action):
        vec = o1.getRelVec(o2)
        return self.classifier.test(vec,action)
        
    def checkChange(self, pre, post):
        dif = pre.getLocalChangeVec(post)
        if np.linalg.norm(dif[0:3]) > 0.0 or abs(dif[3]) > 0.0:
            return True, dif
        return False, dif
        
        
    def update(self, o1Pre, o1Post, o2Pre, action):
        """
        Parameters
        ----------
        o1Pre: Object
        o1Post: Object
        o2Pre: Object #CURRENTLY o2POST!!!! TODO
        action: np.ndarray
        """
        #TODO Causal determination, make hypothesis and test these!
        
        vec = o1Pre.getRelVec(o2Pre)
        hasChanged, dif = self.checkChange(o1Pre, o1Post)
        if hasChanged:
            self.classifier.train(vec,action, 1)
            return True, dif
        else:
            self.classifier.train(vec,action, 0)
            return False, dif

class MetaNode(object):

    def __init__(self):
        self.weights = 0.0
        self.preSum = None
        self.absMask = None
        self.negWeights = 0.0
        self.posWeights = 0.0
        self.zeroPass = None
        self.posSum = None
        self.negSum = None
        self.prev = None
        self.signCombinations= {}
        pass

    def train(self, pre, dif):
        """
        Parameters
        ----------
        pre : np.ndarray
            Vector of preconditions
        dif : float
            Absolut difference value of the feature
        """
        #Compare incoming pres and find the things they have in common/are relevant for a given dif
        lPre = len(pre)
        if self.zeroPass == None:
            self.zeroPass = [False]*lPre
            self.posSum = np.zeros(lPre)
            self.negSum = np.zeros(lPre)
            self.posWeights = np.zeros(lPre)
            self.negWeights = np.zeros(lPre)
            self.prev = np.zeros(lPre)
        curSigCom = ";".join("{}".format(n) for n in np.sign(pre[[4,5,10,11]]))
        for i in xrange(lPre):
#            curSigCom += str(np.sign(pre[i]))
            
            if not self.zeroPass[i]:
                if USE_DYNS:
                    if abs(pre[1]) < 0.01:
                        self.zeroPass[i] = True
                else:
                    if abs(pre[i]) < 0.001:
                        self.zeroPass[i] = True
            if pre[i] < 0:
                self.negSum[i] += dif*pre[i]
                self.negWeights[i] += dif
            elif pre[i] > 0:
                self.posSum[i] += dif*pre[i]
                self.posWeights[i] += dif
            else:
                self.negSum[i] += dif*pre[i]
                self.posSum[i] += dif*pre[i]
                self.negWeights[i] += dif
                self.posWeights[i] += dif
                
            if self.posWeights[i] == self.negWeights[i]:
                self.prev[i] = np.sign(pre[i])
        print "pos weights: ", self.posWeights[[4,5,10,11]]
        print "neg weights: ", self.negWeights[[4,5,10,11]]
        if curSigCom in self.signCombinations:
            self.signCombinations[curSigCom] += 1
        else:
            self.signCombinations[curSigCom] = 1
                    
        
    def getPreconditions(self):
        res = np.zeros(len(self.zeroPass))
        res2 = np.zeros(len(self.zeroPass))
        res2valid = False
        print "signCombinations: ", self.signCombinations
        for i in xrange(len(self.zeroPass)):
            if i in [4,5,10,11]:
                print "i: {}, posSum: {}, negSum: {}, posW: {}, negW: {} zero: {}".format(i, self.posSum[i], self.negSum[i], self.posWeights[i], self.negWeights[i], self.zeroPass[i])
            if self.zeroPass[i]:
                res[i] = (self.posSum[i]+self.negSum[i])/(self.posWeights[i]+self.negWeights[i])
                res2[i] =(self.posSum[i]+self.negSum[i])/(self.posWeights[i]+self.negWeights[i])
            else:
#                print "index: {}, pos weights: {}, neg weights: {}".format(i, self.posWeights[i], self.negWeights[i])
                if self.posWeights[i] > self.negWeights[i]:
                    res[i] = self.posSum[i]/self.posWeights[i]
                    if self.negWeights[i] > 0.2:
                        res2[i] = self.negSum[i]/self.negWeights[i]
                        res2valid = True
                    else:
                        res2[i] = self.posSum[i]/self.posWeights[i]
                elif self.posWeights[i] == self.negWeights[i]:
                    res2valid = True
                    if self.prev[i] < 0:
                        res[i] = self.negSum[i]/self.negWeights[i]
                        res2[i] = self.posSum[i]/self.posWeights[i]
                    else:
                        res[i] = self.posSum[i]/self.posWeights[i]
                        res2[i] = self.negSum[i]/self.negWeights[i]
                else:
                    res[i] = self.negSum[i]/self.negWeights[i]
                    if self.posWeights[i] > 0.2:
                        res2[i] = self.posSum[i]/self.posWeights[i]
                        res2valid =True
                    else:
                        res2[i] = self.negSum[i]/self.negWeights[i]
        if res2valid:
            return res, res2
        else:
            return res, None
            
class MetaNetwork(object):
    
    def __init__(self):
        self.nodes = {}
        self.curIndex = None
        self.curSecIndex = None
        self.preConsSize = None
        self.difSize = None
        pass
    
    def train(self, pre, difs):
        if self.preConsSize == None:
            self.preConsSize = len(pre)
        if self.difSize == None:
            self.difSize = len(difs)
#        print "difs: ", difs
#        print "training network with pre: ", pre
        for i in xrange(len(difs)):
            #It appears smaller values break inverse model since the weights can 
            #get swapped for point symmetric preconditions
            if abs(difs[i]) > 0.002: 
                index = str(i*np.sign(difs[i]))
                if not index in self.nodes:
                    self.nodes[index] = MetaNode()
                print "training index: {} with dif: {}".format(index, difs[i])
                print "precons: ",pre[[4,5,10,11]]
                self.nodes[index].train(pre,abs(difs[i]))
                
    def tobeNamed(self):
        """
            Function that tries to find preconditions that might increase its knowledge
            about the obejct interaction.
        """
        curKeys = self.nodes.keys()
        for i in xrange(self.difSize):
            if i in curKeys and not -i in curKeys:
                return self.nodes[i].getPreconditions()
            if -i in curKeys and not i in curKeys:
                return self.nodes[-i].getPreconditions()
                
                
    def getPreconditions(self, targetDifs):
        res = self.preConsSize
        norm = 0.0
        if GREEDY_TARGET:
            if self.curIndex != None:
                ind = float(self.curIndex)
                #Consider making this a ratio of maximum/total difs so that it avoids jumping back and forth when it is already quite close to target
                if np.sign(ind) == np.sign(targetDifs[abs(ind)]) and abs(targetDifs[abs(ind)]) > 0.02: 
                    print "working on curIndex: ", self.curIndex
                    preCons1, preCons2 = self.nodes[self.curIndex].getPreconditions()
                else:
                    self.curIndex = None
                    
            
            if self.curIndex == None:
                sortedDifs = np.argsort(abs(targetDifs))                
                maxDif = sortedDifs[-1]
                index = str(maxDif*np.sign(targetDifs[maxDif]))
                self.curSecIndex =str(sortedDifs[-2]*np.sign(targetDifs[sortedDifs[-2]]))
                print "targetDifs: ", targetDifs
                print "maxindex: ", index
                if not index in self.nodes:
                    print "index i {} for targetDif {}, not known".format(index, targetDifs[i])
                    print "nodes: ", self.nodes.keys()
                    print "targetDifs: ", targetDifs
                else:
                    self.curIndex = index
                    print "precons for index: ", index
                    preCons1, preCons2 = self.nodes[index].getPreconditions()
                    
            if preCons2 == None:
                print "no alternative"
                return preCons1
            else:
                index2 = self.curSecIndex
                if not index2 in self.nodes:
                    print "using pre1"
                    return preCons1
                else:
                    print "precons for index: ", index2
                    secCons1, secCons2 = self.nodes[index2].getPreconditions()
                    o1 = np.linalg.norm(secCons1-preCons1)
                    o2 = np.linalg.norm(secCons1-preCons2)
#                    print "dist1: ", o1
#                    print "dist2: ", o2
#                    print "preCons1: ", preCons1
#                    print "preCons2: ", preCons2
#                    print "secCons1: ", secCons1
                    if secCons2 == None:
                        if o1 <= o2:
                            print "using pre1"
                            return preCons1
                        else:
                            print "using pre2"
                            return preCons2
                    else:
                        o3 = np.linalg.norm(secCons2-preCons1)
                        o4 = np.linalg.norm(secCons2-preCons2)
                        if min(o1,o3) < min(o2,o4):
                            print "using pre1"
                            return preCons1
                        else:
                            print "using pre2"
                            return preCons2
                

        else:
            for i in xrange(len(targetDifs)):
              if abs(targetDifs[i]) > 0.001:
                  index = i*np.sign(targetDifs[i])
                  if not index in self.nodes:
                      print "index i {} for targetDif {}, not known".format(index, targetDifs[i])
                      print "nodes: ", self.nodes.keys()
                      print "targetDifs: ", targetDifs
                  else:
                      res += abs(targetDifs[i])*self.nodes[index].getPreconditions()
                      norm += abs(targetDifs[i])
            if norm > 0:    
                return res/norm
            else:
                return res
        
            
class Predictor(object):
    
    def __init__(self):
        self.predictors = {}
        self.inverseModel = {}
    
    def predict(self, o1, o2, action):
        if o1.id in self.predictors:
            return o1.predict(self.predictors[o1.id], o2)
        else:
            return o1
            
    def getAction(self,targetId, dif):
        if targetId in self.inverseModel:
            return self.inverseModel[targetId].getPreconditions(dif)
        else:
            print "target not found"
            return None
    
    def update(self, intState, action, dif):
        if not intState[0] in self.predictors:
            #TODO check for close ones that can be used
            self.predictors[intState[0]] = ITM()
            self.inverseModel[intState[0]] = MetaNetwork()
#        with open("../../trainDataPush20.txt", "a") as f:
#            f.write(";".join(["{:.4f}".format(x) for x in np.concatenate((intState, dif))]))
#            f.write("\n")
#        self.predictors[intState[0]].train(Node(0, wIn = intState[mask], wOut=dif))
        self.predictors[intState[0]].update(intState[mask], dif, etaIn=0.1)
        self.inverseModel[intState[0]].train(intState, dif)


class ModelGate(object):
    
    def __init__(self):
        self.gate = GateFunction()
        self.actuator = None
        self.predictor = Predictor()
        self.curObjects = {}
        self.target = None
        self.training = True #Determines if the model should be trained on updates or
                            # just update it's objects features
        
        
    def setTarget(self, target):
        """
            Sets a target that is to be reached.
            Target is an object (maybe partially described)
            Parameters
            ----------
            target : Object
        """
        self.target = target
        
    def isTargetReached(self):
        targetO = self.curObjects[self.target.id]
        difVec = targetO.vec[:4]-self.target.vec[:4]
        norm = np.linalg.norm(difVec)
        print "dif norm: ", norm
        if norm < 0.01:
            return True
        return False
        
    def explore(self):
        """
            Returns an action in order to increase the knowledge of the model.
            
            Returns: np.ndarray
                Action vector for the actuator
        """
        
        pass
        
        
    def getAction(self):
        """
            Returns an action, that is to be performed, trying to get closer to the
            target if one is set.
            
            Returns: np.ndarray
                Action vector for the actuator
        """
        if self.target is None:
            return np.array([0.0,0.0,0.0])
        else:
            if self.isTargetReached():
                print "target reached"
                return np.array([0.0,0.0,0.0])
            else:
                targetO = self.curObjects[self.target.id]
                # Determine difference vector, the object should follow
#                print "global dif vec: ", self.target.vec-targetO.vec
                difVec = targetO.getLocalChangeVec(self.target)
#                print "difVec: ", difVec[:5]
                pre = self.predictor.getAction(self.target.id, difVec[:4])
                relTargetPos = pre[4:7]
                print "rel target pos: ", relTargetPos
                relTargetVel = pre[10:13]
                print "relTargetVel: ", relTargetVel
                
                pos, vel = targetO.getGlobalPosVel(relTargetPos, relTargetVel)
                print "target vel: ", vel
                print "target pos: ", pos
                print "cur pos: ", self.actuator.vec[0:3]
                difPos = pos-self.actuator.vec[0:3]
#                print "difpos norm: ", np.linalg.norm(difPos)
                relVec = targetO.getRelVec(self.actuator)
                relPos = relVec[4:7]
                # Determine Actuator position that allows action in good direction
                wrongSides = relPos*relTargetPos < 0
                if np.any(wrongSides):
                    if max(abs(relTargetPos[wrongSides]-relPos[wrongSides])) > 0.05:
                     # Bring actuator into position so that it influences targetobject
                        print "try circlying"
                        return targetO.circle(self.actuator)
                        
                if np.linalg.norm(difPos) > 0.02:
                    action = 0.5*difPos/np.linalg.norm(difPos)
                    tmpAc = self.actuator.predict(action)
                    if not self.gate.test(targetO, tmpAc, action):
                        print "doing difpos"
                        return action
                    else:
                        print "circlying since can't do difpos"
                        return targetO.circle(self.actuator)
#                else:
                print "using vel"
                normVel = np.linalg.norm(vel)
                if normVel == 0.0 or (normVel > 0.01 and normVel < 0.2):
                    return vel
                else:
                    return 0.3*vel/normVel
#                

#                #TODO!
#                # Work in open loop: Compare result of previous action with expected result
#                pass
            
        pass
    
    def predict(self, ws, action):
        #TODO Remove ws from here since it is not needed at all    
        newWS = WorldState()
        newWS.actuator = self.actuator.predict(action)
        for o in self.curObjects.values():
            if self.gate.test(o, newWS.actuator, action):
                newO = self.predictor.predict(o, newWS.actuator, action)
                newWS.objectStates[o.id] = newO
                
            else:
                o.vec[4:] = 0.0
                newWS.objectStates[o.id] = o
        return newWS
        
        
    def resetObjects(self, curWS):
        for o in curWS.objectStates.values():
            if o.id in self.curObjects:
                self.curObjects[o.id].update(o)
            else:
                self.curObjects[o.id] = o
                
        if self.actuator == None:
            self.actuator = curWS.actuator
        self.actuator.update(curWS.actuator, np.array([0.0,0.0,0.0]))
        
    def update(self, curWS, action):
        
        for o in curWS.objectStates.values():
            #TODO extent to more objects
            if o.id in self.curObjects:
#                hasChanged, dif = self.gate.update(self.curObjects[o.id], o, self.actuator, action)
                if self.training:
                    hasChanged, dif = self.gate.update(self.curObjects[o.id], o, curWS.actuator, action)
                    if hasChanged:
                        self.predictor.update(self.curObjects[o.id].getRelVec(self.actuator), action, dif)
                self.curObjects[o.id].update(curWS.objectStates[o.id])
            else:
                self.curObjects[o.id] = o
                
        if self.actuator == None:
            self.actuator = curWS.actuator
        self.actuator.update(curWS.actuator, action, self.training)
            
    