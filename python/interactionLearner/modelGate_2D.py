#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 15 12:27:54 2015

Reworked gate model to only use 2D

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


import common
#from topoMaps import ITM
from network import Node
from itm import ITM
import copy

from operator import itemgetter

NUMDEC = common.config.NUMDEC
USE_DYNS = common.config.USE_DYNS

GREEDY_TARGET = True

HARDCODEDGATE = True
HARDCODEDACTUATOR = True

#mask = np.array([3,4,5,7,8,10,11])
mask = np.array([0,1,2,3,4,5,6,7,8,9])

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
        vec = np.zeros(10)
        vec[0] = self.id
        vec[1] = other.id
        if USE_DYNS:
            vec[2], vec[3] = common.computeDistanceClosing(self.id, self.vec[0:2],self.vec[3:5], 
                        self.vec[2], other.id, other.vec[0:2], other.vec[3:5], other.vec[2])
            vec[4:6], vec[6:8], vec[8:10] = common.relPosVel(self.vec[0:3], self.vec[4:7], self.vec[3], other.vec[0:3], other.vec[4:7])
        else:
            vec[2], vec[3] = common.computeDistanceClosing(self.id, self.vec[0:2],self.vec[0:2]-self.lastVec[0:2], 
                        self.vec[2], other.id, other.vec[0:2], other.vec[0:2]-other.lastVec[0:2], other.vec[2])
            vec[4:6], vec[6:8], vec[8:10] = common.relPosVel(self.vec[0:2], self.vec[0:2]-self.lastVec[0:2], self.vec[2], other.vec[0:2], other.vec[0:2]-other.lastVec[0:2])
        
#        vec[10] = np.dot(np.linalg.norm(vec[4:7]), np.linalg.norm(vec[7:10]))
#        if vec[6] != -0.02:
#            raise NotImplementedError(vec)
#        print "relVel: ", vec[10:13]
        
        return vec
        
    def getRelObjectVec(self, other):
        vec = np.zeros(len(self.vec))
        vec[0:2] = common.relPos(self.vec[0:2], self.vec[2], other.vec[0:2])
        vec[2] = other.vec[2]-self.vec[2]
        return vec
        
    def getGlobalPosVel(self, localPos, localVel):
        return common.globalPosVel(self.vec[0:2], self.vec[2], localPos, localVel)
                
    def getLocalChangeVec(self, post):
        res = np.copy(post.vec)
        res -= self.vec
        if USE_DYNS:
            res[0:2], res[3:5] = common.relPosVelChange(self.vec[2], res[0:2], res[3:5])
        else:
            res[0:2], v =  common.relPosVelChange(self.vec[2], res[0:2], np.zeros(2))
        return res

    def predict(self, predictor, other):
        resO = copy.deepcopy(self)
#        print "object before: ", resO.vec[1:4]
#        print "relVec: ", self.getRelVec(other)[4:7]
        print "using itm for object prediction"
        pred = predictor.test(self.getRelVec(other)[mask])
#        pred = predictor.test(self.getRelVec(other))
        if USE_DYNS:
            pred[0:2], pred[3:5] = common.globalPosVelChange(self.vec[2], pred[0:2], pred[3:5])
        else:
            pred[0:2], v = common.globalPosVelChange(self.vec[2], pred[0:2], np.zeros(2))
        print "prediction for o: {}: {}".format(self.id, pred)
        self.predVec = self.vec + pred#*1.5 #interestingly enough, *1.5 improves prediction accuracy quite a lot
        resO.vec = np.round(self.predVec, common.NUMDEC)
        resO.lastVec = np.copy(self.vec)
#        print "resulting object: ", resO.vec[1:4]
        return resO
        
        
        
    def update(self, newO):
        self.lastVec = np.copy(self.vec)
        self.vec = np.copy(newO.vec)
        
    def circle(self, otherObject, direction = None):
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
        relPos = otherObject.vec[0:2] - self.vec[0:2]
        if dist < 0.04:
            return 0.4*relPos/np.linalg.norm(relPos)
        elif dist > 0.06:
            return -0.4*relPos/np.linalg.norm(relPos)
        else:
            tangent = np.array([-relPos[1], relPos[0], 0.0])
            if direction != None and np.any(tanged*direction < 0):
                return -0.4*tangent/np.linalg.norm(tangent)
            else:
                return 0.4*tangent/np.linalg.norm(tangent)
        
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
        ang = self.vec[2]
        c = np.cos(ang)
        s = np.sin(ang)
        p1xn = p1x*c -p1y*s + self.vec[0]
        p1yn = p1x*s + p1y*c + self.vec[1]
        p2xn = p2x*c - p2y*s + self.vec[0]
        p2yn = p2x*s + p2y*c + self.vec[1]
        return np.array([np.copy(self.vec[0:2]), np.array([p1xn,p1yn]), np.array([p2xn,p2yn])])
        
        
    @classmethod
    def parse(cls, m):
        res = cls()
        res.id = m.id 
        if USE_DYNS:
            res.vec = np.zeros(5)
