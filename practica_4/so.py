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
        if not self.kernel.scheduler.isEmpty():
            nextPcb = self.kernel.scheduler.getNextPcb()
            nextPcb.state = "Running"
            self.kernel.dispatcher.load(nextPcb)
        elif not self.kernel.ioDeviceController._currentPCB is None: #con esto verificamos si hay un proceso en waiting
             log.logger.info("Hay un proceso en waiting, esperar.")
             
        else:
            print(self.kernel.pcbTable._table) #imprimo como quedaron los pcb
            HARDWARE.switchOff()
            print(self.kernel.diagrama.table)
            print(self.kernel.diagrama.print_gantt())
            

        



class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters

        pcb = self.kernel.runningPCB     ##guardo el pcb que estaba running
        pcb.state = "Waiting"            # ponemos el pcb que estaba running en waiting
        self.kernel.dispatcher.save(pcb) ##el distpacher se encarga de guardar la posicion y liberar la cpu
        
        
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        log.logger.info(self.kernel.ioDeviceController)

        if not self.kernel.scheduler.isEmpty():
            nextPcb = self.kernel.scheduler.getNextPcb()
            nextPcb.state = "Running"
            self.kernel.dispatcher.load(nextPcb)

class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        self.kernel.cargarPcb(pcb)     
        log.logger.info(self.kernel.ioDeviceController)      


##NEW 
class NewIterruptionHandler(AbstractInterruptionHandler):
        def execute(self,irq):
            parameters = irq.parameters	        
            program = parameters['program']	        
            priority = parameters['priority']
            ##Cargar En Memoria y devolver dirBase
            dirBase = self.kernel.loader.load(program)
            ##crearPCB
            pcb = PCB(program.name, dirBase, priority)
            ##agregar pcb en la tablaPCB
            self.kernel.pcbTable.add(pcb)
            ##Si el cpu esta ocupado ponerlo en la readyQueue sino ponerlo en ejecucion/running
            self.kernel.cargarPcb(pcb)
            
            log.logger.info("\n Executing program: {name}".format(name=program.name))
            log.logger.info(HARDWARE)
            ##HARDWARE.cpu.pc = 0
            print(self.kernel.pcbTable._table)
            print(self.kernel.scheduler.readyQueue)

class TimeoutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        #  si hay un PCB corriendo y la readyQueue no está vacía
        if  self.kernel.runningPCB is not None and not self.kernel.scheduler.isEmpty():
            pcbRunning = self.kernel.runningPCB    #guardo el pcb que esta running y cambio su estado a ready
            pcbRunning.state = "Ready"
             # Guardo el  el pcbRunning y lo agrego a la ready queue 
            self.kernel.dispatcher.save(pcbRunning)
            self.kernel.scheduler.add(pcbRunning)

            # cargo el nextPCB de la ready queue
            nextPcb = self.kernel.scheduler.getNextPcb()
            nextPcb.state = "Running"
            self.kernel.dispatcher.load(nextPcb)
            log.logger.info(f"Timeout: PCB {pcbRunning.pid} expropiado. PCB {nextPcb.pid} en ejecución.")
        else:
            # Si no hay ningún PCB corriendo o la readyQueue está vacía, no hacer nada
            log.logger.info("Timeout: No hay PCB corriendo o la readyQueue está vacía.")



class StatInterruptionHandler(AbstractInterruptionHandler):
    
    def execute(self,irq):
        self.kernel.scheduler.checkTick()
        self.kernel.diagrama.checkTick()


class DiagramGant:
    def __init__(self,kernel):
        self._kernel = kernel
        self.table = []

    @property
    def kernel(self):
        return self._kernel
    
    def add(self, list):
        self.table.append(list)

    def checkTick(self):
        tickActual = HARDWARE.clock.currentTick         ##Obtengo el tick actual
        if self.kernel.runningPCB is not None:          ##Me fijo que haya un proceso en running
            pid = self.kernel.runningPCB.pid            ##Obtengo el pid del pcb en running
            self.kernel.diagrama.add([tickActual,pid])  ##agrego al diagrama, que pid se ejecuto en el tickActual

    def print_gantt(self):
        ticks = [tick for tick, _ in self.table]                    ##Obtengo una lista de todos los ticks
        max_tick = max(ticks)                                       ##Obtengo cual fue el maximo tick para el header
        pids = sorted(set(pid for _, pid in self.table))            ##Ordeno sin repeticion los pids
        tabla = []  
        for pid in pids:
            fila = [f"P{pid}"]
            for tick in range(max_tick + 1):                        ## + 1 para contemplar el 0         
                simbolo = "-" if [tick, pid] in self.table else " "
                fila.append(simbolo)
            tabla.append(fila)
        headers = [f"{self.kernel.scheduler.name}"] +  [ t for t in range(max_tick + 1)]
        print(tabulate(tabla, headers=headers, tablefmt="grid"))
        

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
        HARDWARE.timer.reset() 
   
    def save(self, pcb):
        pcb.pc = HARDWARE.cpu.pc 
        self.kernel.runningPCB = None
        HARDWARE.cpu.pc = -1


