# 🖥️ Sistemas Operativos - UNQ

Repositorio de trabajos prácticos de la materia **Sistemas Operativos** de la **Universidad Nacional de Quilmes (UNQ)**.

Este proyecto consiste en la construcción incremental de un **simulador de sistema operativo**, desarrollando los principales mecanismos de gestión de procesos, CPU y memoria.

---

## 🚀 Objetivo del proyecto

El objetivo principal fue **comprender cómo funciona internamente un sistema operativo**, llevando conceptos teóricos a implementaciones concretas mediante:

* Gestión de procesos
* Planificación de CPU
* Administración de memoria
* Memoria virtual (paginación bajo demanda y reemplazo de páginas)

Todo esto construido sobre un **emulador base de hardware y SO**, evolucionado progresivamente en cada trabajo práctico.

---

## 🧠 Conceptos clave aprendidos

### ⚙️ Sistemas Operativos

* Abstracción del hardware
* Gestión de recursos (CPU, memoria, I/O)
* System Calls
* Estructura del sistema operativo

---

### 🧵 Procesos y Concurrencia

* Procesos y estados
* PCB (Process Control Block)
* Multiprogramación
* Manejo de interrupciones (IRQ)

---

### 📊 Planificación de CPU

* Algoritmos de scheduling:

  * FIFO
  * Round Robin
  * Preemptive y Non-Preemptive 
* Métricas:

  * Uso de CPU
  * Tiempo de respuesta
  * TurnAround

---

### 🧮 Administración de Memoria

* Particionamiento fijo y variable
* Uso eficiente de memoria física
* Introducción a paginación

---

### 💿 Memoria Virtual

* Paginación
* **Paginación bajo demanda**
* **Algoritmos de reemplazo de páginas** (FIFO, LRU, Óptimo)
* Manejo de fallos de página (page faults)
* Bases del problema de thrashing

---

## 🛠️ Trabajo práctico (enfoque aplicado)

El proyecto se desarrolló de forma incremental:

### 🧪 TP1 - Introducción al sistema

* Análisis del emulador base
* CPU, memoria e interrupciones
* Funcionamiento del kernel

---

### 📦 TP2 - Sistemas Batch

* Ejecución de procesos por lote
* Modelo secuencial

---

### 🔄 TP3 - Procesos y PCB

* Estructuras de procesos
* Manejo de IRQ
* Multiprogramación

---

### ⏱️ TP4 - Planificación de CPU

* Implementación de algoritmos de scheduling
* Simulación de asignación de CPU

---

### 🧮 TP5 - Administración de memoria

* Manejo de memoria física
* Esquemas de particionamiento

---

### 💿 TP6 - Memoria virtual

* Implementación de **paginación**
* **Paginación bajo demanda**
* Manejo de **page faults**
* Implementación de **algoritmos de reemplazo de páginas**

---

## 🧩 Tecnologías utilizadas

* 🐍 Python (simulación del sistema operativo)
* 🖥️ Emulador de hardware educativo
* 🐧 Conceptos basados en sistemas tipo Unix/Linux

---

## 📚 Relación con la teoría

Este proyecto implementa en la práctica los contenidos centrales de la materia:

* Gestión y planificación de procesos
* Administración de memoria
* Memoria virtual (incluyendo demanda y reemplazo)

Cada componente desarrollado refleja directamente los conceptos teóricos trabajados en clase.

---

## 🎯 Resultados y aprendizaje

Este trabajo permitió:

* Entender cómo interactúan los componentes internos de un SO
* Implementar mecanismos reales de:

  * Planificación de CPU
  * Multiprogramación
  * Memoria virtual
* Modelar problemas complejos como:
  * Page faults
  * Reemplazo de páginas

---

## 📖 Estructura del repositorio

```
SistemasOperativos/
├── TP1/          # Introducción al emulador
├── TP2/          # Sistemas Batch
├── TP3/          # Procesos y PCB
├── TP4/          # Planificación de CPU
├── TP5/          # Administración de memoria
├── TP6/          # Memoria virtual
└── README.md     # Este archivo
```

---

## 🔍 Algoritmos implementados

### Planificación de CPU

| Algoritmo | Descripción | Ventajas | Desventajas |
|-----------|-------------|----------|------------|
| **FIFO** | First In First Out | Simple | Efecto convoy |
| **Round Robin** | Quantum de tiempo | Equitativo | Overhead de context switch |
| **SJF** | Shortest Job First | Minimiza tiempo medio | Inanición |

### Reemplazo de páginas

| Algoritmo | Estrategia | Costo |
|-----------|-----------|-------|
| **FIFO** | Reemplaza página más antigua | Bajo |
| **LRU** | Reemplaza página menos usada recientemente | Alto |
| **Óptimo** | Reemplaza página usada más lejanamente | Teórico |

---

## 💡 Casos de estudio

Se implementaron y analizaron casos de estudio que demostraron:

* **Efecto convoy**: Impacto de procesos largos en FIFO
* **Context switching**: Overhead en Round Robin
* **Thrashing**: Problema de reemplazo excesivo de páginas
* **Inanición**: En algoritmos no equitativos

---

## 🚦 Métricas de evaluación

Durante el desarrollo se midieron y optimizaron:

* ⏱️ **Tiempo de respuesta**: Latencia desde la solicitud hasta la respuesta
* 📊 **Utilización de CPU**: Porcentaje de tiempo útil vs ocioso
* 🔄 **Turnover time**: Tiempo total de ejecución de un proceso
* 💾 **Page faults**: Cantidad de accesos a memoria secundaria
* ⚖️ **Fairness**: Equidad en la asignación de recursos

---

## 🔑 Aprendizajes clave

1. **Comprensión profunda del kernel**: Cómo el SO actúa como intermediario entre hardware y aplicaciones
2. **Tradeoffs de diseño**: Cada algoritmo presenta compromisos entre rendimiento, complejidad y equidad
3. **Simulación como herramienta**: La modelación permite entender comportamientos complejos sin hardware real
4. **Importancia de las estructuras de datos**: Colas, tablas de páginas y PCBs son fundamentales
5. **Debugging en concurrencia**: Herramientas y técnicas para identificar problemas en sistemas multiprogramados

---

## 📝 Notas de implementación

* El simulador fue desarrollado iterativamente, agregando complejidad en cada TP
* Se priorizó la claridad del código sobre la optimización
* Se incluyeron comentarios extensos para facilitar la comprensión
* Las estructuras siguen convenciones de sistemas operativos reales


## ⚖️ Licencia

Este proyecto es con fines educativos.

**Última actualización**: Marzo 2026