#            res.vec[0] = m.id
            res.vec[0] = npround(m.pose.position.x, NUMDEC) #posX
            res.vec[1] = npround(m.pose.position.y, NUMDEC) #posY
            res.vec[2] = npround(common.quaternionToEuler(np.array([m.pose.orientation.x,m.pose.orientation.y,
                                                m.pose.orientation.z,m.pose.orientation.w])), NUMDEC)[2] #ori
            res.vec[3] = npround(m.linVel.x, NUMDEC) #linVelX
            res.vec[4] = npround(m.linVel.y, NUMDEC) #linVelY
        
#            res.vec[8] = npround(m.angVel.z, NUMDEC) #angVel
        else:
            res.vec = np.zeros(3)
#            res.vec[0] = m.id
            res.vec[0] = npround(m.pose.position.x, NUMDEC) #posX
            res.vec[1] = npround(m.pose.position.y, NUMDEC) #posY
            res.vec[2] = npround(common.quaternionToEuler(np.array([m.pose.orientation.x,m.pose.orientation.y,
                                                m.pose.orientation.z,m.pose.orientation.w])), NUMDEC)[2] #ori
        res.lastVec = np.copy(res.vec)
        return res

class Actuator(Object):
    
    def __init__(self):
        Object.__init__(self)
        self.predictor = ITM()
        if USE_DYNS:
            self.vec = np.zeros(5)
        else:
            self.vec = np.zeros(3)
        pass
    
    def predict(self, action):
#        res = copy.deepcopy(self)
        res = Actuator()
        res.id = self.id
        self.predVec = np.copy(self.vec)
#        res.vec[5:8] = action #Set velocity
        if USE_DYNS:
            self.predVec[3:5] = action
        else:
            pass
        #Hardcorded version
        if HARDCODEDACTUATOR:
#            res.vec[1:4] += 0.01*action
            self.predVec[0:2] += 0.01*action
        else:
            #Only predict position
            p = self.predictor.predict(action)
            self.predVec[0:2] += p
#            res.vec[1:4] += p
        res.lastVec = np.copy(self.vec)
        res.vec = np.round(self.predVec, common.NUMDEC)
        res.predictor = self.predictor
        return res
            
    def update(self, newAc, action, training = True):
        self.lastVec = self.vec
#        self.predictor = newAc.predictor
        if training:
            if HARDCODEDACTUATOR:
                pass
            else:
                pdif = newAc.vec[0:2]-self.vec[0:2]
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
        self.clas = ITM()
        self.isTrained = False
        
    def train(self, o1vec, avec, label):
        if HARDCODEDGATE:
            pass
        else:
            self.clas.update(o1vec[[2,3,6,7]], np.array([label]), testMode=0)
            self.isTrained = True
    
    def test(self, ovec, avec):
        
        if HARDCODEDGATE:
            if ovec[3] <= -ovec[2]:
#                print "Change: closing: {}, dist: {}, relVel: {}".format(ovec[3], ovec[2], ovec[6:8])
                return 1
            else:
                if ovec[3] == 0 and np.linalg.norm(ovec[6:8]) < 0.001 and ovec[2] < 0.05: #Todo remove distance from this
#                    print "Change: closing: {}, dist: {}, relVel: {}".format(ovec[3], ovec[2], ovec[6:8])
                    return 1    
                else:
#                    print "no Change: closing: {}, dist: {}, relVel: {}".format(ovec[3], ovec[2], ovec[6:8])
                    return 0
        else:
#            print "testing with gate itm"
            if self.isTrained:
                pred = self.clas.test(ovec[[2,3,6,7]], testMode=0)
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
        if np.linalg.norm(dif[0:2]) > 0.0 or abs(dif[2]) > 0.0:
