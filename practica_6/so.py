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
        # Obtenemos el PCB que estaba corriendo
        pcbQueMuere = self.kernel.runningPCB
        if pcbQueMuere is None:
            log.logger.info("Kill: no hay PCB corriendo.")
            return

        # Liberar frames que tenga en memoria
        framesUsados = []
        for val in pcbQueMuere.pageTable.values():
            if val is not None:
                (frame, isDirty) = val
                framesUsados.append(frame)

        if framesUsados:
            self.kernel.memoryManager.releaseFrames(framesUsados)

        pcbQueMuere.state = "Terminated"
        # quitarlo de la PCB table
        self.kernel.pcbTable.remove(pcbQueMuere.pid)
        self.kernel.dispatcher.save(pcbQueMuere)

        if not self.kernel.scheduler.isEmpty():
            nextPcb = self.kernel.scheduler.getNextPcb()
            nextPcb.state = "Running"
            self.kernel.dispatcher.load(nextPcb)
        elif not self.kernel.ioDeviceController._currentPCB is None:
            log.logger.info("Hay un proceso en waiting, esperar.")
        else:
            # Si no hay más procesos, apagamos hardware y mostramos diagrama
            print(self.kernel.pcbTable._table)
            HARDWARE.switchOff()
            print(self.kernel.diagrama.table)
            print(self.kernel.diagrama.print_gantt())



# kill anterior
# class KillInterruptionHandler(AbstractInterruptionHandler):

#     def execute(self, irq):
#         log.logger.info(" Program Finished ")
#         pcbF = self.kernel.runningPCB
#         pcbF.state = "Terminated"
#         framesDelPcb = pcbF.pageTable.values()
#         self.kernel.memoryManager.freeFrames(framesDelPcb)
#         self.kernel.dispatcher.save(pcbF)
#         print("PCB TERMINADO, frames Actuales:",self.kernel.memoryManager.framesLibres)

#         # Si hay procesos en ReadyQueue, los cargamos
#         if not self.kernel.scheduler.isEmpty():
#             nextPcb = self.kernel.scheduler.getNextPcb()
#             nextPcb.state = "Running"
#             self.kernel.dispatcher.load(nextPcb)
#         elif not self.kernel.ioDeviceController._currentPCB is None: #con esto verificamos si hay un proceso en waiting
#              log.logger.info("Hay un proceso en waiting, esperar.")
             
#         else:
#             print(self.kernel.pcbTable._table) #imprimo como quedaron los pcb
#             HARDWARE.switchOff()
#             print(self.kernel.diagrama.table)
#             print(self.kernel.diagrama.print_gantt())
            

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
            log.logger.info(irq.parameters)
            ##crearPCB
            pcb = PCB(irq.parameters[0],irq.parameters[1])
            log.logger.info(pcb)
            ##Cargar En Memoria y devolver pageTable
            pageTable = self.kernel.loader.load(pcb)
           
            
            pcb.setPageTable(pageTable)
            ##agregar pcb en la tablaPCB
            self.kernel.pcbTable.add(pcb)
            ##Si el cpu esta ocupado ponerlo en la readyQueue sino ponerlo en ejecucion/running
            self.kernel.cargarPcb(pcb)
            
            log.logger.info("\n Executing program: {name}".format(name=irq.parameters[0]))
            log.logger.info(HARDWARE)

            ##HARDWARE.cpu.pc = 0
            print(self.kernel.pcbTable._table)
            print(self.kernel.scheduler.readyQueue)
            print("Frames Dsp de asignarles al pcb:",self.kernel.memoryManager.framesLibres)


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



