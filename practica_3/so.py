#!/usr/bin/env python

from hardware import *
import log



## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)




## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            #print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)


    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)

## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        pcbF = self.kernel.runningPCB
        pcbF.state = "Terminated"
        self.kernel.dispatcher.save(pcbF)

        # Si hay procesos en ReadyQueue, los cargamos
        if not self.kernel.readyQueue.isEmpty():
            nextPcb = self.kernel.readyQueue.getNextPcb()
            nextPcb.state = "Running"
            self.kernel.dispatcher.load(nextPcb)
        elif not self.kernel.ioDeviceController._currentPCB is None: #con esto verificamos si hay un proceso en waiting
             log.logger.info("Hay un proceso en waiting, esperar.")
             
        else:
            print(self.kernel.pcbTable._table) #imprimo como quedaron los pcb
            HARDWARE.switchOff()
            

        



class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        #pcb = {'pc': HARDWARE.cpu.pc} # porque hacemos esto ???, y para guardar donde se quedo

        pcb = self.kernel.runningPCB     ##guardo el pcb que estaba running
        pcb.state = "Waiting"            # ponemos el pcb que estaba running en waiting
        self.kernel.dispatcher.save(pcb) ##el distpacher se encarga de guardar la posicion y liberar la cpu
        
        
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        log.logger.info(self.kernel.ioDeviceController)

        if not self.kernel.readyQueue.isEmpty():
            nextPcb = self.kernel.readyQueue.getNextPcb()
            nextPcb.state = "Running"
            self.kernel.dispatcher.load(nextPcb)

class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        self.kernel.cargarPcb(pcb)
       

        log.logger.info(self.kernel.ioDeviceController)      


##NEW 
##SI HAY PRINTS RANDOM, ES QUE ESTUVE PROBANDO
class NewIterruptionHandler(AbstractInterruptionHandler):
        def execute(self,irq):
            ##Cargar En Memoria y devolver dirBase
            dirBase = self.kernel.loader.load(irq.parameters)
            ##crearPCB
            pcb = PCB(irq.parameters.name, dirBase)
            ##agregar pcb en la tablaPCB
            self.kernel.pcbTable.add(pcb)
            ##Si el cpu esta ocupado ponerlo en la readyQueue sino ponerlo en ejecucion
            self.kernel.cargarPcb(pcb)
            
            log.logger.info("\n Executing program: {name}".format(name=irq.parameters.name))
            log.logger.info(HARDWARE)
            ##HARDWARE.cpu.pc = 0
            print(self.kernel.pcbTable._table)
##LOADER
class Loader:

    def __init__(self):
        self._baseDir = 0

    def load(self, program):
        # loads the program in main memory
        startDir = self._baseDir
        progSize = len(program.instructions)
        
        for index,inst in enumerate(program.instructions):
            HARDWARE.memory.write(startDir + index, inst)
        self._baseDir += progSize
        return startDir #  _baseDir

## DISPATCHER
class Dispatcher():

    def __init__(self,kernel):
        self._kernel = kernel
    
    @property
    def kernel(self):
        return self._kernel

    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc 
        HARDWARE.mmu.baseDir = pcb.baseDir
        self.kernel.runningPCB = pcb
        #print("PCB EN ESTADO RUNNING ACTUAL: ", self.kernel.runningPCB)
   
    def save(self, pcb):
        pcb.pc = HARDWARE.cpu.pc 
        self.kernel.runningPCB = None
        HARDWARE.cpu.pc = -1

## PCB
class PCB:
    _pidCount = 0
    def __init__(self, processName, dir):
        PCB._pidCount += 1
        self._pid = PCB._pidCount
        self._baseDir = dir
        self._pc = 0
        self._state = "Ready"
        self._path = processName

    @property
    def pid(self):
        return self._pid
    
    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, value):
        self._pc = value
    
    @property
    def baseDir(self):
        return self._baseDir
    
    @property
    def state(self):
        return self._state 

    @state.setter
    def state(self,newState):
        self._state = newState
        
    def __repr__(self):
        return "pid: {pid} celdaDir: {dir} pc: {pc} estado: {estado} nombreProceso: {nombre}\n ".format(pid=self._pid, dir=self._baseDir, pc=self._pc,estado=self._state, nombre=self._path)
       

#PCBTable
class PCBTable:

    def __init__(self):
        self._table = {}

    def add(self,pcb):
        self._table[pcb.pid] = pcb
    
    def get(self,pid):
        return self._table.get(pid)
    
    def remove(self, pid):
        if pid in self._table:
            return self._table.pop(pid)
        return None
    
class ReadyQueue:
    def __init__(self):
          self.readyQueue = []

    def add (self,pcb): ##agrega un pcb a la readyQueue
        self.readyQueue.append(pcb)

    def isEmpty(self): ## retorna si la readyqueue esta vacia o no
        return len(self.readyQueue) == 0

    def getNextPcb(self): # Si la readyQueuee sta vacia retorna none sino devuelve el primero de la readyQueue
        if self.isEmpty():
            return None
        else:
            return self.readyQueue.pop(0)


# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        newHandler = NewIterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)


        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self.loader = Loader()
        self._pcbTable = PCBTable()
        self.readyQueue = ReadyQueue() 
        self._runningPCB = None
        self.dispatcher = Dispatcher(self)

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    @property
    def runningPCB(self):
        return self._runningPCB

    @property
    def pcbTable(self):
        return self._pcbTable
    
    
    @runningPCB.setter
    def runningPCB(self,pcb):
        self._runningPCB = pcb

    ## emulates a "system call" for programs execution
    def run(self, program):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, program)
        HARDWARE.interruptVector.handle(newIRQ)

    def cargarPcb(self,pcb):
        if self.runningPCB is None:
            pcb.state = "Running"
            self.dispatcher.load(pcb)
        else:
            pcb.state = "Ready"
            self.readyQueue.add(pcb)

    def __repr__(self):
        return "Kernel "