#        if np.linalg.norm(dif) > 0.0:    
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
        self.signCombinations= {}
        self.signCombinationSums= {}
        self.signCombinationNumbers = {}
        self.lenPreCons = 0
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
        self.lenPreCons = lPre
        curSigCom = []
        for i in xrange(lPre):
            if pre[i] < -0.001:
                curSigCom.append('-1')
            elif pre[i] > 0.001:
                curSigCom.append('1')
            else:
                curSigCom.append('0')
        curSigCom = ";".join(curSigCom)
        if curSigCom in self.signCombinations:
            self.signCombinations[curSigCom] += dif
            self.signCombinationSums[curSigCom] += dif*pre
            self.signCombinationNumbers[curSigCom] += 1
        else:
            self.signCombinations[curSigCom] = dif
            self.signCombinationSums[curSigCom] = dif*pre
            self.signCombinationNumbers[curSigCom] = 1
            
    def getPreconditions(self):
        res = np.zeros(self.lenPreCons)
        res2 = np.zeros(self.lenPreCons)
        l = sorted([(k, v) for k,v in self.signCombinations.items()], key=itemgetter(1), reverse=True)
        if len(l) > 1:
            comb1 = l[0][0].split(";")
            comb2 = l[1][0].split(";")
            pre1 = self.signCombinationSums[l[0][0]]
            pre2 = self.signCombinationSums[l[1][0]]
            w1 = self.signCombinations[l[0][0]]
            w2 = self.signCombinations[l[1][0]]
            for i in xrange(len(comb1)):
                if comb1[i] == comb2[i] or comb1[i] == '0' or comb2[i] == '0':
                    res[i] = (pre1[i]+pre2[i])/(w1+w2)
                    res2[i] = res[i]
                else:
                    res[i] = pre1[i]/w1
                    res2[i] = pre2[i]/w2
            return res, res2
        else:
            return self.signCombinationSums[l[0][0]]/self.signCombinations[l[0][0]], None
            
class MetaNetwork(object):
    
    def __init__(self):
        self.nodes = {}
        self.curIndex = None
        self.curSecIndex = None
        self.preConsSize = None
        self.difSize = None
        self.targetIndex = None
        self.preConsToCheck = None
        self.preConsToTry = None
        self.preConIndex = 4  #Currently hard coded to only look at position
        self.tryNext = False
        pass
    
    def train(self, pre, difs):
        if self.preConsSize == None:
            self.preConsSize = len(pre)
        if self.difSize == None:
            self.difSize = len(difs)
        targetIndexFound = False
#        print "difs: ", difs
#        print "training network with pre: ", pre
        for i in xrange(len(difs)):
            #It appears smaller values break inverse model since the weights can 
            #get swapped for point symmetric preconditions
            if abs(difs[i]) > 0.002: 
                index = str(i*np.sign(difs[i]))
                if not index in self.nodes:
                    self.nodes[index] = MetaNode()
