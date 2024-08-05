import os
import sys
import pandas as pd
from PyQt5.QtGui import QIcon, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLineEdit, QLabel, QFrame, \
    QButtonGroup, QRadioButton, QHBoxLayout, QComboBox, QMessageBox, QFileDialog, QSizePolicy, QAction, QSplitter, \
    QMenuBar
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer, Qt, QEventLoop
import nidaqmx
import time
import nidaqmx
from nidaqmx.constants import * #(AcquisitionType)
from nidaqmx.stream_readers import (
    AnalogMultiChannelReader)
import numpy as np
from nidaqmx.system import System
import pyqtgraph as pg

basedir = os.path.dirname(__file__)

DEBUG = True

class AnalogInStream(nidaqmx.Task):

    def __init__(self, deviceID, nr_samples, nr_channels):
        super().__init__()
        self.ai_channels.add_ai_voltage_chan(deviceID + "/ai0")
        self.reader = AnalogMultiChannelReader(self.in_stream)

        self.nr_channels = nr_channels
        self.nr_samples = int(nr_samples)

        # Creating the buffer
        self.acq_data = np.zeros((self.nr_channels, self.nr_samples), dtype=np.float64)

    def configureClock(self, sample_rate):
        try:
            self.timing.cfg_samp_clk_timing(int(sample_rate), sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=self.nr_samples * 50)
        except NameError:
            print("Name Error")

    def acquire_data(self):
        print("Acquire Data")

        if DEBUG:
            return [[np.random.randint(1,11)] for i in range(self.nr_channels)]

        try:
            if self.reader is not None:
                self.reader.read_many_sample(self.acq_data, number_of_samples_per_channel=self.nr_samples)
        except nidaqmx.errors.DaqError as e:
            raise RuntimeError("Failed to acquire data: " + str(e))

        return self.acq_data

    def close_task(self):
        print("Closing Task")
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_task()
        if exc_type is not None:
            raise

class Reader(QObject):
    data_ready = pyqtSignal(np.ndarray)  # Signal to emit the received data
    error_occurred = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.reader = None
        self.isRunning = False
        self.deviceID = None

    def setSamplingAndReadRate(self, samplingRate, readRate, nr_channels = 1):
        self.samplingRate = samplingRate
        self.nr_samples = int(readRate * self.samplingRate)
        self.nr_channels = nr_channels

    def setDeviceID(self,deviceID):
        self.deviceID = deviceID

    def run(self):
        print("Run")
        if DEBUG:
            self.isRunning = True
            while self.isRunning:
                data = [np.random.randint(1,11) for i in range(self.nr_channels)]
                self.data_ready.emit(np.array(data))
                self.delay(500)
        else:
            try:
                with AnalogInStream(self.deviceID, self.nr_samples, self.nr_channels) as self.reader:
                    self.reader.configureClock(self.samplingRate)
                    self.isRunning = True
                    while self.isRunning:
                        data = self.reader.acquire_data()
                        self.data_ready.emit(data)
            except RuntimeError as e:
                print(e)
                # self.stop()
                self.error_occurred.emit()


    def stop(self):
        print("Reader.Stop")
        self.isRunning = False
        if self.reader and not DEBUG:
            self.reader.stop()
            self.reader.close()

    def delay(self,delay):
        loop = QEventLoop()
        QTimer.singleShot(delay, loop.quit)
        loop.exec_()

