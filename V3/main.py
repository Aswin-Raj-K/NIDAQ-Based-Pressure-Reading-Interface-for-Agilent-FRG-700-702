import os
import sys
import pandas as pd
from PyQt5.QtGui import QIcon, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLineEdit, QLabel, QFrame, \
    QButtonGroup, QRadioButton, QHBoxLayout, QComboBox, QMessageBox, QFileDialog
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

DEBUG = False

class AnalogInStream(nidaqmx.Task):

    def __init__(self, deviceID, nr_samples):
        super().__init__()
        self.ai_channels.add_ai_voltage_chan(deviceID + "/ai0")
        self.reader = AnalogMultiChannelReader(self.in_stream)

        self.nr_channels = 1
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
            return np.random.randint(1,11)
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

    def setSamplingAndReadRate(self, samplingRate, readRate):
        self.samplingRate = samplingRate
        self.nr_samples = int(readRate * self.samplingRate)

    def setDeviceID(self,deviceID):
        self.deviceID = deviceID

    def run(self):
        print("Run")
        if DEBUG:
            self.isRunning = True
            while self.isRunning:
                data = np.random.randint(1,11)
                self.data_ready.emit(np.array([data]))
                self.delay(500)
        else:
            try:
                with AnalogInStream(self.deviceID, self.nr_samples) as self.reader:
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
    def __init__(self,parent):
        super().__init__(parent)

        self.setWindowTitle("Pressure Graph")
        self.setGeometry(100, 100, 800, 600)

        # Create a central widget and set the layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        # Create a plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("Pressure", color="black", size="15pt")

        self.layout.addWidget(self.plot_widget)

    def ylabel(self,ylabel):
        self.plot_widget.setLabel('left', ylabel, color='black', size='12pt')

    def xlabel(self, xlabel="Time (min)"):
        self.plot_widget.setLabel('bottom', xlabel, color='black', size='12pt')

    def plot_data(self, x=None, y=None):
        if x is None or y is None:
            x = np.linspace(0, 10, 100)
            y = np.sin(x)

        # Plot the data
        self.plot_widget.plot(x, y, pen=pg.mkPen(color='r', width=2), symbol='o', symbolSize=8, symbolBrush=pg.mkBrush('r'))

    def clearGraph(self):
        self.plot_widget.clear()

    def closeEvent(self, event):
        if hasattr(self.parent(),"onGraphClosed"):
            self.parent().onGraphClosed()
        super().closeEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pressure = []
        self.timeElapsed = 0
        self.dataRecordRate = 1  #Default
        self.graph_window = None
        self.setWindowTitle("Pressure Reader")
        self.setGeometry(100, 100, 300, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        self.setWindowIcon(QIcon(os.path.join(basedir, "icon.png")))

        instruction_text = "<span style='font-size: 10pt;'><b>Instructions</b><br>Connect AIO of NIDAQ to Signal Pin (Pin 3).<br>Data acquire time should be a factor of recording interval. <br> Changing the unit while running will corrupt the recorded data."
        self.instruction = QLabel(instruction_text, self)

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

        self.sampling_rate_label = QLabel("Sampling Rate (Hz)", self)
        self.sampling_rate_edit = QLineEdit(self)
        self.sampling_rate_edit.setText("40000")
        self.sampling_rate_edit.setPlaceholderText("Enter Sampling Rate")
        self.sampling_rate_edit.setValidator(QIntValidator())

        self.data_fetch_rate_label = QLabel("Data Acquire Time (s)", self)
        self.data_fetch_rate_edit = QLineEdit(self)
        self.data_fetch_rate_edit.setText("0.5")
        self.data_fetch_rate_edit.setPlaceholderText("Enter data acquire time")
        self.data_fetch_rate_edit.setValidator(QDoubleValidator())

        self.data_record_rate_label = QLabel("Data Recording Interval (min)", self)
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

        self.current_pressure_label = QLabel("Pressure", self)
        resultFont = self.current_pressure_label.font()
        resultFont.setPointSize(10)
        self.current_pressure_label.setFont(resultFont)
        self.current_pressure_value_label = QLabel("", self)
        self.current_pressure_value_label.setFont(resultFont)

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
        self.device_dropdown = QComboBox(self)
        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.clicked.connect(self.refresh_devices)

        layout = QVBoxLayout()
        layout.addWidget(self.instruction)
        layout.addSpacing(10)
        layout.addWidget(self.separator1)
        layout.addSpacing(10)
        layout.addWidget(self.device_label)
        layout.addWidget(self.device_dropdown)
        layout.addWidget(self.refresh_button)
        layout.addSpacing(10)
        layout.addWidget(self.separator3)
        layout.addSpacing(10)
        layout.addWidget(self.sampling_rate_label)
        layout.addWidget(self.sampling_rate_edit)
        layout.addSpacing(10)
        layout.addWidget(self.data_fetch_rate_label)
        layout.addWidget(self.data_fetch_rate_edit)
        layout.addSpacing(10)
        layout.addWidget(self.data_record_rate_label)
        layout.addWidget(self.data_record_rate_edit)
        layout.addLayout(hlayout)

        buttonLayoutTop = QHBoxLayout()
        buttonLayoutBottom = QHBoxLayout()
        buttonLayoutTop.addWidget(self.start_button)
        buttonLayoutTop.addWidget(self.stop_button)
        buttonLayoutBottom.addWidget(self.plot_button)
        buttonLayoutBottom.addWidget(self.export_button)

        layout.addLayout(buttonLayoutTop)
        layout.addLayout(buttonLayoutBottom)
        layout.addSpacing(10)
        layout.addWidget(self.separator2)
        layout.addSpacing(10)

        layout.addWidget(self.current_pressure_label)
        layout.addWidget(self.current_pressure_value_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.reader_thread = QThread()
        self.reader = Reader()
        self.reader.moveToThread(self.reader_thread)
        self.reader_thread.started.connect(self.reader.run)
        self.reader.data_ready.connect(self.updateUI)
        self.reader.error_occurred.connect(self.errorHandler)

        QTimer.singleShot(1000, self.done)
        self.refresh_devices()  # Initial device refresh

    def checkData(self):
        if (self.dataRecordRate * 60) % self.readRate !=0:
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
            self.current_pressure_value_label.setEnabled(enable)
            self.current_pressure_label.setEnabled(enable)
            self.export_button.setEnabled(enable)
            self.plot_button.setEnabled(enable)


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



        self.pressure = []
        if self.graph_window is not None:
            self.graph_window.clearGraph()

        if not self.reader_thread.isRunning():
            deviceID = self.device_dropdown.currentText()
            print("Sampling Rate:", self.samplingRate)
            print("Read Rate:", self.readRate)
            self.reader.setDeviceID(deviceID)
            self.reader.setSamplingAndReadRate(self.samplingRate, self.readRate)
            self.reader_thread.start()
        self.stop_button.setEnabled(True)

    def plotClicked(self):
        print("Plot Clicked")
        self.graph_window = GraphWindow(self)
        t = [i * self.dataRecordRate for i in range(1,len(self.pressure)+1)]
        # Plot some example data'
        print(self.pressure)
        self.graph_window.plot_data(t,self.pressure)
        self.graph_window.xlabel()

        self.graph_window.ylabel("Pressure (" + self.getCurrentPressureUnit() + ")")
        self.graph_window.show()
        self.plot_button.setEnabled(False)


    def exportClicked(self):
        self.saveData()

    def updateUI(self, data):
        pressure = data[0]
        if not DEBUG:
            pressure = self.calculatePressure(data)
        self.current_pressure_value_label.setText(str(pressure))
        self.timeElapsed += self.readRate
        if (self.dataRecordRate * 60)/self.timeElapsed < 1:
            print("Data Recorded")
            self.timeElapsed = 0
            self.pressure.append(pressure)
            if self.graph_window is not None:
                t = [i * self.dataRecordRate for i in range(1,len(self.pressure)+1)]
                # Plot some example data'
                print(self.pressure)
                self.graph_window.clearGraph()
                self.graph_window.plotData(t, self.pressure)


    def done(self):
        # Lock the window size
        self.setFixedSize(self.size())

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
        t = [i * self.dataRecordRate for i in range(1,len(self.pressure)+1)]
        data = pd.DataFrame({'Time (min)': t, "Pressure (" + self.getCurrentPressureUnit() + ")": self.pressure})

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