## Page Fault Handler
class PageFaultInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        pageId = irq.parameters                # Página que causó el Page Fault
        pcb = self.kernel.runningPCB           # PCB que estaba en ejecución
        self.kernel.pageFaultCount += 1
        print(f"[PAGE FAULT #{self.kernel.pageFaultCount}]  PCB {pcb.pid} necesita la página {pageId}")

        #log.logger.info(f"!!! PAGE FAULT: PCB {pcb.pid} necesita la Página {pageId}")


        framesAsignados = self.kernel.memoryManager.alocFrames(1) #  pido un frame libre al MemoryManager 
        if not framesAsignados:
            log.logger.error("No hay frames libres para manejar Page Fault.")
            HARDWARE.switchOff()
        frame = framesAsignados[0] # Obtenemos el frame
        log.logger.info(f"Asignando Frame {frame} para la Página {pageId}")
        program = self.kernel.fileSystem.read(pcb.path) # cargo la pagina desde el filesystem al frame
        frameSize = HARDWARE.mmu.frameSize

        startIndex = pageId * frameSize # inicio y fin  de la pagina
        endIndex = min(startIndex + frameSize, len(program.instructions)) # esto es para solo leer las instrucciones que existen
        # Copiamos las instrucciones de esa página al frame designado
        for i in range(startIndex, endIndex):
            instruction = program.instructions[i]
            offset = i % frameSize
            physicalAddress = frame * frameSize + offset
            HARDWARE.memory.write(physicalAddress, instruction)

        pcb.pageTable[pageId] = (frame, False) # actualizo la pagetable

        # Registrar en el MemoryManager el propietario de ese frame
        self.kernel.memoryManager.registerFrameUsados(frame, pcb.pid, pageId)
        HARDWARE.mmu.setPageFrame(pageId, frame) # actualizo el tlb
        log.logger.info(f"Page Fault resuelto. PCB {pcb.pid} continúa ejecución.")

#####
class MemoryManager:
    def __init__(self, frameSize, kernel):
        HARDWARE.mmu.frameSize = frameSize
        self._kernel = kernel
        self._cantFramesActuales = HARDWARE.memory.size // HARDWARE.mmu.frameSize
        self._framesLibres = [i for i in range(self._cantFramesActuales)]

        self._framesUsados = dict()
        self._victimSelector = FifoVictimSelector() #algoritmo de selecion de victima

    @property
    def framesLibres(self):
        return self._framesLibres

    def alocFrames(self, number):
        frames = []
        for _ in range(number):
            if len(self._framesLibres) > 0:
                frame = self._framesLibres[0]
                self._framesLibres = self._framesLibres[1:]
            else:
                # si no hay frames libres, libero un frame 
                frame = self.liberarVictima()
            # Si consigue un frame, lo agrego a la lista de asignados
            if frame is not None:
                frames.append(frame)
        return frames

    def freeFrames(self, lista):
        # libera una lista de frames (sin tocar owners)
        for frame in lista:
            if frame not in self._framesLibres:
                self._framesLibres.append(frame)
            # quitar del selector por si estaba
            self._victimSelector.removeFrame(frame)
            # quitar owner si existía
            if frame in self._framesUsados:
                self._framesUsados.pop(frame, None)

    def registerFrameUsados(self, frame, pid, pageId):
        self._framesUsados[frame] = (pid, pageId)
        self._victimSelector.addFrame(frame)

    def liberarVictima(self):
        frameVictima = self._victimSelector.selectVictim()
        if frameVictima is None:
            return None

        frameAsignado = self._framesUsados.pop(frameVictima, None)
        if frameAsignado is not None:
            pid, pageId = frameAsignado
            # Buscamos el PCB del proceso que usaba el frame
            pcbVictima = self._kernel.pcbTable.get(pid)
            if pcbVictima:
                # Marcamos la página como no residente (ya no está cargada)
                pcbVictima.pageTable[pageId] = None

        # Limpiamos la TLB (por si apuntaba a una página vieja)
        if HARDWARE.mmu is not None:
            HARDWARE.mmu.resetTLB()

        # Marcamos el frame como libre nuevamente
        if frameVictima not in self._framesLibres:
            self._framesLibres.append(frameVictima)

        # Devolvemos el número del frame liberado
        return frameVictima

    def releaseFrames(self, lista):
        for frame in lista:
            # Eliminamos la referencia de uso si existe
            self._framesUsados.pop(frame, None)
            # Lo quitamos del selector de víctimas
            self._victimSelector.removeFrame(frame)
            # Lo agregamos a los libres
            if frame not in self._framesLibres:
                self._framesLibres.append(frame)


