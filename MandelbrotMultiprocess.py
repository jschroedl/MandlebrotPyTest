import sys, random, math, time, os, threading

from multiprocessing import Array, Pool, cpu_count, Process, Value, sharedctypes
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor
import mymodule

xMin = -3
xMax = 3
yMin = -3
yMax = 3
zoomLevel = 4
pointsReady = False

class GuiApp(QWidget):
    oldWindowSize = 0

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        #This code determines what the base window will look like
        self.setGeometry(0, 0, 1000, 1000)    #300, 190
        self.setWindowTitle('Mandelbrot')
        self.show()
        #self.showFullScreen()

    #Called whenever the window is resized or brought into focus
    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        self.drawMandelbrot(qp)
        qp.end()
    
    def mousePressEvent(self, event):
        global xMin
        global xMax
        global yMin
        global yMax
        
        size = self.size()
        windowWidth = size.width()
        windowHeight = size.height()

        xMouse = event.x()
        yMouse = event.y()

        #print("xMouse: ", xMouse)
        #print("yMouse: ", yMouse)
        #print("Before Map - xMin: ", xMin)
        #print("Before Map - yMin: ", yMin)
        #print("Before Map - xMax: ", xMax)
        #print("Before Map - yMax: ", yMax)

        xMouse = linearMap(xMouse, 0, windowWidth, xMin, xMax)
        yMouse = linearMap(yMouse, 0, windowHeight, yMax, yMin)

        #print("xMouse: ", xMouse)
        #print("yMouse: ", yMouse)

        #Make temporary variables to store the new x/y min/max so they aren't changed while the algorithms are still working
        xMinTemp = xMouse - ((xMax - xMin) / (zoomLevel * zoomLevel))
        xMaxTemp = xMouse + ((xMax - xMin) / (zoomLevel * zoomLevel))
        yMinTemp = yMouse - ((yMax - yMin) / (zoomLevel * zoomLevel))
        yMaxTemp = yMouse + ((yMax - yMin) / (zoomLevel * zoomLevel))

        xMin = xMinTemp
        xMax = xMaxTemp
        yMin = yMinTemp
        yMax = yMaxTemp

        #Update scale for the new zoomed in view
        #widthScale = widthScale / ((zoomLevel * zoomLevel) / 1.5)
        #heightScale = heightScale / ((zoomLevel * zoomLevel) / 1.5)

        widthScale = (xMax - xMin) / size.width()
        heightScale = (yMax - yMin) / size.height()

        runMultiprocessing(self)

    def drawMandelbrot(self, qp):
        size = self.size()
        
        if pointsReady is True:
            
            numCols = size.width()
            numRows = size.height()

            colorIndex = 0
            for row in range(0, numRows):
                for col in range(0, numCols):

                    color = mymodule.arr[colorIndex]
                    colorIndex += 1

                    #The calculateMandelbrot will set color to -1 if the iterations are infinite else set the color based on iterations
                    if color != -1:
                        qp.setPen(QColor.fromHsv(color, 255, 255))
                    else:
                        qp.setPen(Qt.black)

                    #draw the point on the canvas
                    qp.drawPoint(col, row)
        else:
            #qp.setPen(Qt.gray)
            qp.fillRect(0, 0, size.width(), size.height(), Qt.gray)
        
#Custom version of the range function that works with float numbers
def frange(start, stop, step):
    i = start
    while i < stop:
        yield i
        i += step

def linearMap(value, low, high, newLow, newHigh):
    return newLow + ((value - low) / (high - low)) * (newHigh - newLow)

def mandelbrotCalculate(startRow, endRow, size, widthScale, heightScale, i):
        maxIteration = 255

        numRows = int(endRow - startRow)
        numCols = int(size.width())

        print("Process {0} started. startPixel={1} endPixel={2} numRows={3} numCols={4}".format(i, startRow, endRow, numRows, numCols))

        colorIndex = int(startRow * numCols)
        for row in range(int(startRow), int(endRow)):
            for col in range(0, numCols):
                w = xMin + (col * widthScale)
                h = yMin + (row * heightScale)

                x = 0
                y = 0
                iteration = 0

                while (x*x + y*y <= 4) and (iteration < maxIteration):
                    xtemp = (x*x - y*y) + w
                    y = ((2*x) * y) + h
                    x = xtemp
                    iteration += 1
            
                if iteration != maxIteration:
                    mymodule.arr[colorIndex] = iteration
                else:
                    mymodule.arr[colorIndex] = -1 

                # Move to the next pixel     
                colorIndex += 1

        print("Process {0} ended.".format(i))

def initProcess(share):
  mymodule.arr = share

def runMultiprocessing(guiApp):
    size = guiApp.size()
    global pointsReady
    pointsReady = False

    arr = Array('i', range(size.width() * size.height()), lock=False)
    initProcess(arr)

    #numberOfThreads = os.cpu_count()
    numberOfThreads = 4
    print("Running with ", numberOfThreads, " number of threads.")

    #Create a pool of numberOfThreads many workers
    pool = Pool(processes=numberOfThreads, initializer=initProcess, initargs=(arr,))

    pieceHeight = size.height() / numberOfThreads

    widthScale = (xMax - xMin) / size.width()
    heightScale = (yMax - yMin) / size.height()

    time1 = time.time()

    multipleResults = []

    # The screen size is probably not a multiple of the
    # number of threads. The last thread will handle
    # the extra columns 
    extraRows = size.height() % numberOfThreads

    for i in range(numberOfThreads):
        startRow = pieceHeight * i
        endRow = pieceHeight * (i+1)  # exclusive

        if i == numberOfThreads:
            endRow += extraRows

        multipleResults.append(pool.apply_async(mandelbrotCalculate, args = (startRow, endRow, size, widthScale, heightScale, i)))
    
    print("Waiting for results")

    for result in multipleResults:
        result.get()

    pool.close()
    pool.join()

    pointsReady = True

    #for p in threadPool:
    #    p.join()
    
    time2 = time.time()
    print('computation took %0.3f ms' % ((time2-time1)*1000.0))

    guiApp.repaint()

if __name__ == '__main__':
    app = QApplication([])
    guiApp = GuiApp()
    runMultiprocessing(guiApp)
    app.exec_()