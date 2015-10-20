#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 19:15:35 2015

@author: jpoeppel
"""
#
import numpy as np
#
#
#data = np.loadtxt("../data/gateModel10Runs_Gate_Act_NoDynsITMNewWinner.txt", delimiter=";")
#
#print np.mean(data,axis = 0)

#data = np.loadtxt("./testData.txt", delimiter=";")
#print data
"""
New records
"""


import os

#directory = "../evalData/"
directory = "./"

fileList = os.listdir(directory)

for f in fileList:
    if "config" in f:
        break
    
    if "evalTest" in f:
        #load data
        print "filename: ", directory+f
        data = np.loadtxt(directory+f, delimiter = ';')
        
        trainrows = data[:,1] == 1
        
        testrows = np.invert(trainrows)
        testData = data[testrows,:]
        testDifs = np.copy(testData[:,:14])
        testDifs[:,5:14] -= testData[:,14:]
        
        lastFrames = testData[:,3] ==0
        lastFrames = np.roll(lastFrames, -1) #TODO Test if this is always correct!
        
        #Consider filtering, i.e. only last frame
        actDifs = testDifs[:,12:14]
        oriDifs = testDifs[:,11]
        posDifs = testDifs[:,5:7]
        keyPoint1Difs = testDifs[:,7:9]
        keyPoint2Difs = testDifs[:,9:11]
        