## PCB
class PCB:
    _pidCount = 0
    def __init__(self, processName, dir, prioridad = None):
        PCB._pidCount += 1
        self._pid = PCB._pidCount
        self._baseDir = dir
        self._pc = 0
        self._state = "Ready"
        self._path = processName
        self._priority = prioridad
        self._priorityTemp = self._priority

    @property
    def pid(self):
        return self._pid
    
    @property
    def pc(self):
        return self._pc

    @property
    def priority(self):
        return self._priority

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

    @property
    def priorityTemp(self):
        return self._priorityTemp

    @priorityTemp.setter
    def priorityTemp(self,newPrioTemp):
        self._priorityTemp = newPrioTemp
        
    def __repr__(self):
        return "pid: {pid} celdaDir: {dir} pc: {pc} estado: {estado} nombreProceso: {nombre} prioridad: {prioridad} prioridadTemporal: {prioTemp}\n ".format(pid=self._pid, dir=self._baseDir, pc=self._pc,estado=self._state, nombre=self._path, prioridad = self._priority, prioTemp = self._priorityTemp)
       

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

##---------------------------  AbstactScheduler   --------------------------
class AbstactScheduler:
    def __init__(self):
        self.readyQueue = []
        self.name = 'Abstact'

    @property
    def name(self):
        return self._name

    def add (self,pcb): ##agrega un pcb a la readyQueue
        self.readyQueue.append(pcb)

    def isEmpty(self): ## retorna si la readyqueue esta vacia o no
        return len(self.readyQueue) == 0

    def checkTick(self):
        # el scheduler FCFS no hace nada 
        pass
    ##para no romper si cambio de scheduler
    def mustExpropiate(self,PCBenPC,PCBParaAgregar):
        return False


##----------------------------------------------------------------
class schedulerFCFS(AbstactScheduler):
    def __init__(self):
        self.readyQueue = []
        self._name = 'FCFS'

    def getNextPcb(self): # Si la readyQueuee sta vacia retorna none sino devuelve el primero de la readyQueue
        if self.isEmpty():
            return None
        else:
            return self.readyQueue.pop(0)
        ## Hereda las demas funciones del AbstractScheduler

##----------------------------------------------------------------
class schedulerRR(schedulerFCFS):
    def __init__(self,quantum):
        self._quantum = quantum
        HARDWARE.timer.quantum = quantum #seteo el quantum para el schedule RoundRobin
        self._name = 'RR'

    @property
    def name(self):
        return self._name

    @property
    def quantum(self):
        return self._quantum     
    
    ## Hereda las demas funciones del schedulerFCFS

##----------------------------------------------------------------
class schedulerPrioNoEx(AbstactScheduler):
    def __init__(self):
        self._tickParaAging = 5
        HARDWARE.cpu.enable_stats = True
        self._name = 'PrNEx'

    def getNextPcb(self):  # Si la readyQueuee esta vacia retorna none sino devuelve el pcb con mayor prioridad(siendo 0 el mas alto)
        if self.isEmpty(): 
            return None
        else:
            return self.pcbConMayorPrioridad()

    def pcbConMayorPrioridad(self):
        pcbConMasPrioridad = self.readyQueue[0]
        for pcb in self.readyQueue[1:]:
            if pcb.priorityTemp < pcbConMasPrioridad.priorityTemp:  
                pcbConMasPrioridad = pcb

        self.readyQueue.remove(pcbConMasPrioridad)
        return pcbConMasPrioridad
    
    def aumentarPrio(self,pcb):
        if pcb.priorityTemp > 0:
            pcb.priorityTemp -= 1

    def checkTick(self):
        if self._tickParaAging == 0:
            log.logger.info("Se realizo aging")
            log.logger.info(f"prioridades despues del aging: {self.readyQueue}")
            self._tickParaAging = 5
            for pcb in self.readyQueue:
                self.aumentarPrio(pcb)
        else:
            self._tickParaAging -= 1
    ## Hereda las demas funciones del AbstractScheduler

##----------------------------------------------------------------


class schedulerPrioEx(schedulerPrioNoEx):
    def __init__(self):
        self._name = 'PrEx'

    def mustExpropiate(self,PCBenPC,PCBParaAgregar):
        return PCBParaAgregar.priority < PCBenPC.priority 

    ## Hereda las demas funciones del scheduler no expropiativo
    ## con la diferencia de que  tiene que expropiar

##----------------------------------------------------------------





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

        timeoutHandler = TimeoutInterruptionHandler(self)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)

        statHandler =  StatInterruptionHandler(self)
        HARDWARE.interruptVector.register(STAT_INTERRUPTION_TYPE, statHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self._loader = Loader()
        self._pcbTable = PCBTable()
        self._scheduler = schedulerRR(4)
        self._runningPCB = None
        self._dispatcher = Dispatcher(self)
        self._diagrama = DiagramGant(self)
        HARDWARE.cpu.enable_stats = True

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    @property
    def runningPCB(self):
        return self._runningPCB

    @property
    def loader(self):
        return self._loader

    @property
    def pcbTable(self):
        return self._pcbTable

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def dispatcher(self):
        return self._dispatcher

    @property
    def diagrama(self):
        return self._diagrama
    
    
    @runningPCB.setter
    def runningPCB(self,pcb):
        self._runningPCB = pcb

    ## emulates a "system call" for programs execution
    def run(self, program,priority = None):
        parameters = {'program': program, 'priority': priority}
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, parameters)
        HARDWARE.interruptVector.handle(newIRQ)

    def cargarPcb(self,pcb):
        if self.runningPCB is None:
            pcb.state = "Running"
            self.dispatcher.load(pcb)
        elif self.scheduler.mustExpropiate(self.runningPCB,pcb):
            pcbExpropiado = self.runningPCB
            self.scheduler.add(pcbExpropiado)
            self.dispatcher.load(pcb)
        else:
            pcb.state = "Ready"
            self.scheduler.add(pcb)

    def __repr__(self):
        return "Kernel "