#############
class FileSystem:
    def __init__(self):
        self._disco = dict()

    @property
    def disco(self):
        return self._disco

    def write(self,path,instructions):
        self._disco[path] = instructions
    
    def read(self, path):
        return self._disco.get(path)



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

    def __init__(self,kernel):
        self._kernel = kernel
        self._baseDir = 0

    @property
    def kernel(self):
        return self._kernel

    def load(self, pcb):
        pcbACargar = self.kernel.fileSystem.read(pcb.path)
        log.logger.info(pcbACargar.instructions)
        frameSize = HARDWARE.mmu.frameSize
        progSize = len(pcbACargar.instructions)
        paginas = (progSize + frameSize - 1) // frameSize
        #framesParaUsar = self.kernel.memoryManager.alocFrames(paginas)
        pageTable = dict()
        #  no tiene que cargar ninguna pagina y lanza un pageFault
        for pag in range(paginas):
            pageTable[pag] = None
        
        # for index,inst in enumerate(pcbACargar.instructions):
        #     pagina = index // frameSize                     
        #     desplazamiento = index % frameSize              
        #     frame = pageTable[pagina] 
        #     log.logger.info(frame)
        #     dirFisica = frame * frameSize + desplazamiento
        #     HARDWARE.memory.write(dirFisica, inst)
        # Retornamos la tabla de páginas "virtual"
        return pageTable 

## DISPATCHER
class Dispatcher():

    def __init__(self,kernel):
        self._kernel = kernel
    
    @property
    def kernel(self):
        return self._kernel

    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc 
        HARDWARE.mmu.resetTLB()
        for page, value in pcb.pageTable.items():
            if value is not None:
                frame = value[0]       
                HARDWARE.mmu.setPageFrame(page,frame) 
            else:
                HARDWARE.mmu.setPageFrame(page,None)
        self.kernel.runningPCB = pcb
        HARDWARE.timer.reset() 
   
    def save(self, pcb):
        pcb.pc = HARDWARE.cpu.pc 
        self.kernel.runningPCB = None
        HARDWARE.cpu.pc = -1


## PCB
class PCB:
    _pidCount = 0
    def __init__(self, processName, prioridad = None):
        PCB._pidCount += 1
        self._pid = PCB._pidCount
        self._pc = 0
        self._state = "Ready"
        self._path = processName
        self._priority = prioridad
        self._priorityTemp = self._priority
        self._pageTable = dict()

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

    @property
    def pageTable(self):
        return self._pageTable

    @property
    def path(self):
        return self._path

    def setPageTable(self,table):
        self._pageTable = table
        
        
    def __repr__(self):
        return "pid: {pid} pc: {pc} estado: {estado} nombreProceso: {nombre} prioridad: {prioridad} prioridadTemporal: {prioTemp} pageTable: {pageTable}\n ".format(pid=self._pid, pc=self._pc,estado=self._state, nombre=self._path, prioridad = self._priority, prioTemp = self._priorityTemp, pageTable = self._pageTable)
       

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

class schedulerFCFS:
    def __init__(self):
        self.readyQueue = []
        self._name = 'FCFS'

    @property
    def name(self):
        return self._name

    def add (self,pcb): ##agrega un pcb a la readyQueue
        self.readyQueue.append(pcb)

    def isEmpty(self): ## retorna si la readyqueue esta vacia o no
        return len(self.readyQueue) == 0

    def getNextPcb(self): # Si la readyQueuee sta vacia retorna none sino devuelve el primero de la readyQueue
        if self.isEmpty():
            return None
        else:
            return self.readyQueue.pop(0)
    
    def checkTick(self):
        # el scheduler FCFS no hace nada 
        pass

    ##para no romper si cambio de scheduler
    def mustExpropiate(self,PCBenPC,PCBParaAgregar):
        return False



class schedulerRR:
    def __init__(self,quantum):
        self.readyQueue = []
        self._quantum = quantum
        HARDWARE.timer.quantum = quantum #seteo el quantum para el schedule RoundRobin
        self._name = 'RR'

    @property
    def name(self):
        return self._name

    @property
    def quantum(self):
        return self._quantum     

    def add (self,pcb): ##agrega un pcb a la readyQueue
        self.readyQueue.append(pcb)

    def isEmpty(self): ## retorna si la readyqueue esta vacia o no
        return len(self.readyQueue) == 0

    def getNextPcb(self): # Si la readyQueuee esta vacia retorna none sino devuelve el primero de la readyQueue
        if self.isEmpty():
            return None
        else:
            return self.readyQueue.pop(0)

    def checkTick(self):
        # el scheduler RR no hace nada en cada tick
        pass

    ##para no romper si cambio de scheduler
    def mustExpropiate(self,PCBenPC,PCBParaAgregar):
        return False