#                print "training index: {} with dif: {}".format(index, difs[i])
#                print "precons: ",pre[[4,5,6,10,11]]
                self.nodes[index].train(pre,abs(difs[i]))

                if self.targetIndex != None and index == self.targetIndex:
                    print "target: {} successfully found.".format(index)
                    self.targetIndex =None
                    self.preConIndex = 4
                    targetIndexFound = True
        if self.preConsToTry != None:
            print "precons similarity: ", np.linalg.norm(pre-self.preConsToTry)
            print "given pres: ", pre
            print "desired pres: ", self.preConsToTry
        if self.preConsToTry != None and np.linalg.norm(pre-self.preConsToTry) < 0.01:
            print "similar precons reached: ", np.linalg.norm(pre-self.preConsToTry)
            if not targetIndexFound:
                print "similar precons did not yield expected results."
                print "targetIndex: ", self.targetIndex
                print "actual difs: ", difs
                self.tryNext = True

                
    def tobeNamed(self):
        """
            Function that tries to find preconditions that might increase its knowledge
            about the obejct interaction.
        """
        if self.targetIndex == None:
            curKeys = self.nodes.keys()
            print "curKeys: ", curKeys
            for i in xrange(self.difSize):
                if str(1.0*i) in curKeys and not str(-1.0*i) in curKeys:
                    self.targetIndex = str(-1.0*i)
                    self.preConsToCheck = self.nodes[str(1.0*i)].getPreconditions()[0]
                    break
                if str(-1.0*i) in curKeys and not str(1.0*i) in curKeys:
                    self.targetIndex = str(1.0*i)
                    self.preConsToCheck = self.nodes[str(-1.0*i)].getPreconditions()[0]
                    break
                #TODO if no unkown key is left, look at "worst" key and improve that
                # figure out a way to measure which one is worst
        else:
            if self.tryNext:
                self.preConIndex += 1
            if self.preConIndex == 7:#len(self.preConsToCheck):
                self.targetIndex = None
                self.preConIndex = 4    
                return self.tobeNamed()
                
        if self.targetIndex == None:
            print "No key found to improve"
            return None
                
        print "targetIndex: ", self.targetIndex
        self.preConsToTry = np.copy(self.preConsToCheck)
        self.preConsToTry[self.preConIndex] *= -1
            

        return self.preConsToTry
        
                
    def getPreconditions(self, targetDifs):
        res = self.preConsSize
        if GREEDY_TARGET:
            if self.curIndex != None:
                ind = float(self.curIndex)
                indSign = -1 if '-'in self.curIndex else 1
                #Consider making this a ratio of maximum/total difs so that it avoids jumping back and forth when it is already quite close to target
                if indSign == np.sign(targetDifs[abs(ind)]) and abs(targetDifs[abs(ind)]) > 0.01: 
                    print "working on curIndex: ", self.curIndex
                    preCons1, preCons2 = self.nodes[self.curIndex].getPreconditions()
                else:
                    self.curIndex = None
                    
            
            if self.curIndex == None:
                print "target difs: ", targetDifs
                sortedDifs = np.argsort(abs(targetDifs))     
                print "sortedDifs: ", sortedDifs
                maxDif = sortedDifs[-1]
                index = str(maxDif*np.sign(targetDifs[maxDif]))
                self.curSecIndex =str(sortedDifs[-2]*np.sign(targetDifs[sortedDifs[-2]]))
#                print "targetDifs: ", targetDifs
#                print "maxindex: ", index
                if not index in self.nodes:
                    print "index i {} for targetDif {}, not known".format(index, targetDifs[abs(float(index))])
                    print "nodes: ", self.nodes.keys()
                    print "targetDifs: ", targetDifs
                    return None
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
                        if min(o1,o3) <= min(o2,o4):
                            print "using pre1 sec"
                            return preCons1
                        else:
                            print "using pre2 sec"
                            return preCons2
                

        else:
            raise NotImplementedError("Currently only greedy is possible")
        
            
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
            
    def getExplorationPreconditions(self, objectId):
        if objectId in self.inverseModel:
            return self.inverseModel[objectId].tobeNamed()
        else:
            print "No inverse model for objectId {}".format(objectId)
    
    def update(self, intState, action, dif):
        if not intState[0] in self.predictors:
            #TODO check for close ones that can be used
            self.predictors[intState[0]] = ITM()
            self.inverseModel[intState[0]] = MetaNetwork()
        if np.linalg.norm(dif) == 0.0:
            print "training with zero dif: ", dif
            raise NotImplementedError
        self.predictors[intState[0]].update(intState[mask], dif, etaIn = 0.1)
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
        difVec = targetO.vec-self.target.vec
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
        # Get promising pre conditions
        # Fullfilly pre conditions
        # Perform action from precondtions (idially if it triggers gate/find action that triggers gate)
        # (If successfull ->) get next set of preconditions for different attribute?
        for oId in self.curObjects.keys():
            preCons = self.predictor.getExplorationPreconditions(oId)
            
        if preCons == None:
            print "No features found that need to be improved"
            return np.zeros(2)
        else:
            targetO = self.curObjects[oId]
            relTargetPos = preCons[4:6]
            print "rel target pos: ", relTargetPos
            relTargetVel = preCons[8:10]
            print "relTargetVel: ", relTargetVel
            
            pos, vel = targetO.getGlobalPosVel(relTargetPos, relTargetVel)
            print "target vel: ", vel
            print "target pos: ", pos
            print "cur pos: ", self.actuator.vec[0:2]
            difPos = pos-self.actuator.vec[0:2]
            print "difpos norm: ", np.linalg.norm(difPos)
            relVec = targetO.getRelVec(self.actuator)
            