class GraphWindow(QMainWindow):
    COLORS = ['r', 'b', 'g', 'y', 'o', 'k']
    STATUS_MERGED = 0
    STATUS_SPLIT = 1
    def __init__(self,parent):
        super().__init__(parent)
        self.plotStatus = GraphWindow.STATUS_MERGED
        self.setWindowTitle("Pressure Graph")
        self.setGeometry(100, 100, 800, 600)

        # Create a central widget and set the layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)

        # Create a menu bar
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        # Add a menu and action to split the graph
        self.view_menu = self.menu_bar.addMenu("View")
        self.split_action = QAction("Split", self)
        self.combine_action = QAction("Combine", self)
        self.split_action.triggered.connect(self.splitGraphs)
        self.combine_action.triggered.connect(self.combineGraphs)
        self.view_menu.addAction(self.split_action)
        self.view_menu.addAction(self.combine_action)

        # Create a layout for the plot widgets
        self.plot_layout = QVBoxLayout()
        self.main_layout.addLayout(self.plot_layout)

        # Create a plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("Pressure", color="black", size="12pt")
        self.plot_layout.addWidget(self.plot_widget)

        self.plot_widgets = [self.plot_widget]
        self.y_unit = "None"
        self.combine_action.setEnabled(False)

    def setYLabel(self,ylabel):
        self.y_unit = ylabel

    def updateYlabel(self,index = 0):
        self.plot_widgets[index].setLabel('left', self.y_unit, color='black', size='12pt')

    def xlabel(self, xlabel="Time (min)", index = 0):
        self.plot_widgets[index].setLabel('bottom', xlabel, color='black', size='12pt')

    def plotData(self, x=None, y=None, color ='r', index = 0, symbol='o', symbolSize=8):
        if x is None or y is None:
            x = np.linspace(0, 10, 100)
            y = np.sin(x)
        if len(self.plot_widgets)==1:
            index = 0
        # Plot the data
        self.plot_widgets[index].plot(x, y, pen=pg.mkPen(color=color, width=2), symbol=symbol, symbolSize=symbolSize, symbolBrush=pg.mkBrush(color))
        self.updateYlabel(index=index)
        self.xlabel()

    def addLegend(self):
        self.legend = pg.LegendItem((80, 60), offset=(30, 30))
        self.legend.setParentItem(self.plot_widgets[0].graphicsItem())
        if len(self.plot_widgets) == 1:
            for i,plot in enumerate(self.plot_widgets[0].getPlotItem().items):
                self.legend.addItem(plot,f"Senor AI{i}")


    def clearGraph(self):
        for plot in self.plot_widgets:
            plot.clear()

    def closeEvent(self, event):
        if hasattr(self.parent(),"onGraphClosed"):
            self.parent().onGraphClosed()
        super().closeEvent(event)

    def combineGraphs(self):
        for i in reversed(range(self.splitter.count())):
            self.splitter.widget(i).setParent(None)
        self.splitter.setParent(None)
        self.splitter = None

        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.setTitle(f"Pressure", color="black", size="12pt")
        plot_widgets = self.plot_widgets
        self.plot_widgets = [plot_widget]
        for i,plot in enumerate(plot_widgets):
            x, y = plot.getPlotItem().items[0].getData()
            self.plotData(x, y, GraphWindow.COLORS[i])

        self.plot_layout.addWidget(plot_widget)
        self.updateYlabel()
        self.xlabel()
        self.addLegend()
        self.split_action.setEnabled(True)
        self.combine_action.setEnabled(False)


    def splitGraphs(self):


        plot_widget = self.plot_widgets[0]
        plots = plot_widget.getPlotItem().items
        print(plots)

        self.splitter = QSplitter(Qt.Vertical)
        self.plot_widgets = []

        for i in range(len(plots)):
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('w')
            plot_widget.setTitle(f"Pressure (Sensor AI{i + 1})", color="black", size="12pt")

            self.splitter.addWidget(plot_widget)
            self.plot_widgets.append(plot_widget)
            x, y = plots[i].getData()
            self.plotData(x, y, GraphWindow.COLORS[i], i)
            self.updateYlabel(i)
            self.xlabel(index=i)


        for i in range(self.plot_layout.count()):
            self.plot_layout.itemAt(i).widget().setParent(None)
        self.plot_layout.addWidget(self.splitter)
        self.split_action.setEnabled(False)
        self.combine_action.setEnabled(True)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pressure = []
        self.currentDataUnit = "unit"
        self.timeElapsed = 0
        self.dataRecordRate = 1  #Default
        self.graph_window = None
        self.setWindowTitle("Pressure Reader")
        self.setGeometry(100, 100, 300, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        self.setWindowIcon(QIcon(os.path.join(basedir, "icon.png")))

        instruction_text = "<span style='font-size: 10pt;'><b>Instructions</b><br>Connect Signal pin of the senor to the NIDAQ AI.<br>Data acquire time should be a factor of recording interval. <br> Changing the unit while running will corrupt the recorded data."
        self.instruction = QLabel(instruction_text, self)
        self.instruction.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        # self.instruction.setStyleSheet("background-color: blue;")

        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.startClicked)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stopClicked)
        self.stop_button.setEnabled(False)

        self.plot_button = QPushButton("Plot Data", self)
        self.plot_button.clicked.connect(self.plotClicked)
        # self.plot_button.setEnabled(False)

        self.export_button = QPushButton("Export Data", self)
        self.export_button.clicked.connect(self.exportClicked)
        # self.export_button.setEnabled(False)

        self.add_sensor_button = QPushButton("Add Sensor", self)
        self.add_sensor_button.clicked.connect(self.addClicked)

        self.remove_sensor_button = QPushButton("Remove Sensor", self)
        self.remove_sensor_button.clicked.connect(self.removeClicked)
        self.remove_sensor_button.setEnabled(False)

        self.sampling_rate_label = QLabel("Sampling Rate (Hz)", self)
        self.sampling_rate_label.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.sampling_rate_edit = QLineEdit(self)
        self.sampling_rate_edit.setText("40000")
        self.sampling_rate_edit.setPlaceholderText("Enter Sampling Rate")
        self.sampling_rate_edit.setValidator(QIntValidator())

        self.data_fetch_rate_label = QLabel("Data Acquire Time (s)", self)
        self.data_fetch_rate_label.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.data_fetch_rate_edit = QLineEdit(self)
        self.data_fetch_rate_edit.setText("0.5")
        self.data_fetch_rate_edit.setPlaceholderText("Enter data acquire time")
        self.data_fetch_rate_edit.setValidator(QDoubleValidator())

        self.data_record_rate_label = QLabel("Data Recording Interval (min)", self)
        self.data_record_rate_label.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.data_record_rate_edit = QLineEdit(self)
        self.data_record_rate_edit.setText("3")
        self.data_record_rate_edit.setPlaceholderText("Enter data record interval")
        self.data_record_rate_edit.setValidator(QIntValidator())

        self.separator1 = QFrame(self)
        self.separator1.setFrameShape(QFrame.HLine)
        self.separator1.setFrameShadow(QFrame.Sunken)
        self.separator2 = QFrame(self)
        self.separator2.setFrameShape(QFrame.HLine)
        self.separator2.setFrameShadow(QFrame.Sunken)
        self.separator3 = QFrame(self)
        self.separator3.setFrameShape(QFrame.HLine)
        self.separator3.setFrameShadow(QFrame.Sunken)

        self.pressureSection = []
        self.pressureSection.append(self.addPressureSection())

        self.radio_mbar = QRadioButton("mbar", self)
        self.radio_torr = QRadioButton("torr", self)
        self.radio_pascal = QRadioButton("pascal", self)
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio_mbar, id=0)
        self.radio_group.addButton(self.radio_torr, id=1)
        self.radio_group.addButton(self.radio_pascal, id=2)
        self.radio_mbar.setChecked(True)  # Set default checked button

        hlayout = QHBoxLayout()
        hlayout.addStretch()
        hlayout.addWidget(self.radio_mbar)
        hlayout.addWidget(self.radio_torr)
        hlayout.addWidget(self.radio_pascal)
        hlayout.addStretch()
        hlayout.setContentsMargins(10, 10, 10, 10)  # Left, Top, Right, Bottom
        hlayout.setSpacing(20)  # Space between the radio buttons

        self.device_label = QLabel("Connected NIDAQ Devices:", self)
        self.device_label.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.device_dropdown = QComboBox(self)
        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.clicked.connect(self.refresh_devices)

        self.mainLayout = QVBoxLayout()

        self.mainLayout.addWidget(self.instruction)
        self.mainLayout.addSpacing(10)
        self.mainLayout.addWidget(self.separator1)
        self.mainLayout.addSpacing(10)
        self.mainLayout.addWidget(self.device_label)
        self.mainLayout.addWidget(self.device_dropdown)
        self.mainLayout.addWidget(self.refresh_button)
        self.mainLayout.addSpacing(10)
        self.mainLayout.addWidget(self.separator3)
        self.mainLayout.addSpacing(10)
        self.mainLayout.addWidget(self.sampling_rate_label)
        self.mainLayout.addWidget(self.sampling_rate_edit)
        self.mainLayout.addSpacing(10)
        self.mainLayout.addWidget(self.data_fetch_rate_label)
        self.mainLayout.addWidget(self.data_fetch_rate_edit)
        self.mainLayout.addSpacing(10)
        self.mainLayout.addWidget(self.data_record_rate_label)
        self.mainLayout.addWidget(self.data_record_rate_edit)
        self.mainLayout.addLayout(hlayout)



        buttonLayoutTop = QHBoxLayout()
        buttonLayoutMiddle = QHBoxLayout()
        buttonLayoutBottom = QHBoxLayout()
        buttonLayoutTop.addWidget(self.start_button)
        buttonLayoutTop.addWidget(self.stop_button)
        buttonLayoutMiddle.addWidget(self.plot_button)
        buttonLayoutMiddle.addWidget(self.export_button)
        buttonLayoutBottom.addWidget(self.add_sensor_button)
        buttonLayoutBottom.addWidget(self.remove_sensor_button)

        self.mainLayout.addLayout(buttonLayoutTop)
        self.mainLayout.addLayout(buttonLayoutMiddle)
        self.mainLayout.addLayout(buttonLayoutBottom)
        self.mainLayout.addSpacing(10)
        self.mainLayout.addWidget(self.separator2)
        self.mainLayout.addSpacing(10)

        # self.mainLayout.addLayout(self.pressureSectionLayout)
        self.updatePressureSection()




        self.container = QWidget()
        self.container.setLayout(self.mainLayout)
        self.setCentralWidget(self.container)
        # self.container.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)

        self.reader_thread = QThread()
        self.reader = Reader()
        self.reader.moveToThread(self.reader_thread)
        self.reader_thread.started.connect(self.reader.run)
        self.reader.data_ready.connect(self.updateUI)
        self.reader.error_occurred.connect(self.errorHandler)

        QTimer.singleShot(0, self.done)
        self.refresh_devices()  # Initial device refresh


        # self.setStyleSheet("background-color: lightblue;")

    def enableRadioButtons(self,enable):
        self.radio_mbar.setEnabled(enable)
        self.radio_pascal.setEnabled(enable)
        self.radio_torr.setEnabled(enable)


    def addPressureSection(self, port=0):
        pressureLabel = QLabel(f"Sensor {port + 1} Pressure (AI{port})", self)
        pressureLabel.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        resultFont = pressureLabel.font()
        resultFont.setPointSize(10)
        pressureLabel.setFont(resultFont)
        pressureValueLabel = QLabel("", self)
        pressureValueLabel.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        pressureValueLabel.setFont(resultFont)
        # pressureValueLabel.setStyleSheet("background-color: red;")
        # pressureLabel.setStyleSheet("background-color: orange;")
        return [pressureLabel, pressureValueLabel]

    def updatePressureSection(self):
        for i in self.pressureSection:
            self.mainLayout.addWidget(i[0])
            self.mainLayout.addWidget(i[1])

    def checkData(self):
        if (self.dataRecordRate * (60 if not DEBUG else 1)) % self.readRate !=0:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Invalid Inputs")
            msg_box.setInformativeText("Data acquire time should be a factor of recording interval.")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            return False
        return True

    def errorHandler(self):
        print("Error Handler")
        try:

            if self.reader_thread:
                self.reader_thread.quit()
                self.reader_thread.wait()

            msg_box = QMessageBox(self)
            # msg_box.setMinimumSize(400)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("An error occurred")
            msg_box.setInformativeText("NIDAQ Device Unexpectedly Removed!")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
            self.device_dropdown.setEnabled(True)
            self.device_label.setEnabled(True)
            self.refresh_button.setEnabled(True)
            self.refresh_devices()

        except Exception as e:
            print(e)


    def refresh_devices(self):
        print("Refresh Devices")
        system = System.local()
        devices = system.devices
        device_names = [device.name for device in devices]
        self.setEnabled(len(device_names)!=0)
        self.device_dropdown.clear()
        self.device_dropdown.addItems(device_names)

        return len(device_names)!=0

    def setEnabled(self, enable):
        if not DEBUG:
            self.data_record_rate_edit.setEnabled(enable)
            self.data_record_rate_label.setEnabled(enable)
            self.data_fetch_rate_edit.setEnabled(enable)
            self.data_fetch_rate_label.setEnabled(enable)
            self.sampling_rate_edit.setEnabled(enable)
            self.start_button.setEnabled(enable)
            self.sampling_rate_label.setEnabled(enable)
            self.radio_mbar.setEnabled(enable)
            self.radio_torr.setEnabled(enable)
            self.radio_pascal.setEnabled(enable)
            self.pressureValueLabel.setEnabled(enable)
            self.pressureLabel.setEnabled(enable)
            self.export_button.setEnabled(enable)
            self.plot_button.setEnabled(enable)
            self.add_sensor_button.setEnabled(enable)
            self.remove_sensor_button.setEnabled(enable)


    def stopClicked(self):
        print("Stop Clicked")
        self.reader.stop()
        self.reader_thread.quit()
        self.reader_thread.wait()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.sampling_rate_edit.setEnabled(True)
        self.data_record_rate_edit.setEnabled(True)
        self.data_fetch_rate_edit.setEnabled(True)
        self.device_dropdown.setEnabled(True)
        self.device_label.setEnabled(True)
        self.refresh_button.setEnabled(True)

        self.sampling_rate_label.setEnabled(True)
        self.data_record_rate_label.setEnabled(True)
        self.data_fetch_rate_label.setEnabled(True)

        self.add_sensor_button.setEnabled(True)
        self.remove_sensor_button.setEnabled(True)

        self.export_button.setEnabled(True)
        self.enableRadioButtons(True)


    def showWarning(self):
        reply = QMessageBox.question(self, 'Warning', 'Starting again will erase any previously stored data, Save before starting?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.exportClicked()
            return True

        return False

    def startClicked(self):
        print("Start Clicked")
        self.dataRecordRate = int(self.data_record_rate_edit.text())
        self.samplingRate = int(self.sampling_rate_edit.text())
        self.readRate = float(self.data_fetch_rate_edit.text())
        if (not self.refresh_devices() and not DEBUG) or not self.checkData():
            return 0

        if len(self.pressure) != 0:
            if self.showWarning():
                return 0



        self.start_button.setEnabled(False)
        self.sampling_rate_edit.setEnabled(False)
        self.data_fetch_rate_edit.setEnabled(False)
        self.data_record_rate_edit.setEnabled(False)
        self.device_dropdown.setEnabled(False)
        self.device_label.setEnabled(False)
        self.refresh_button.setEnabled(False)

        self.sampling_rate_label.setEnabled(False)
        self.data_record_rate_label.setEnabled(False)
        self.data_fetch_rate_label.setEnabled(False)
        self.add_sensor_button.setEnabled(False)
        self.remove_sensor_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.enableRadioButtons(False)


        self.pressure = [[] for i in range(len(self.pressureSection))]
        self.currentDataUnit = self.getCurrentPressureUnit()
        if self.graph_window is not None:
            self.graph_window.setYLabel("Pressure (" + self.currentDataUnit + ")")
            self.graph_window.clearGraph()

        if not self.reader_thread.isRunning():
            deviceID = self.device_dropdown.currentText()
            print("Sampling Rate:", self.samplingRate)
            print("Read Rate:", self.readRate)
            self.reader.setDeviceID(deviceID)
            self.reader.setSamplingAndReadRate(self.samplingRate, self.readRate, len(self.pressureSection))
            self.reader_thread.start()
        self.stop_button.setEnabled(True)

    def plotClicked(self):
        print("Plot Clicked")
        self.graph_window = GraphWindow(self)
        self.graph_window.setYLabel("Pressure (" + self.getCurrentPressureUnit() + ")")
        t = [i * self.dataRecordRate for i in range(1,len(self.pressure[0])+1)]
        for i,data in enumerate(self.pressure):
            self.graph_window.plotData(t, data, GraphWindow.COLORS[i])

        self.graph_window.addLegend()
        self.graph_window.show()
        self.plot_button.setEnabled(False)


    def exportClicked(self):
        self.saveData()

    def updateUI(self, data):
        pressureArray = []
        for i,j in enumerate(self.pressureSection):
            pressure = data[i] if DEBUG else self.calculatePressure(data[i])
            pressureArray.append(pressure)
            j[1].setText(str(pressure))

        self.timeElapsed += self.readRate
        if (self.dataRecordRate * 1 if DEBUG else 60)/self.timeElapsed < 1:
            print("Data Recorded")
            self.timeElapsed = 0

            for i,j in enumerate(pressureArray):
                self.pressure[i].append(j)

            if self.graph_window is not None:
                print(self.pressure)
                t = [i * self.dataRecordRate for i in range(1,len(self.pressure[0])+1)]
                # Plot some example data
                self.graph_window.clearGraph()
                for i,data in enumerate(self.pressure):
                    self.graph_window.plotData(t, data, GraphWindow.COLORS[i],i)


    def done(self):
        self.adjustSize()

    def calculatePressure(self, data):
        U = np.average(data[0])
        print(U)
        checked_button = self.radio_group.checkedButton()
        index = self.radio_group.id(checked_button)
        D = [11.33, 11.46, 9.333]
        d = D[index]
        avPressure = pow(10, 1.667 * U - d)
        return avPressure

    def getCurrentPressureUnit(self):
        checked_button = self.radio_group.checkedButton()
        index = self.radio_group.id(checked_button)
        D = ["mbar", "torr", "pascal"]
        return D[index]

    def saveData(self):
        # Create a DataFrame from the data
        t = [i * self.dataRecordRate for i in range(1,len(self.pressure[0])+1)]
        dataDict = {'Time (min)': t}
        print(self.pressure)
        for i,data in enumerate(self.pressure):
            dataDict[f"Pressure Sensor AI{i}({self.currentDataUnit}"] = data

        data = pd.DataFrame(dataDict)

        # Open file dialog to get save location and filename
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Data as Excel", "", "Excel Files (*.xlsx);;All Files (*)", options=options)

        if file_name:
            # Save the DataFrame to the specified Excel file
            data.to_excel(file_name, index=False)
            print(f"Data saved to {file_name}")

    def onGraphClosed(self):
        self.graph_window = None
        self.plot_button.setEnabled(True)

    def addClicked(self):
        totalSection = len(self.pressureSection)
        self.pressureSection.append(self.addPressureSection(totalSection))
        self.updatePressureSection()

        if totalSection > 0:
            self.remove_sensor_button.setEnabled(True)

    def removeClicked(self):
        if len(self.pressureSection) == 2:
            self.remove_sensor_button.setEnabled(False)

        item = self.pressureSection[-1]
        self.mainLayout.removeWidget(item[0])
        self.mainLayout.removeWidget(item[1])
        item[0].deleteLater()
        item[1].deleteLater()
        self.pressureSection.pop()
        QTimer.singleShot(0, self.done)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

#ToDo:
# ADD LEGEND
# SIMPLIFY PLOT DATA BY GIVING ALL THE DATA ONCE AS ARGUMENT
