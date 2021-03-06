## BacLog Copyright 2010,2011 by Timothy Middelkoop licensed under the Apache License 2.0
## Services

import tagged
import bacnet
from message import Message
from scheduler import Task

import scheduler

debug=True
trace=True

## Objects

### TODO: Migrate this to a generic object type and push to bacnet 
### These are not first class objects as there is no ANS.1 Encoding.
### Use a similar object structure and initialization style (ducktype) as bacnet objects.

def register(scheduler,mh,servicehandler,Service=None):
    if Service==None:
        Service=servicehandler._service
    print "service.register>", Service
    scheduler.add(servicehandler)
    mh.addService(servicehandler,Service)

class Object:
    _otype=None 
    _properties=None
    instance=None
    value=None
    
    def __init__(self,instance,name,*args):
        self.property={}
        self.instance=instance
        self.addProperty('objectIdentifier',(self._otype,instance))
        self.addProperty('objectName',name)

        for name,value in self._properties:
            self.addProperty(name,value)

        self.init(*args)

        
    def addProperty(self,name,value=None):
            pidentifier=bacnet.PropertyIdentifier(name)
            if type(value)==type(tuple()):
                value=bacnet.Property(*value,identifier=pidentifier)
            elif value is None:
                value=bacnet.Property(identifier=pidentifier) 
            else:
                value=bacnet.Property(value,identifier=pidentifier)
            self.property[pidentifier]=value
            assert not hasattr(self,name) ## Duplicate attr
            setattr(self,name,value)
            return value
            
    def init(self):
        '''Custom initialization of Object'''
        pass

class Device(Object):
    instance=None
    _otype='device' ## TODO: change to _type and possibly use "compiled" types 
    _properties=[
                ('protocolServicesSupported',['whoIs','readPropertyMultiple','unconfirmedCOVNotification','readProperty']),
                ('systemStatus','operational'),
                ('vendorIdentifier',65535),
                ('segmentation','noSegmentation'),
                ('maxAPDU',1024),
                ('maxSegments',1),
                ('APDUSegmentationTimeout',0),
                ('APDURetries',0),
                ('APDUTimeout',0),
                ('objectList',None),
                ]
            
class BinaryOutput(Object):
    instance=None
    _otype='binaryOutput'
    _properties=[
                 ('description',''),
                 ]
    
    def init(self):
        self.addProperty('presentValue',tagged.Boolean())

## Data support    

class InstanceTable:
    def __init__(self,device,name):
        self._instance={}
        self.device=Device(device,name)
        self.add(self.device)
        
    def add(self,properties):
        assert properties.instance is not None ## Instance number not set
        identifier=self.device.objectList._add(properties._otype,properties.instance)
        self._instance[identifier]=properties
        print "InstanceTable.add>", identifier
        
    def __getitem__(self,index):
        return self._instance[index]
        
    def __repr__(self):
        return repr(self._instance)

## Services


class COV(Task):
    '''Incomplete implementation for testing'''
    def init(self,table):
        self.table=table
        self.device=table.device
        self.subscribe={}
        
    def run(self):
        for i in range(0,2):
            yield scheduler.Wait(1)
            for j in range(0,2):
                for o,(request,v) in self.subscribe.items():
                    print "COV>",i,j,o
                    v._value=not v._value ## boolean only!
                    ack=yield self.cov(o,request,v)
                    assert ack==True

    def cov(self,o,request,v):
        p=self.table[o]
        values=bacnet.SequenceOfPropertyValue()
        pv=values._add()
        pv.property=p.presentValue._identifier
        pv.value=p.presentValue
        
        pv.index=None ## set optional: don't like (from New)!
        pv.priority=None
        
        cov=bacnet.UnconfirmedCOVNotification()
        cov.pid=request.message.spid._value
        cov.device=self.device.objectIdentifier._value
        cov.object=o
        cov.time=0 ## TODO: unimplemented
        cov.values=values
        
        print "COV>",cov.pid,cov.device
        return Message(request.remote,cov,confirmed=False)


class SubscribeCOV(Task):
    _service=bacnet.SubscribeCOV

    def init(self,table,cov):
        self.table=table
        self.cov=cov
        
    def run(self):
        request=yield None ## boot
        while True:
            print "SubscribeCOV>", request.message.object
            assert request.message.confirmed._value==False ## only support unconfirmed
            self.cov.subscribe[request.message.object]=(request,self.table[request.message.object].presentValue._value)
            response=bacnet.SubscribeCOVResponse()
            #print "SubscribeCOV>", request.invoke, response
            request=yield Message(request.remote,response,request.invoke)

class ReadPropertyMultiple(Task):
    _service=bacnet.ReadPropertyMultiple

    def init(self,device,name,table):
        self.device=device
        self.name=name
        self.table=table

    def run(self):
        request=yield None ## boot
        while True:
            if trace: print "ReadPropertyMultiple>", request
            response=bacnet.ReadPropertyMultipleResponse()
            for o in request.message:
                assert o.object.instance==self.device ## support only Device
                result=response._add()
                result.object=o.object
                device=Device(self.device,self.name)
                for reference in o.list:
                    value=device.property.get(reference.property,None)
                    if value==None: continue
                    item=result.list._add()
                    item.property=reference.property
                    item.value=value
                    item.index=None
            
            if trace: print "ReadPropertyMultiple>", request.invoke, response
            request=yield Message(request.remote,response,request.invoke)

class ReadProperty(Task):
    _service=bacnet.ReadProperty
    
    def init(self,device,name,table):
        self.device=device
        self.name=name
        self.table=table
        
    def run(self):
        request=yield None ## boot
        while True:
            if trace: print "ReadProperty>", request
            instance=self.table[request.message.object]
            response=bacnet.ReadPropertyResponse()
            response.object=request.message.object
            response.property=request.message.property
            response.value=instance.property[request.message.property]

            if request.message.index is not None:
                if request.message.index._value > len(response.value): ## 1 based index; bounds error
                    response=bacnet.Error() ## TODO: give proper error value.
                    response.ecode=bacnet.ErrorCode('invalidArrayIndex')
                    response.eclass=bacnet.ErrorClass('property')
                else:
                    response.index=request.message.index._value
                    response.value=response.value[response.index-1] ## 1 based index
                    assert response.index!=0 ## not supported

            if trace: print "ReadProperty>", request.invoke, response
            request=yield Message(request.remote,response,request.invoke)

class WriteProperty(Task):
    _service=bacnet.WriteProperty
    
    def init(self,table):
        self.table=table
        
    def run(self):
        request=yield None ## Boot
        while True:
            print "WriteProperty>", request
            request=yield Message(request.remote,bacnet.WritePropertyACK(),request.invoke)
            


class WhoIs(Task):
    _service=bacnet.WhoIs
    
    def init(self,device):
        self.device=device

    def run(self):
        whois=yield None ## boot
        while True:
            print "WhoIs>", whois
            iam=bacnet.IAm()
            iam.object=bacnet.ObjectIdentifier('device',self.device)
            iam.maxlength=1024
            iam.segmentation=bacnet.Segmented('noSegmentation') #@UndefinedVariable
            iam.vendor=65535
            print "WhoIs>", iam
            whois=yield Message(whois.remote,iam,timeout=None)

