import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import numpy as np

class GraphWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Data Graph")
        self.setGeometry(100, 100, 800, 600)

        # Create a central widget and set the layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        # Create a plot widget
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)
        self.plot_widget.setBackground('w')

        self.plot_widget.setTitle("Sine Wave", color="black", size="15pt")
        self.plot_widget.setLabel('left', 'Amplitude', color='black', size='12pt')
        self.plot_widget.setLabel('bottom', 'Time (s)', color='black', size='12pt')

        # Initialize data
        self.x = np.linspace(0, 10, 100)
        self.y = np.sin(self.x)

        # Plot the initial data
        self.plot_data()

        # Set up a QTimer to update the plot
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(1000)  # Update every 1000 ms (1 second)

    def plot_data(self):
        self.plot_widget.clear()  # Clear the plot before adding new data
        self.plot_widget.plot(self.x, self.y, pen=pg.mkPen(color='r', width=2), symbol='o', symbolSize=8, symbolBrush=pg.mkBrush('r'))

    def update_plot(self):
        # Add a new point
        new_x = self.x[-1] + 0.1
        new_y = np.sin(new_x)

        self.x = np.append(self.x, new_x)
        self.y = np.append(self.y, new_y)

        self.plot_data()

    def clear_graph(self):
        self.plot_widget.clear()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message', 'Are you sure you want to close the graph?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.timer.stop()
            self.clear_graph()  # Clear the graph when the window is closed
            self.parent().on_graph_window_closed()
            event.accept()
        else:
            event.ignore()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 400, 300)

        # Create a central widget and set the layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        # Create a button to show the graph
        self.button = QPushButton("Show Graph")
        self.button.clicked.connect(self.show_graph)
        self.layout.addWidget(self.button)

        # Create a button to clear the graph
        self.clear_button = QPushButton("Clear Graph")
        self.clear_button.clicked.connect(self.clear_graph)
        self.layout.addWidget(self.clear_button)

        self.graph_window = None

    def show_graph(self):
        if self.graph_window is not None:
            self.graph_window.close()

        self.graph_window = GraphWindow(self)
        self.graph_window.show()

    def clear_graph(self):
        if self.graph_window is not None:
            self.graph_window.clear_graph()

    def on_graph_window_closed(self):
        self.graph_window = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