class schedulerPrioEx:
    def __init__(self):
        self.readyQueue = []
        self._tickParaAging = 5 #cada cuanto ticks se realiza el aging 
        HARDWARE.cpu.enable_stats = True
        self._name = 'PrEx'

    @property
    def name(self):
        return self._name


    def add (self,pcb): ##agrega un pcb a la readyQueue
        self.readyQueue.append(pcb)

    def isEmpty(self): ## retorna si la readyqueue esta vacia o no
        return len(self.readyQueue) == 0

    def getNextPcb(self): # Si la readyQueuee sta vacia retorna none sino devuelve el primero de la readyQueue
        if self.isEmpty():
            return None
        else:
            return self.pcbConMayorPrioridad()

    def checkTick(self):    
        if self._tickParaAging == 0:
            log.logger.info("Se realizo aging")
            log.logger.info(f"prioridades despues del aging: {self.readyQueue}")
            self._tickParaAging = 5
            for pcb in self.readyQueue:
                self.aumentarPrio(pcb)
        else:
            self._tickParaAging -= 1    


           
    def pcbConMayorPrioridad(self):
        pcbConMasPrioridad = self.readyQueue[0]
        for pcb in self.readyQueue[1:]:
            if pcb.priorityTemp < pcbConMasPrioridad.priorityTemp:  
                pcbConMasPrioridad = pcb

        self.readyQueue.remove(pcbConMasPrioridad)
        return pcbConMasPrioridad

    def aumentarPrio(self,pcb):
        if pcb.priorityTemp >= 0:
            pcb._priorityTemp -= 1


    def mustExpropiate(self,PCBenPC,PCBParaAgregar):
        return PCBParaAgregar.priority < PCBenPC.priority 





class schedulerPrioNoEx:
    def __init__(self):
        self.readyQueue = []
        self._tickParaAging = 5
        HARDWARE.cpu.enable_stats = True
        self._name = 'PrNEx'

    @property
    def name(self):
        return self._name
        
        
    def add (self,pcb): ##agrega un pcb a la readyQueue
        self.readyQueue.append(pcb)

    def isEmpty(self): ## retorna si la readyqueue esta vacia o no
        return len(self.readyQueue) == 0
 
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

    ##para no romper si cambio de scheduler
    def mustExpropiate(self,PCBenPC,PCBParaAgregar):
        return False



###  Algoritmo de seleccion de victima
class FifoVictimSelector:

    def __init__(self):
        self._queue = []  

    def addFrame(self, frame):
        if frame not in self._queue:
            self._queue.append(frame)

    def removeFrame(self, frame):
        if frame in self._queue:
            self._queue.remove(frame)

    def selectVictim(self):
        if len(self._queue) == 0:
            return None
        victim = self._queue[0]
        self._queue = self._queue[1:]
        return victim




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
        
        pageFaultHandler = PageFaultInterruptionHandler(self)
        HARDWARE.interruptVector.register(PAGE_FAULT_INTERRUPTION_TYPE, pageFaultHandler)
        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)
        self._loader = Loader(self)
        self._pcbTable = PCBTable()
        self._scheduler = schedulerFCFS()
        self._runningPCB = None
        self._dispatcher = Dispatcher(self)
        self._diagrama = DiagramGant(self)
        self._fileSystem = FileSystem()
        self._memoryManager = MemoryManager(4,self)
        HARDWARE.cpu.enable_stats = True
        ##para ver totalidad de frames
        log.logger.info(self._memoryManager.framesLibres)
        self.pageFaultCount = 0 # para saber cuantos fallos hubo
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
    
    @property
    def fileSystem(self):
        return self._fileSystem
    
    @property
    def memoryManager(self):
        return self._memoryManager
    
    
    @runningPCB.setter
    def runningPCB(self,pcb):
        self._runningPCB = pcb

    ## emulates a "system call" for programs execution
    def run(self, path,priority = None):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, [path, priority])
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
        return "Kernel"