#                relVec = targetO.getRelObjectVec(self.actuator)
            relPos = relVec[4:6]
            # Determine Actuator position that allows action in good direction
            wrongSides = relPos*relTargetPos < 0
            if np.any(wrongSides):
                if max(abs(relTargetPos[wrongSides]-relPos[wrongSides])) > 0.05:
                 # Bring actuator into position so that it influences targetobject
                    print "try circlying"
                    return targetO.circle(self.actuator)
                    
            if np.linalg.norm(difPos) > 0.01:
                action = 0.5*difPos/np.linalg.norm(difPos)
                print "difpos action: ", action
                tmpAc = self.actuator.predict(action)
                return action

            print "using vel"
            normVel = np.linalg.norm(vel)
            if normVel == 0.0:
                pass
            else:
                vel = 0.5*vel/normVel
            tmpAc = self.actuator.predict(vel)
            if not self.gate.test(targetO, tmpAc, vel):
                print "looking for different vel"
                for i in xrange(len(vel)):
                    tmpVel = relTargetVel
                    tmpVel[i] *= -1
                    pos, tmpVel = targetO.getGlobalPosVel(relTargetPos, relTargetVel)
                    normVel = np.linalg.norm(tmpVel)
                    if normVel == 0.0:
                        pass
                    else:
                        tmpVel = 0.5*tmpVel/normVel
                    tmpAc = self.actuator.predict(tmpVel)
                    
                    if self.gate.test(targetO, tmpAc, tmpVel):
                        vel = tmpVel
                        print "found new vel: ", vel
                        break
            return vel
                

        
    def getAction(self):
        """
            Returns an action, that is to be performed, trying to get closer to the
            target if one is set.
            
            Returns: np.ndarray
                Action vector for the actuator
        """
        if self.target is None:
#            return self.explore()
            return np.array([0.0,0.0,0.0])
            pass
        else:
            if self.isTargetReached():
                print "target reached"
                self.target = None
                return np.array([0.0,0.0,0.0])
            else:
                targetO = self.curObjects[self.target.id]
                # Determine difference vector, the object should follow
#                print "global dif vec: ", self.target.vec-targetO.vec
                difVec = targetO.getLocalChangeVec(self.target)
                difNorm = np.linalg.norm(difVec)
#                print "difVec: ", difVec[:5]
                pre = self.predictor.getAction(self.target.id, difVec)
                if pre == None:
                    return self.explore()
                relTargetPos = pre[4:6]
                print "rel target pos: ", relTargetPos
                relTargetVel = pre[8:10]
                print "relTargetVel: ", relTargetVel
                
                pos, vel = targetO.getGlobalPosVel(relTargetPos, relTargetVel)
                print "target vel: ", vel
                print "target pos: ", pos
                print "cur pos: ", self.actuator.vec[0:2]
                difPos = pos-self.actuator.vec[0:2]
#                print "difpos norm: ", np.linalg.norm(difPos)
                relVec = targetO.getRelVec(self.actuator)
#                relVec = targetO.getRelObjectVec(self.actuator)
                relPos = relVec[4:6]
                # Determine Actuator position that allows action in good direction
                wrongSides = relPos*relTargetPos < 0
                if np.any(wrongSides):
                    if max(abs(relTargetPos[wrongSides]-relPos[wrongSides])) > 0.05:
                     # Bring actuator into position so that it influences targetobject
                        print "try circlying"
                        return targetO.circle(self.actuator)
                        
                if np.linalg.norm(difPos) > 0.01:
                    action = 0.3*difPos/np.linalg.norm(difPos)
                    print "difpos action: ", action
                    tmpAc = self.actuator.predict(action)
                    if not self.gate.test(targetO, tmpAc, action):
                        print "doing difpos"
                        return action
                    else:
                        predRes = self.predictor.predict(targetO, tmpAc, action)
                        if np.linalg.norm(predRes.vec-self.target.vec) > np.linalg.norm(targetO.vec-self.target.vec):
                            print "circlying since can't do difpos"
                            return targetO.circle(self.actuator, action)
                        else:
                            print "doing difpos anyways"
                            return action

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
        #TODO Remove ws from here since it is not needed at all. Not true if online learning is tested in new prediction task
        newWS = WorldState()
#        newWS.actuator = self.actuator.predict(action)
        newWS.actuator = ws.actuator.predict(action)
        for o in ws.objectStates.values():
#        for o in self.curObjects.values():
            if self.gate.test(o, newWS.actuator, action):
                newO = self.predictor.predict(o, newWS.actuator, action)
                newWS.objectStates[o.id] = newO
                
            else:
                if USE_DYNS:
                    #Stop dynamics
                    o.vec[3:] = 0.0
                    
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
        self.actuator.update(curWS.actuator, np.array([0.0,0.0]))
        
    def update(self, curWS, action):
        print "updating model"
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
            
    