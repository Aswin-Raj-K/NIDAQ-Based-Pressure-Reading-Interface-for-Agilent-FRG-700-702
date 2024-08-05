import os
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLineEdit, QLabel, QFrame, \
    QButtonGroup, QRadioButton, QHBoxLayout, QComboBox, QMessageBox, QSizePolicy
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer, Qt
import nidaqmx
import time
import nidaqmx
from nidaqmx.constants import * #(AcquisitionType)
from nidaqmx.stream_readers import (
    AnalogMultiChannelReader)
import numpy as np
from nidaqmx.system import System

basedir = os.path.dirname(__file__)


class AnalogInStream(nidaqmx.Task):

    def __init__(self, deviceID, nr_samples):
        super().__init__()
        self.ai_channels.add_ai_voltage_chan(deviceID+ "/ai0")
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
        if self.reader:
            self.reader.stop()
            self.reader.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pressure Reader")
        self.setGeometry(100, 100, 300, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        self.setWindowIcon(QIcon(os.path.join(basedir, "icon.png")))

        instruction_text = "<span style='font-size: 10pt;'><b>Instructions</b><br>Connect AIO of NIDAQ to Signal Pin (Pin 3)"
        self.instruction = QLabel(instruction_text, self)

        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.startClicked)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stopClicked)
        self.stop_button.setEnabled(False)

        self.sampling_rate_label = QLabel("Sampling Rate (Hz)", self)
        self.sampling_rate_edit = QLineEdit(self)
        self.sampling_rate_edit.setText("40000")
        self.sampling_rate_edit.setPlaceholderText("Enter Sampling Rate")

        self.data_fetch_rate_label = QLabel("Data Acquire Rate (s)", self)
        self.data_fetch_rate_edit = QLineEdit(self)
        self.data_fetch_rate_edit.setText("0.5")
        self.data_fetch_rate_edit.setPlaceholderText("Enter Samples Per Channel")

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
        layout.addLayout(hlayout)

        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
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
        self.stop_button.setEnabled(enable)

    def stopClicked(self):
        print("Stop Clicked")
        self.reader.stop()
        self.reader_thread.quit()
        self.reader_thread.wait()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.sampling_rate_edit.setEnabled(True)
        self.data_fetch_rate_edit.setEnabled(True)
        self.device_dropdown.setEnabled(True)
        self.device_label.setEnabled(True)
        self.refresh_button.setEnabled(True)

    def startClicked(self):
        print("Start Clicked")
        if not self.refresh_devices():
            return 0

        self.start_button.setEnabled(False)
        self.sampling_rate_edit.setEnabled(False)
        self.data_fetch_rate_edit.setEnabled(False)
        self.device_dropdown.setEnabled(False)
        self.device_label.setEnabled(False)
        self.refresh_button.setEnabled(False)


        if not self.reader_thread.isRunning():
            self.samplingRate = int(self.sampling_rate_edit.text())
            self.readRate = float(self.data_fetch_rate_edit.text())
            deviceID = self.device_dropdown.currentText()
            print("Sampling Rate:", self.samplingRate)
            print("Read Rate:", self.readRate)
            self.reader.setDeviceID(deviceID)
            self.reader.setSamplingAndReadRate(self.samplingRate, self.readRate)
            self.reader_thread.start()
        self.stop_button.setEnabled(True)

    def updateUI(self, data):
        self.current_pressure_value_label.setText(str(self.calculatePressure(data)))

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
