import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
import pyqtgraph as pg
import numpy as np

class GraphWindow(QMainWindow):
    def __init__(self):
        super().__init__()

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

        # Plot some example data
        self.plot_data()

    def plot_data(self):
        # Example data
        x = np.linspace(0, 10, 100)
        y = np.sin(x)

        # Plot the data
        self.plot_widget.plot(x, y, pen=pg.mkPen(color='r', width=2), symbol='o', symbolSize=8, symbolBrush=pg.mkBrush('r'))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Main Window")
        self.setGeometry(100, 100, 400, 300)

        # Create a central widget and set the layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        # Create a button
        self.button = QPushButton("Show Graph")
        self.button.clicked.connect(self.show_graph)
        self.layout.addWidget(self.button)

    def show_graph(self):
        self.graph_window = GraphWindow()
        self.graph_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
